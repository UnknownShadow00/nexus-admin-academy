"""Idempotent loader for the Nexus V2 certification hierarchy (Phase 1A).

Reads maintainable YAML data files under ``backend/content/`` and upserts:

    certifications
    certification_versions   (exam codes carried as data)
    certification_domains
    certification_modules
    certification_objectives

Guarantees:

* Re-running never creates duplicates — every entity is matched on its stable
  natural key and updated in place.
* Objective codes are stable; nothing is renumbered.
* Multiple certification versions coexist (the same objective code can exist
  under 220-1201 and 220-1202 independently).
* Switching a lesson/question/module from one certification version to another
  is a data edit, never a code change.
* The loader NEVER deletes rows and NEVER touches ``training_weeks`` or any
  legacy progression table.

Nothing here runs automatically. It is invoked explicitly (tests, a future
admin action, or ``backend/seed_v2_foundation.py``).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

import yaml
from sqlalchemy.orm import Session

from app.models.certification import (
    ASSESSMENT_ROLE_VALUES,
    PERMISSION_STATUS_VALUES,
    RESOURCE_TYPE_VALUES,
    Certification,
    CertificationDomain,
    CertificationModule,
    CertificationObjective,
    CertificationVersion,
    InterviewPrompt,
    InterviewPromptObjective,
    LearningResource,
    LearningResourceLink,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
    normalize_importance,
)
from app.models.lab import LabTemplate
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, Question, Quiz
from app.models.service_desk import ServiceDeskScenario

_HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONTENT_DIR = os.path.join(_HERE, "content")
DEFAULT_CERT_DIR = os.path.join(DEFAULT_CONTENT_DIR, "certifications")
DEFAULT_OBJECTIVES_DIR = os.path.join(DEFAULT_CONTENT_DIR, "objectives")
DEFAULT_RESOURCES_DIR = os.path.join(DEFAULT_CONTENT_DIR, "resources")
DEFAULT_INTERVIEW_PROMPTS_DIR = os.path.join(DEFAULT_CONTENT_DIR, "interview-prompts")
DEFAULT_CURRICULUM_DIR = os.path.join(DEFAULT_CONTENT_DIR, "curriculum")
DEFAULT_QUESTIONS_DIR = os.path.join(DEFAULT_CONTENT_DIR, "questions")
EDITORIAL_APPROVALS_FILE = "editorial-approvals.yaml"
DEFAULT_LABS_DIR = os.path.join(DEFAULT_CONTENT_DIR, "labs")


class ContentValidationError(ValueError):
    """A content data file failed validation. Message names the file + field."""


@dataclass
class LoadSummary:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    by_entity: dict = field(default_factory=dict)

    def record(self, entity: str, outcome: str) -> None:
        setattr(self, outcome, getattr(self, outcome) + 1)
        bucket = self.by_entity.setdefault(entity, {"created": 0, "updated": 0, "unchanged": 0})
        bucket[outcome] += 1

    def as_dict(self) -> dict:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "by_entity": self.by_entity,
        }


def _read_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level")
    return data


def _apply(row, fields: dict) -> bool:
    """Set attributes that differ; return True if anything changed."""
    changed = False
    for key, value in fields.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    return changed


def load_certifications(db: Session, path: str | None = None, *, summary: LoadSummary | None = None) -> LoadSummary:
    """Upsert one certification file (cert + versions + domains + modules)."""
    path = path or os.path.join(DEFAULT_CERT_DIR, "comptia_aplus.yaml")
    summary = summary or LoadSummary()
    doc = _read_yaml(path)

    cert_data = doc["certification"]
    cert = (
        db.query(Certification)
        .filter(Certification.cert_key == cert_data["cert_key"])
        .one_or_none()
    )
    cert_fields = {
        "name": cert_data["name"],
        "provider": cert_data.get("provider"),
        "display_order": int(cert_data.get("display_order", 0)),
        "active": bool(cert_data.get("active", True)),
    }
    if cert is None:
        cert = Certification(cert_key=cert_data["cert_key"], **cert_fields)
        db.add(cert)
        db.flush()
        summary.record("certification", "created")
    else:
        summary.record("certification", "updated" if _apply(cert, cert_fields) else "unchanged")

    for version_data in doc.get("versions", []):
        version = (
            db.query(CertificationVersion)
            .filter(CertificationVersion.version_key == version_data["version_key"])
            .one_or_none()
        )
        version_fields = {
            "certification_id": cert.id,
            "label": version_data["label"],
            "exam_codes": list(version_data.get("exam_codes", [])),
            "is_current": bool(version_data.get("is_current", False)),
            "effective_date": _as_str(version_data.get("effective_date")),
            "source_name": version_data.get("source_name"),
            "source_url": version_data.get("source_url"),
            "active": bool(version_data.get("active", True)),
        }
        if version is None:
            version = CertificationVersion(version_key=version_data["version_key"], **version_fields)
            db.add(version)
            db.flush()
            summary.record("certification_version", "created")
        else:
            summary.record(
                "certification_version",
                "updated" if _apply(version, version_fields) else "unchanged",
            )

        for order_default, domain_data in enumerate(version_data.get("domains", []), start=1):
            _upsert_domain(db, version, domain_data, order_default, summary)

        # Domains must be persisted before modules resolve their domain FK,
        # regardless of the session's autoflush setting.
        db.flush()

        for order_default, module_data in enumerate(version_data.get("modules", []), start=1):
            _upsert_module(db, version, module_data, order_default, summary)

    db.flush()
    return summary


def _upsert_domain(db, version, domain_data, order_default, summary) -> None:
    domain = (
        db.query(CertificationDomain)
        .filter(
            CertificationDomain.certification_version_id == version.id,
            CertificationDomain.domain_key == str(domain_data["domain_key"]),
        )
        .one_or_none()
    )
    fields = {
        "title": domain_data["title"],
        "weight_percent": _as_int(domain_data.get("weight_percent")),
        "display_order": int(domain_data.get("display_order", order_default)),
        "active": bool(domain_data.get("active", True)),
    }
    if domain is None:
        domain = CertificationDomain(
            certification_version_id=version.id,
            domain_key=str(domain_data["domain_key"]),
            **fields,
        )
        db.add(domain)
        summary.record("certification_domain", "created")
    else:
        summary.record(
            "certification_domain", "updated" if _apply(domain, fields) else "unchanged"
        )


def _upsert_module(db, version, module_data, order_default, summary) -> None:
    module = (
        db.query(CertificationModule)
        .filter(CertificationModule.module_key == module_data["module_key"])
        .one_or_none()
    )
    domain_id = None
    domain_key = module_data.get("certification_domain_key")
    if domain_key is not None:
        domain = (
            db.query(CertificationDomain)
            .filter(
                CertificationDomain.certification_version_id == version.id,
                CertificationDomain.domain_key == str(domain_key),
            )
            .one_or_none()
        )
        domain_id = domain.id if domain else None
    fields = {
        "certification_version_id": version.id,
        "certification_domain_id": domain_id,
        "title": module_data["title"],
        "skill_promise": module_data.get("skill_promise"),
        "importance_hint": module_data.get("importance_hint"),
        "display_order": int(module_data.get("display_order", order_default)),
        "legacy_module_code": module_data.get("legacy_module_code"),
        "active": bool(module_data.get("active", True)),
    }
    if module is None:
        module = CertificationModule(module_key=module_data["module_key"], **fields)
        db.add(module)
        summary.record("certification_module", "created")
    else:
        summary.record(
            "certification_module", "updated" if _apply(module, fields) else "unchanged"
        )
    db.flush()
    _sync_module_assessments(db, module, module_data.get("assessments") or [], summary)


def _sync_module_assessments(db, module, assessments: list, summary) -> None:
    """Upsert module_assessments rows for one module. Engine refs (quiz / lab /
    Service Desk scenario) are OPTIONAL and resolved by human-readable key;
    an unresolvable ref is a warning, not an error — the row is still created
    so the wiring is visible."""
    for order_default, item in enumerate(assessments, start=1):
        role = str(item.get("assessment_role") or "").strip()
        key = str(item.get("assessment_key") or "").strip()
        if not key or role not in ASSESSMENT_ROLE_VALUES:
            raise ContentValidationError(
                f"module '{module.module_key}': assessment needs a key and a valid "
                f"assessment_role (one of {sorted(ASSESSMENT_ROLE_VALUES)}); got "
                f"key={key!r} role={role!r}"
            )
        quiz_id = _resolve_quiz(db, item.get("quiz_ref"))
        lab_id = _resolve_lab(db, item.get("lab_ref"))
        scenario_id = _resolve_scenario(db, item.get("service_desk_ref"))
        lesson_meta_id = _resolve_lesson_meta(db, item.get("lesson_key"))
        config = dict(item.get("config") or {})
        # Preserve stable engine references as data so presentation clients can
        # offer a useful launch target even when a separately-seeded engine row
        # has not been loaded into this development database yet.
        for source_key, config_key in (
            ("quiz_ref", "engine_quiz_ref"),
            ("lab_ref", "engine_lab_ref"),
            ("service_desk_ref", "engine_service_desk_ref"),
        ):
            if item.get(source_key):
                config[config_key] = str(item[source_key])
        fields = {
            "certification_module_id": module.id,
            "lesson_v2_meta_id": lesson_meta_id,
            "assessment_role": role,
            "title": item.get("title"),
            "quiz_id": quiz_id,
            "lab_template_id": lab_id,
            "service_desk_scenario_id": scenario_id,
            "displayed_count": _as_int(item.get("displayed_count")),
            "pass_percent": int(item.get("pass_percent", 70)),
            "config": config,
            "display_order": int(item.get("display_order", order_default)),
            "active": bool(item.get("active", True)),
        }
        row = (
            db.query(ModuleAssessment)
            .filter(ModuleAssessment.assessment_key == key)
            .one_or_none()
        )
        if row is None:
            db.add(ModuleAssessment(assessment_key=key, **fields))
            summary.record("module_assessment", "created")
        else:
            summary.record("module_assessment", "updated" if _apply(row, fields) else "unchanged")


def _resolve_quiz(db, ref):
    if ref is None or ref == "":
        return None
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        row = db.get(Quiz, int(ref))
    else:
        row = db.query(Quiz).filter(Quiz.title == str(ref)).first()
    return row.id if row else None


def _resolve_lab(db, ref):
    if not ref:
        return None
    row = db.query(LabTemplate).filter(LabTemplate.title == str(ref)).first()
    return row.id if row else None


def _resolve_scenario(db, ref):
    if not ref:
        return None
    row = db.query(ServiceDeskScenario).filter(ServiceDeskScenario.stable_key == str(ref)).first()
    return row.id if row else None


def _resolve_lesson_meta(db, lesson_key):
    if not lesson_key:
        return None
    row = db.query(LessonV2Meta).filter(LessonV2Meta.lesson_key == str(lesson_key)).first()
    return row.id if row else None


def load_objectives(db: Session, path: str, *, summary: LoadSummary | None = None) -> LoadSummary:
    """Upsert every objective in one file for the version it names."""
    summary = summary or LoadSummary()
    doc = _read_yaml(path)

    version_key = doc["version_key"]
    version = (
        db.query(CertificationVersion)
        .filter(CertificationVersion.version_key == version_key)
        .one_or_none()
    )
    if version is None:
        raise ValueError(
            f"{path}: certification version '{version_key}' is not loaded — "
            "run load_certifications first"
        )

    file_source_name = doc.get("source_name")
    file_source_url = doc.get("source_url")

    for order_default, obj in enumerate(doc.get("objectives", []), start=1):
        code = str(obj["code"])
        row = (
            db.query(CertificationObjective)
            .filter(
                CertificationObjective.certification_version_id == version.id,
                CertificationObjective.objective_code == code,
            )
            .one_or_none()
        )
        fields = {
            "domain_key": _as_str(obj.get("domain_key")),
            "objective_text": obj["text"],
            "subtopics": list(obj.get("subtopics", [])),
            "display_order": int(obj.get("display_order", order_default)),
            "source_name": obj.get("source_name", file_source_name),
            "source_url": obj.get("source_url", file_source_url),
            "active": bool(obj.get("active", True)),
        }
        if row is None:
            row = CertificationObjective(
                certification_version_id=version.id,
                objective_code=code,
                **fields,
            )
            db.add(row)
            summary.record("certification_objective", "created")
        else:
            summary.record(
                "certification_objective",
                "updated" if _apply(row, fields) else "unchanged",
            )

    db.flush()
    return summary


def load_all(
    db: Session,
    *,
    cert_dir: str | None = None,
    objectives_dir: str | None = None,
    commit: bool = False,
    summary: LoadSummary | None = None,
) -> dict:
    """Load every certification file, then every objective file it references."""
    cert_dir = cert_dir or DEFAULT_CERT_DIR
    objectives_dir = objectives_dir or DEFAULT_OBJECTIVES_DIR
    summary = summary if summary is not None else LoadSummary()

    objective_files: list[str] = []
    for name in sorted(os.listdir(cert_dir)):
        if not name.endswith((".yaml", ".yml")):
            continue
        cert_path = os.path.join(cert_dir, name)
        load_certifications(db, cert_path, summary=summary)
        doc = _read_yaml(cert_path)
        for version_data in doc.get("versions", []):
            ref = version_data.get("objectives_file")
            if ref:
                objective_files.append(os.path.join(objectives_dir, ref))

    for obj_path in objective_files:
        load_objectives(db, obj_path, summary=summary)

    if commit:
        db.commit()
    return summary.as_dict()


def _version_id_for(db, version_key, *, where: str):
    if not version_key:
        return None
    row = (
        db.query(CertificationVersion)
        .filter(CertificationVersion.version_key == str(version_key))
        .one_or_none()
    )
    if row is None:
        raise ContentValidationError(
            f"{where}: certification_version '{version_key}' is not loaded"
        )
    return row.id


def _objective_ids_for(db, version_id, codes, *, where: str) -> list[int]:
    ids: list[int] = []
    for code in codes or []:
        row = (
            db.query(CertificationObjective)
            .filter(
                CertificationObjective.certification_version_id == version_id,
                CertificationObjective.objective_code == str(code),
            )
            .one_or_none()
        )
        if row is None:
            raise ContentValidationError(
                f"{where}: objective_code '{code}' does not exist in that version"
            )
        ids.append(row.id)
    return ids


def load_resources(db: Session, path: str, *, summary: LoadSummary | None = None) -> LoadSummary:
    """Upsert learning resources + their lesson/module links from one YAML file."""
    summary = summary or LoadSummary()
    doc = _read_yaml(path)
    rel = os.path.basename(path)

    for item in doc.get("resources", []):
        key = str(item.get("resource_key") or "").strip()
        if not key:
            raise ContentValidationError(f"{rel}: a resource is missing 'resource_key'")
        rtype = str(item.get("resource_type") or "").strip()
        if rtype not in RESOURCE_TYPE_VALUES:
            raise ContentValidationError(
                f"{rel}: resource '{key}': resource_type '{rtype}' invalid "
                f"(expected one of {sorted(RESOURCE_TYPE_VALUES)})"
            )
        perm = str(item.get("permission_status") or "unknown").strip().lower()
        if perm not in PERMISSION_STATUS_VALUES:
            raise ContentValidationError(
                f"{rel}: resource '{key}': permission_status '{perm}' invalid"
            )
        version_id = _version_id_for(
            db, item.get("certification_version"), where=f"{rel}: resource '{key}'"
        )
        fields = {
            "title": item.get("title") or key,
            "url": item.get("url"),
            "provider": item.get("provider"),
            "resource_type": rtype,
            "certification_version_id": version_id,
            "duration": _as_str(item.get("duration")),
            "source_name": item.get("source_name"),
            "source_url": item.get("source_url"),
            "permission_status": perm,
            "license_note": item.get("license_note"),
            "active": bool(item.get("active", True)),
        }
        row = (
            db.query(LearningResource)
            .filter(LearningResource.resource_key == key)
            .one_or_none()
        )
        if row is None:
            row = LearningResource(resource_key=key, **fields)
            db.add(row)
            db.flush()
            summary.record("resource", "created")
        else:
            summary.record("resource", "updated" if _apply(row, fields) else "unchanged")

        _sync_resource_links(db, row, item.get("links") or [], rel, key, summary)

    db.flush()
    return summary


def _sync_resource_links(db, resource, links, rel, key, summary) -> None:
    desired: set[tuple] = set()
    for order_default, link in enumerate(links, start=1):
        lesson_meta_id = _resolve_lesson_meta(db, link.get("lesson_key"))
        module_id = None
        if link.get("module_key"):
            module = (
                db.query(CertificationModule)
                .filter(CertificationModule.module_key == str(link["module_key"]))
                .one_or_none()
            )
            if module is None:
                raise ContentValidationError(
                    f"{rel}: resource '{key}': link module_key '{link['module_key']}' not found"
                )
            module_id = module.id
        if link.get("lesson_key") and lesson_meta_id is None:
            raise ContentValidationError(
                f"{rel}: resource '{key}': link lesson_key '{link['lesson_key']}' not found "
                "(load lessons first)"
            )
        if lesson_meta_id is None and module_id is None:
            raise ContentValidationError(
                f"{rel}: resource '{key}': a link needs lesson_key or module_key"
            )
        existing = (
            db.query(LearningResourceLink)
            .filter(
                LearningResourceLink.resource_id == resource.id,
                LearningResourceLink.lesson_v2_meta_id == lesson_meta_id,
                LearningResourceLink.certification_module_id == module_id,
            )
            .one_or_none()
        )
        link_fields = {
            "is_required": bool(link.get("required", False)),
            "display_order": int(link.get("order", order_default)),
        }
        if existing is None:
            db.add(
                LearningResourceLink(
                    resource_id=resource.id,
                    lesson_v2_meta_id=lesson_meta_id,
                    certification_module_id=module_id,
                    **link_fields,
                )
            )
            summary.record("resource_link", "created")
        else:
            summary.record(
                "resource_link", "updated" if _apply(existing, link_fields) else "unchanged"
            )
        desired.add((lesson_meta_id, module_id))

    for stale in (
        db.query(LearningResourceLink)
        .filter(LearningResourceLink.resource_id == resource.id)
        .all()
    ):
        if (stale.lesson_v2_meta_id, stale.certification_module_id) not in desired:
            db.delete(stale)
            summary.record("resource_link", "updated")


def load_interview_prompts(db: Session, path: str, *, summary: LoadSummary | None = None) -> LoadSummary:
    """Upsert Explain / interview prompts + their objective links (no AI)."""
    summary = summary or LoadSummary()
    doc = _read_yaml(path)
    rel = os.path.basename(path)

    for item in doc.get("prompts", []):
        key = str(item.get("prompt_key") or "").strip()
        if not key:
            raise ContentValidationError(f"{rel}: a prompt is missing 'prompt_key'")
        if not str(item.get("prompt") or "").strip():
            raise ContentValidationError(f"{rel}: prompt '{key}': 'prompt' text is required")
        version_id = _version_id_for(
            db, item.get("certification_version"), where=f"{rel}: prompt '{key}'"
        )
        module_id = None
        if item.get("module"):
            module = (
                db.query(CertificationModule)
                .filter(CertificationModule.module_key == str(item["module"]))
                .one_or_none()
            )
            if module is None:
                raise ContentValidationError(
                    f"{rel}: prompt '{key}': module '{item['module']}' not found"
                )
            module_id = module.id
        rubric = item.get("rubric") or {}
        if not isinstance(rubric, dict):
            raise ContentValidationError(f"{rel}: prompt '{key}': 'rubric' must be a mapping")
        fields = {
            "certification_version_id": version_id,
            "certification_module_id": module_id,
            "domain_key": _as_str(item.get("domain")),
            "prompt": item["prompt"],
            "expected_concepts": list(item.get("expected_concepts") or []),
            "rubric": dict(rubric),
            "rubric_version": _as_str(item.get("rubric_version")),
            "importance": normalize_importance(item.get("importance")),
            "model_answer_outline": item.get("model_answer_outline"),
            "source_name": item.get("source_name"),
            "source_url": item.get("source_url"),
            "active": bool(item.get("active", True)),
        }
        row = (
            db.query(InterviewPrompt).filter(InterviewPrompt.prompt_key == key).one_or_none()
        )
        if row is None:
            row = InterviewPrompt(prompt_key=key, **fields)
            db.add(row)
            db.flush()
            summary.record("interview_prompt", "created")
        else:
            summary.record("interview_prompt", "updated" if _apply(row, fields) else "unchanged")

        want = set(
            _objective_ids_for(
                db, version_id, item.get("objectives") or [], where=f"{rel}: prompt '{key}'"
            )
        )
        have = {
            r.objective_id
            for r in db.query(InterviewPromptObjective).filter(
                InterviewPromptObjective.interview_prompt_id == row.id
            )
        }
        for oid in want - have:
            db.add(InterviewPromptObjective(interview_prompt_id=row.id, objective_id=oid))
            summary.record("interview_prompt_objective", "created")
        for oid in have - want:
            db.query(InterviewPromptObjective).filter(
                InterviewPromptObjective.interview_prompt_id == row.id,
                InterviewPromptObjective.objective_id == oid,
            ).delete()
            summary.record("interview_prompt_objective", "updated")

    db.flush()
    return summary


def load_labs(db: Session, path: str, *, summary: LoadSummary | None = None) -> LoadSummary:
    """Upsert guided practical labs from one YAML file.

    A lab is curriculum data: adding or editing a practical is a data change,
    never a code change. Rows are matched on ``title`` (the same human-readable
    key ``module_assessments.lab_ref`` resolves against). This loader creates
    only self-contained guided labs — it never provisions a VM and never sets
    ``proxmox_template_vmid`` unless the file explicitly names one.
    """
    summary = summary or LoadSummary()
    doc = _read_yaml(path)
    rel = os.path.basename(path)

    for item in doc.get("labs", []):
        title = str(item.get("title") or "").strip()
        if not title:
            raise ContentValidationError(f"{rel}: a lab is missing 'title'")
        difficulty = int(item.get("difficulty", 1))
        if not 1 <= difficulty <= 5:
            raise ContentValidationError(
                f"{rel}: lab '{title}': difficulty must be 1-5, got {difficulty}"
            )
        lesson_meta_id = _resolve_lesson_meta(db, item.get("lesson_key"))
        fields = {
            "description": item.get("description"),
            "lab_type": item.get("lab_type") or "guided",
            "difficulty": difficulty,
            "estimated_minutes": _as_int(item.get("estimated_minutes")),
            "is_published": bool(item.get("is_published", True)),
            "environment_requirements": dict(item.get("environment_requirements") or {}),
            "setup_instructions": item.get("setup_instructions"),
            "break_script": item.get("break_script"),
            "success_criteria": dict(item.get("success_criteria") or {}),
            "required_evidence": dict(item.get("required_evidence") or {}),
            "hints": item.get("hints") or {},
            "model_solution": item.get("model_solution"),
            "proxmox_template_vmid": _as_int(item.get("proxmox_template_vmid")),
        }
        row = db.query(LabTemplate).filter(LabTemplate.title == title).first()
        if row is None:
            row = LabTemplate(title=title, **fields)
            # Legacy NOT NULL column with no V2 meaning; keep it stable.
            row.week_number = int(item.get("week_number", 0))
            db.add(row)
            summary.record("lab_template", "created")
        else:
            changed = _apply(row, fields)
            summary.record("lab_template", "updated" if changed else "unchanged")
        if lesson_meta_id is not None:
            meta = db.get(LessonV2Meta, lesson_meta_id)
            if meta is not None and meta.lesson_id is not None:
                row.lesson_id = meta.lesson_id

    db.flush()
    return summary


def load_question_banks(
    db: Session, questions_dir: str | None = None, *, summary: LoadSummary | None = None
) -> LoadSummary:
    """Import every question-bank spreadsheet under ``content/questions/``.

    Each ``*.csv`` / ``*.xlsx`` file is parsed and imported through the SAME
    ``app.services.question_importer`` pipeline the admin UI uses — identical
    validation, fingerprint de-duplication, freeform grading-metadata parsing,
    and companion ``question_v2_meta`` writes. Questions are therefore never
    hard-coded in Python: a maintainer edits the spreadsheet and re-runs the
    loader.

    NOTE: ``question_importer.confirm_import`` owns its own transaction and
    commits on success, so imported questions are persisted regardless of this
    function's caller. A row whose content and V2 metadata are unchanged since
    the last run is reported as ``unchanged`` (a true no-op — no write, no
    provenance re-stamp); a changed row is ``updated``; a new row is
    ``created``. Rows on an already-published quiz are skipped, never
    silently overwritten.
    """
    from app.services.question_importer import (
        ImportFileError,
        confirm_import,
        parse_csv_file,
        parse_xlsx_file,
    )

    summary = summary or LoadSummary()
    questions_dir = questions_dir or DEFAULT_QUESTIONS_DIR
    if not os.path.isdir(questions_dir):
        return summary

    for name in sorted(os.listdir(questions_dir)):
        lower = name.lower()
        if lower.endswith(".csv"):
            parser = parse_csv_file
        elif lower.endswith((".xlsx", ".xlsm")):
            parser = parse_xlsx_file
        else:
            continue
        with open(os.path.join(questions_dir, name), "rb") as handle:
            data = handle.read()
        try:
            rows = parser(data)
        except ImportFileError as exc:
            raise ContentValidationError(f"{name}: {exc}") from exc
        result = confirm_import(
            db, rows, duplicate_policy="update_draft", source_filename=name
        )
        for _ in range(result["created"]):
            summary.record("question", "created")
        for _ in range(result["updated"]):
            summary.record("question", "updated")
        for _ in range(result.get("unchanged", 0) + result["skipped_duplicates"]):
            summary.record("question", "unchanged")
        if result["skipped_invalid"]:
            raise ContentValidationError(
                f"{name}: {result['skipped_invalid']} row(s) failed question "
                "validation; fix the spreadsheet and re-run"
            )
    _apply_question_bank_editorial_approvals(db, questions_dir, summary)
    return summary


def _apply_question_bank_editorial_approvals(
    db: Session, questions_dir: str, summary: LoadSummary
) -> None:
    """Promote only the exact bank bytes that received human review."""
    manifest_path = os.path.join(questions_dir, EDITORIAL_APPROVALS_FILE)
    if not os.path.isfile(manifest_path):
        return
    with open(manifest_path, encoding="utf-8") as handle:
        approvals = (yaml.safe_load(handle) or {}).get("approvals") or []
    for approval in approvals:
        filename = str(approval.get("filename") or "").strip()
        title = str(approval.get("quiz_title") or "").strip()
        expected_hash = str(approval.get("sha256") or "").strip().lower()
        expected_count = int(approval.get("reviewed_question_count") or 0)
        if not filename or not title or approval.get("editorial_status") != EDITORIAL_STATUS_VALIDATED:
            raise ContentValidationError(f"{EDITORIAL_APPROVALS_FILE}: invalid approval entry")
        bank_path = os.path.join(questions_dir, filename)
        if not os.path.isfile(bank_path):
            raise ContentValidationError(f"{EDITORIAL_APPROVALS_FILE}: missing reviewed bank {filename}")
        with open(bank_path, "rb") as handle:
            actual_hash = hashlib.sha256(handle.read()).hexdigest()
        if actual_hash != expected_hash:
            raise ContentValidationError(
                f"{filename}: content changed after editorial approval; review and update its approval hash"
            )
        quiz = db.query(Quiz).filter(Quiz.title == title).one_or_none()
        if quiz is None:
            raise ContentValidationError(f"{filename}: reviewed quiz {title!r} was not imported")
        actual_count = db.query(Question).filter(Question.quiz_id == quiz.id).count()
        if actual_count != expected_count:
            raise ContentValidationError(
                f"{filename}: reviewed {expected_count} questions but imported {actual_count}"
            )
        changed = not (
            quiz.editorial_status == EDITORIAL_STATUS_VALIDATED
            and quiz.answer_keys_validated
            and quiz.explanations_complete
        )
        quiz.editorial_status = EDITORIAL_STATUS_VALIDATED
        quiz.answer_keys_validated = True
        quiz.explanations_complete = True
        summary.record("question_bank_editorial_approval", "updated" if changed else "unchanged")


def load_content(
    db: Session,
    *,
    curriculum_dir: str | None = None,
    resources_dir: str | None = None,
    interview_prompts_dir: str | None = None,
    questions_dir: str | None = None,
    labs_dir: str | None = None,
    commit: bool = False,
    summary: LoadSummary | None = None,
) -> dict:
    """Load Markdown lessons, then question banks, labs, resources, prompts.

    ``load_all`` (hierarchy + objectives + module assessments) must have run
    first — lessons/resources/prompts reference that structure. Re-run
    ``load_all`` AFTER this so ``module_assessments`` can resolve the
    ``quiz_ref`` / ``lab_ref`` that only exist once this function has created
    the quiz and lab rows. ``load_module()`` does this whole sequence in one
    call — prefer it unless you specifically need a single pass.
    """
    from app.services.v2_lesson_loader import load_lessons

    curriculum_dir = curriculum_dir or DEFAULT_CURRICULUM_DIR
    resources_dir = resources_dir or DEFAULT_RESOURCES_DIR
    interview_prompts_dir = interview_prompts_dir or DEFAULT_INTERVIEW_PROMPTS_DIR
    labs_dir = labs_dir or DEFAULT_LABS_DIR
    summary = summary if summary is not None else LoadSummary()

    if os.path.isdir(curriculum_dir):
        load_lessons(db, curriculum_dir, summary=summary)

    load_question_banks(db, questions_dir, summary=summary)

    if os.path.isdir(labs_dir):
        for name in sorted(os.listdir(labs_dir)):
            if name.endswith((".yaml", ".yml")):
                load_labs(db, os.path.join(labs_dir, name), summary=summary)

    for directory, loader in (
        (resources_dir, load_resources),
        (interview_prompts_dir, load_interview_prompts),
    ):
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith((".yaml", ".yml")):
                loader(db, os.path.join(directory, name), summary=summary)

    if commit:
        db.commit()
    return summary.as_dict()


def load_module(
    db: Session,
    *,
    cert_dir: str | None = None,
    objectives_dir: str | None = None,
    curriculum_dir: str | None = None,
    resources_dir: str | None = None,
    interview_prompts_dir: str | None = None,
    questions_dir: str | None = None,
    labs_dir: str | None = None,
    commit: bool = False,
) -> dict:
    """One-call, idempotent load of the whole V2 curriculum from ``content/``.

    A curriculum author calls this and does not need to know the internal
    ordering. It:

    1. loads the certification hierarchy + objectives + module-assessment rows
       (``load_all``);
    2. loads all content — Markdown lessons, question banks (CSV/XLSX), guided
       labs, learning resources, interview/Explain prompts (``load_content``);
    3. reconverges the hierarchy pass (``load_all`` again) so every
       ``module_assessments`` row can now resolve the ``quiz_ref`` / ``lab_ref``
       / ``service_desk_ref`` that only exists once step 2 has created the quiz
       and lab rows.

    Returns the merged ``LoadSummary`` plus a ``references`` block reporting
    how many ``module_assessments`` engine refs resolved, so a caller can
    assert wiring is complete in one place.
    """
    summary = LoadSummary()
    load_all(db, cert_dir=cert_dir, objectives_dir=objectives_dir, summary=summary)
    load_content(
        db,
        curriculum_dir=curriculum_dir,
        resources_dir=resources_dir,
        interview_prompts_dir=interview_prompts_dir,
        questions_dir=questions_dir,
        labs_dir=labs_dir,
        summary=summary,
    )
    load_all(db, cert_dir=cert_dir, objectives_dir=objectives_dir, summary=summary)

    # Report reference resolution so one call can prove the wiring converged.
    # quick_check / module_quiz / practical refs come from content this loader
    # creates, so they MUST resolve. service_desk points at a scenario owned by
    # a separate Service Desk seed — it is reported but not required here.
    assessments = db.query(ModuleAssessment).all()
    content_roles = {"quick_check", "module_quiz", "practical"}
    need_content_engine = [a for a in assessments if a.assessment_role in content_roles]
    unresolved = sorted(
        a.assessment_key
        for a in need_content_engine
        if not (a.quiz_id or a.lab_template_id)
    )
    sd_rows = [a for a in assessments if a.assessment_role == "service_desk"]

    if commit:
        db.commit()

    out = summary.as_dict()
    out["references"] = {
        "content_engine_assessments": len(need_content_engine),
        "content_engine_resolved": len(need_content_engine) - len(unresolved),
        "content_engine_unresolved": unresolved,
        "service_desk_assessments": len(sd_rows),
        "service_desk_resolved": sum(1 for a in sd_rows if a.service_desk_scenario_id),
    }
    return out


def backfill_examcompass_permission(db: Session, *, commit: bool = False) -> dict:
    """Mark existing, un-classified ExamCompass questions as ``permitted``.

    Owner decision (Phase 1A): existing ExamCompass questions may be reused.
    Provenance is preserved exactly — the legacy ``questions.source`` text is
    never rewritten. Only the companion ``question_v2_meta`` row is created or
    updated, and only when the question is currently unclassified (no meta row,
    or ``permission_status = 'unknown'``).
    """
    matched = 0
    updated = 0
    questions = (
        db.query(Question)
        .filter(Question.source.isnot(None), Question.source.ilike("%examcompass%"))
        .all()
    )
    for question in questions:
        matched += 1
        meta = (
            db.query(QuestionV2Meta)
            .filter(QuestionV2Meta.question_id == question.id)
            .one_or_none()
        )
        if meta is None:
            meta = QuestionV2Meta(
                question_id=question.id,
                permission_status="permitted",
                source_name="ExamCompass",
            )
            db.add(meta)
            updated += 1
        elif meta.permission_status == "unknown":
            meta.permission_status = "permitted"
            if not meta.source_name:
                meta.source_name = "ExamCompass"
            updated += 1
    if commit:
        db.commit()
    return {"matched": matched, "updated": updated}


def _as_str(value) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_int(value) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
