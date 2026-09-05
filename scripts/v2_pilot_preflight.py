#!/usr/bin/env python3
"""Read-only pilot-readiness preflight for the Nexus V2 curriculum.

Answers one question: if the V2 pilot were switched on against this database
right now, would a student hit a wall?

**This script never writes.** It opens the database read-only, runs SELECTs,
and prints PASS / WARN / FAIL per check. Point ``--database-url`` at a
disposable copy to rehearse a migration or a content load; the default target
is whatever ``DATABASE_URL`` the backend is configured with, and even then
nothing is mutated.

    ./.venv/bin/python ../scripts/v2_pilot_preflight.py
    ./.venv/bin/python ../scripts/v2_pilot_preflight.py --json
    ./.venv/bin/python ../scripts/v2_pilot_preflight.py --check-links
    ./.venv/bin/python ../scripts/v2_pilot_preflight.py --baseline before.json
    ./.venv/bin/python ../scripts/v2_pilot_preflight.py --compare-baseline before.json

Exit status is 1 if any check FAILs, otherwise 0. WARNs never fail the run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"


@dataclass
class Report:
    checks: list[dict] = field(default_factory=list)

    def add(self, section: str, name: str, status: str, detail: str = "") -> None:
        self.checks.append(
            {"section": section, "name": name, "status": status, "detail": detail}
        )

    @property
    def counts(self) -> Counter:
        return Counter(check["status"] for check in self.checks)

    @property
    def failed(self) -> bool:
        return self.counts[FAIL] > 0

    def render(self) -> str:
        lines: list[str] = []
        section = None
        for check in self.checks:
            if check["section"] != section:
                section = check["section"]
                lines.append(f"\n== {section} ==")
            detail = f" — {check['detail']}" if check["detail"] else ""
            lines.append(f"  [{check['status']:<4}] {check['name']}{detail}")
        counts = self.counts
        lines.append(
            f"\nsummary: {counts[PASS]} pass, {counts[WARN]} warn, "
            f"{counts[FAIL]} fail, {counts[SKIP]} skip"
        )
        lines.append("V2 PILOT PREFLIGHT " + ("FAILED" if self.failed else "PASSED"))
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #


def check_schema(report: Report, db, database_url: str) -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    section = "Schema"
    try:
        config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
        config.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
        heads = ScriptDirectory.from_config(config).get_heads()
    except Exception as exc:  # pragma: no cover - environment dependent
        report.add(section, "alembic head", SKIP, f"could not read migrations: {exc}")
        return

    if len(heads) == 1:
        report.add(section, "single Alembic head", PASS, heads[0])
    else:
        report.add(section, "single Alembic head", FAIL, f"{len(heads)} heads: {heads}")

    try:
        current = [
            row[0]
            for row in db.execute(text("SELECT version_num FROM alembic_version"))
        ]
    except Exception as exc:
        report.add(section, "current revision", FAIL, f"unreadable: {exc}")
        return

    if len(current) != 1:
        report.add(
            section, "current revision", FAIL, f"{len(current)} rows in alembic_version"
        )
        return
    if heads and current[0] == heads[0]:
        report.add(section, "database is at head", PASS, current[0])
    else:
        report.add(
            section,
            "database is at head",
            FAIL,
            f"database at {current[0]}, head is {heads[0] if heads else 'unknown'}",
        )


# --------------------------------------------------------------------------- #
# Curriculum
# --------------------------------------------------------------------------- #


def check_curriculum(report: Report, db) -> dict:
    from app.models.certification import (
        Certification,
        CertificationObjective,
        CertificationVersion,
        InterviewPrompt,
        LessonObjective,
        LessonV2Meta,
        ModuleAssessment,
    )
    from app.models.certification import CertificationModule
    from app.services.v2_curriculum_service import STUDENT_MODULE_ROLES

    section = "Curriculum"
    counts = {
        "certifications": db.query(Certification).count(),
        "versions": db.query(CertificationVersion).count(),
        "objectives": db.query(CertificationObjective).count(),
        "modules_active": db.query(CertificationModule).filter_by(active=True).count(),
        "lessons": db.query(LessonV2Meta)
        .filter(LessonV2Meta.status.in_(("ready", "published")))
        .count(),
        "assessments": db.query(ModuleAssessment).filter_by(active=True).count(),
        "explain_prompts": db.query(InterviewPrompt).filter_by(active=True).count(),
    }
    for label, value in counts.items():
        report.add(section, label, PASS if value else FAIL, str(value))

    visible = []
    for module in db.query(CertificationModule).filter_by(active=True).all():
        assessments = (
            db.query(ModuleAssessment)
            .filter_by(certification_module_id=module.id, active=True)
            .all()
        )
        has_lessons = (
            db.query(LessonV2Meta)
            .filter(
                LessonV2Meta.certification_module_id == module.id,
                LessonV2Meta.status.in_(("ready", "published")),
            )
            .first()
            is not None
        )
        if has_lessons and STUDENT_MODULE_ROLES.issubset(
            {row.assessment_role for row in assessments}
        ):
            visible.append(module)
    report.add(
        section,
        "modules visible to students",
        PASS if visible else FAIL,
        str(len(visible)),
    )

    unmapped = (
        db.query(LessonV2Meta)
        .filter(
            LessonV2Meta.status.in_(("ready", "published")),
            ~LessonV2Meta.id.in_(db.query(LessonObjective.lesson_v2_meta_id)),
        )
        .count()
    )
    report.add(
        section,
        "lessons mapped to objectives",
        PASS if unmapped == 0 else WARN,
        "all mapped" if unmapped == 0 else f"{unmapped} lesson(s) without an objective",
    )
    return {"visible_modules": [module.module_key for module in visible], **counts}


# --------------------------------------------------------------------------- #
# Assessments — the available-but-unopenable class of bug
# --------------------------------------------------------------------------- #


def check_assessments(report: Report, db, visible_module_keys: list[str]) -> None:
    from app.models.certification import CertificationModule, ModuleAssessment
    from app.models.lab import LabTemplate
    from app.services.v2_curriculum_service import (
        assessment_is_available,
        quiz_is_student_visible,
        service_desk_scenario_is_playable,
    )

    section = "Assessments"
    offenders: list[str] = []
    checked = 0
    for module_key in visible_module_keys:
        module = db.query(CertificationModule).filter_by(module_key=module_key).one()
        for assessment in (
            db.query(ModuleAssessment)
            .filter_by(certification_module_id=module.id, active=True)
            .all()
        ):
            checked += 1
            if not assessment_is_available(db, assessment):
                continue
            role = assessment.assessment_role
            openable = True
            if role in {"quick_check", "module_quiz"}:
                openable = quiz_is_student_visible(db, assessment.quiz_id)
            elif role == "practical":
                openable = bool(
                    assessment.lab_template_id
                    and db.query(LabTemplate.id)
                    .filter(
                        LabTemplate.id == assessment.lab_template_id,
                        LabTemplate.is_published.is_(True),
                    )
                    .first()
                )
            elif role == "service_desk":
                openable = service_desk_scenario_is_playable(db, assessment)
            if not openable:
                offenders.append(assessment.assessment_key)
    report.add(section, "student-facing assessments checked", PASS, str(checked))
    if offenders:
        report.add(
            section,
            "no available-but-unopenable assessment",
            FAIL,
            ", ".join(sorted(offenders)),
        )
    else:
        report.add(section, "no available-but-unopenable assessment", PASS)

    blocked = [
        assessment.assessment_key
        for assessment in db.query(ModuleAssessment).filter_by(active=True).all()
        if assessment.assessment_role in {"quick_check", "module_quiz"}
        and not assessment_is_available(db, assessment)
    ]
    report.add(
        section,
        "knowledge checks blocked from students",
        PASS if not blocked else WARN,
        "none" if not blocked else f"{len(blocked)}: " + ", ".join(sorted(blocked)[:8]),
    )


# --------------------------------------------------------------------------- #
# Editorial
# --------------------------------------------------------------------------- #


def check_editorial(report: Report, db) -> None:
    from app.models.certification import ModuleAssessment
    from app.models.quiz import (
        EDITORIAL_STATUS_VALIDATED,
        QUIZ_STATUS_PUBLISHED,
        Quiz,
    )

    section = "Editorial"
    quiz_ids = {row.quiz_id for row in db.query(ModuleAssessment).all() if row.quiz_id}
    if not quiz_ids:
        report.add(
            section, "V2 question banks", FAIL, "no bank is bound to an assessment"
        )
        return

    approved, published, blocked, missing_approval = [], [], [], []
    for quiz in db.query(Quiz).filter(Quiz.id.in_(quiz_ids)).all():
        reasons = []
        if quiz.status == QUIZ_STATUS_PUBLISHED and quiz.is_active:
            published.append(quiz.title)
        if quiz.status != QUIZ_STATUS_PUBLISHED:
            reasons.append(f"status={quiz.status}")
        if not quiz.is_active:
            reasons.append("inactive")
        if quiz.editorial_status != EDITORIAL_STATUS_VALIDATED:
            reasons.append(f"editorial={quiz.editorial_status}")
        if not quiz.answer_keys_validated:
            reasons.append("answer keys unvalidated")
        if quiz.editorial_status != EDITORIAL_STATUS_VALIDATED:
            missing_approval.append(quiz.title)
        (blocked if reasons else approved).append((quiz.title, reasons))

    report.add(section, "approved banks", PASS, str(len(approved)))
    report.add(section, "published banks", PASS, str(len(published)))
    report.add(
        section,
        "banks missing approval",
        WARN if missing_approval else PASS,
        "none" if not missing_approval else ", ".join(sorted(missing_approval)),
    )
    if blocked:
        # Reported, never repaired — editorial review is a human gate.
        detail = "; ".join(
            f"{title} ({', '.join(reasons)})" for title, reasons in blocked
        )
        report.add(section, "blocked banks", WARN, detail)
    else:
        report.add(section, "blocked banks", PASS, "none")


# --------------------------------------------------------------------------- #
# Service Desk
# --------------------------------------------------------------------------- #


def check_service_desk(report: Report, db) -> None:
    from sqlalchemy import func
    from app.models.certification import ModuleAssessment
    from app.models.service_desk import (
        ServiceDeskScenario,
        ServiceDeskScenarioVersion,
    )

    section = "Service Desk"
    rows = (
        db.query(ModuleAssessment)
        .filter_by(assessment_role="service_desk", active=True)
        .all()
    )
    if not rows:
        report.add(section, "Service Desk assessments", WARN, "none defined")
    else:
        unresolved, unpublished, mismatched = [], [], []
        for assessment in rows:
            expected = (assessment.config or {}).get("engine_service_desk_ref")
            scenario = (
                db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
                if assessment.service_desk_scenario_id
                else None
            )
            if scenario is None and expected:
                scenario = (
                    db.query(ServiceDeskScenario)
                    .filter(
                        func.lower(ServiceDeskScenario.stable_key) == expected.lower()
                    )
                    .one_or_none()
                )
            if scenario is None:
                unresolved.append(assessment.assessment_key)
                continue
            if expected and scenario.stable_key.lower() != expected.lower():
                mismatched.append(assessment.assessment_key)
            published = (
                db.query(ServiceDeskScenarioVersion.id)
                .filter_by(scenario_id=scenario.id, status="published")
                .first()
            )
            if published is None:
                unpublished.append(scenario.stable_key)

        report.add(section, "Service Desk assessments", PASS, str(len(rows)))
        report.add(
            section,
            "every assessment resolves a stable key",
            PASS if not unresolved else FAIL,
            "all resolved" if not unresolved else ", ".join(sorted(unresolved)),
        )
        report.add(
            section,
            "assessment relationships match stable keys",
            PASS if not mismatched else FAIL,
            "all valid" if not mismatched else ", ".join(sorted(mismatched)),
        )
        report.add(
            section,
            "every scenario has a published version",
            PASS if not unpublished else FAIL,
            "all published" if not unpublished else ", ".join(sorted(unpublished)),
        )

    expected_realism = {f"inc25{number:02d}" for number in range(1, 11)}
    evidence_based: set[str] = set()
    for stable_key in sorted(expected_realism):
        scenario = (
            db.query(ServiceDeskScenario)
            .filter(func.lower(ServiceDeskScenario.stable_key) == stable_key)
            .one_or_none()
        )
        version = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id, status="published")
            .order_by(ServiceDeskScenarioVersion.version_number.desc())
            .first()
            if scenario
            else None
        )
        definition = version.definition_json if version else {}
        if definition.get("simulation_fixture") and str(
            definition.get("objective_catalog_version", "")
        ).startswith("realism-v"):
            evidence_based.add(stable_key)
    missing = sorted(key.upper() for key in expected_realism - evidence_based)
    report.add(
        section,
        "scenario realism",
        PASS if len(evidence_based) == 10 else FAIL,
        (
            "10/10 former converted scenarios use evidence-based fixtures"
            if len(evidence_based) == 10
            else f"{len(evidence_based)}/10 evidence-based; missing: {', '.join(missing)}"
        ),
    )


# --------------------------------------------------------------------------- #
# Practicals — the legacy week-gate coupling
# --------------------------------------------------------------------------- #


def check_practicals(report: Report, db) -> None:
    from app.models.certification import ModuleAssessment
    from app.models.lab import LabTemplate

    section = "Practicals"
    rows = (
        db.query(ModuleAssessment)
        .filter_by(assessment_role="practical", active=True)
        .all()
    )
    if not rows:
        report.add(section, "V2 practicals", FAIL, "none defined")
        return
    report.add(section, "V2 practicals", PASS, str(len(rows)))

    unresolved, unpublished, bad_type, has_vmid, legacy_weeks = [], [], [], [], []
    for assessment in rows:
        lab = (
            db.get(LabTemplate, assessment.lab_template_id)
            if assessment.lab_template_id
            else None
        )
        if lab is None:
            unresolved.append(assessment.assessment_key)
            continue
        if not lab.is_published:
            unpublished.append(assessment.assessment_key)
        if not (lab.lab_type or "").strip():
            bad_type.append(assessment.assessment_key)
        if lab.proxmox_template_vmid is not None:
            has_vmid.append(assessment.assessment_key)
        if lab.week_number != 0:
            legacy_weeks.append(f"{assessment.assessment_key} (week {lab.week_number})")

    report.add(
        section,
        "every practical resolves a lab",
        PASS if not unresolved else FAIL,
        "all resolved" if not unresolved else ", ".join(sorted(unresolved)),
    )
    report.add(
        section,
        "every practical is published",
        PASS if not unpublished else FAIL,
        "all published" if not unpublished else ", ".join(sorted(unpublished)),
    )
    report.add(
        section,
        "lab_type is set",
        PASS if not bad_type else FAIL,
        "all set" if not bad_type else ", ".join(sorted(bad_type)),
    )
    report.add(
        section,
        "no Proxmox VM required for the A+ pilot",
        PASS if not has_vmid else FAIL,
        "none" if not has_vmid else ", ".join(sorted(has_vmid)),
    )
    report.add(
        section,
        "validated V2 practical relationships",
        PASS if not unresolved else FAIL,
        "explicit module/assessment/lab relationships present",
    )
    report.add(
        section,
        "legacy week metadata",
        WARN if legacy_weeks else PASS,
        "none" if not legacy_weeks else ", ".join(sorted(legacy_weeks)),
    )


# --------------------------------------------------------------------------- #
# Required resources
# --------------------------------------------------------------------------- #


def check_resources(report: Report, db, *, check_links: bool, timeout: float) -> None:
    from app.models.certification import LearningResource, LearningResourceLink
    from app.services.v2_content_loader import valid_external_url

    section = "Required resources"
    rows = (
        db.query(LearningResourceLink, LearningResource)
        .join(LearningResource, LearningResource.id == LearningResourceLink.resource_id)
        .filter(
            LearningResourceLink.is_required.is_(True),
            LearningResource.active.is_(True),
        )
        .all()
    )
    if not rows:
        report.add(section, "required resources", WARN, "none defined")
        return
    report.add(section, "required resources", PASS, str(len(rows)))

    unusable = [
        resource.resource_key
        for _, resource in rows
        if not valid_external_url(resource.url)
    ]
    report.add(
        section,
        "every required resource has a usable URL",
        PASS if not unusable else FAIL,
        "all valid" if not unusable else ", ".join(sorted(unusable)),
    )

    if not check_links:
        report.add(section, "link reachability", SKIP, "pass --check-links to test")
        return
    for _, resource in rows:
        status, detail = _probe(resource.url, timeout)
        report.add(section, f"link {resource.resource_key}", status, detail)


def _probe(url: str, timeout: float) -> tuple[str, str]:
    """Classify one URL as reachable / redirect / unavailable / timeout.

    Network access is opt-in (``--check-links``) and never part of a content
    load. HEAD first, falling back to GET where a host does not support it.
    """
    import urllib.error
    import urllib.request

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(
            url, method=method, headers={"User-Agent": "nexus-v2-preflight/1.0"}
        )
        try:
            with opener.open(request, timeout=timeout) as response:
                return PASS, f"reachable ({response.status} via {method})"
        except urllib.error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                return WARN, f"redirect ({exc.code})"
            if exc.code in {403, 405, 501} and method == "HEAD":
                continue  # host refuses HEAD; retry with GET
            return WARN, f"unavailable (HTTP {exc.code})"
        except TimeoutError:
            return WARN, "timeout"
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                return WARN, "timeout"
            return WARN, f"unavailable ({exc.reason})"
        except Exception as exc:  # pragma: no cover - defensive
            return WARN, f"unavailable ({exc})"
    return WARN, "unavailable (HEAD and GET both refused)"


# --------------------------------------------------------------------------- #
# Stable keys and orphans
# --------------------------------------------------------------------------- #


def check_stable_keys(report: Report, db) -> None:
    from sqlalchemy import func
    from app.models.certification import (
        CertificationModule,
        InterviewPrompt,
        LearningResource,
        LessonV2Meta,
        ModuleAssessment,
    )
    from app.models.service_desk import ServiceDeskScenario

    section = "Stable keys"
    for label, model, column in (
        ("module_key", CertificationModule, CertificationModule.module_key),
        ("lesson_key", LessonV2Meta, LessonV2Meta.lesson_key),
        ("assessment_key", ModuleAssessment, ModuleAssessment.assessment_key),
        ("resource_key", LearningResource, LearningResource.resource_key),
        ("prompt_key", InterviewPrompt, InterviewPrompt.prompt_key),
        (
            "Service Desk stable_key",
            ServiceDeskScenario,
            ServiceDeskScenario.stable_key,
        ),
    ):
        duplicates = [
            f"{value} x{count}"
            for value, count in db.query(column, func.count(model.id))
            .group_by(column)
            .having(func.count(model.id) > 1)
            .all()
        ]
        report.add(
            section,
            f"{label} is unique",
            PASS if not duplicates else FAIL,
            "unique" if not duplicates else ", ".join(duplicates),
        )


def check_orphans(report: Report, db) -> None:
    from app.models.certification import (
        CertificationModule,
        InterviewPrompt,
        LearningResourceLink,
        LessonObjective,
        LessonV2Meta,
        ModuleAssessment,
        QuestionObjective,
    )
    from app.models.lab import LabTemplate
    from app.models.service_desk import ServiceDeskScenario

    section = "Orphans"
    module_ids = db.query(CertificationModule.id)
    lesson_ids = db.query(LessonV2Meta.id)

    checks = [
        (
            "assessments without a module",
            db.query(ModuleAssessment)
            .filter(~ModuleAssessment.certification_module_id.in_(module_ids))
            .count(),
        ),
        (
            "lessons without a module",
            db.query(LessonV2Meta)
            .filter(~LessonV2Meta.certification_module_id.in_(module_ids))
            .count(),
        ),
        (
            "Explain prompts without a module",
            db.query(InterviewPrompt)
            .filter(~InterviewPrompt.certification_module_id.in_(module_ids))
            .count(),
        ),
        (
            "lesson objectives without a lesson",
            db.query(LessonObjective)
            .filter(~LessonObjective.lesson_v2_meta_id.in_(lesson_ids))
            .count(),
        ),
        (
            "resource links without a target",
            db.query(LearningResourceLink)
            .filter(
                LearningResourceLink.lesson_v2_meta_id.is_(None),
                LearningResourceLink.certification_module_id.is_(None),
            )
            .count(),
        ),
        (
            "practicals pointing at a missing lab",
            db.query(ModuleAssessment)
            .filter(
                ModuleAssessment.lab_template_id.isnot(None),
                ~ModuleAssessment.lab_template_id.in_(db.query(LabTemplate.id)),
            )
            .count(),
        ),
        (
            "assessments pointing at a missing scenario",
            db.query(ModuleAssessment)
            .filter(
                ModuleAssessment.service_desk_scenario_id.isnot(None),
                ~ModuleAssessment.service_desk_scenario_id.in_(
                    db.query(ServiceDeskScenario.id)
                ),
            )
            .count(),
        ),
    ]
    try:
        checks.append(
            (
                "question objectives without a question",
                db.query(QuestionObjective)
                .filter(
                    ~QuestionObjective.question_id.in_(
                        db.query(
                            __import__(
                                "app.models.quiz", fromlist=["Question"]
                            ).Question.id
                        )
                    )
                )
                .count(),
            )
        )
    except Exception:  # pragma: no cover - defensive
        pass

    for label, count in checks:
        report.add(section, label, PASS if count == 0 else FAIL, str(count))


# --------------------------------------------------------------------------- #
# V1 safety baseline
# --------------------------------------------------------------------------- #


def v1_baseline(db) -> dict:
    """Capture what V1 students can currently see, for before/after comparison."""
    from app.models.quiz import Quiz
    from app.services.quiz_visibility import (
        student_visible_quiz_filters,
        v1_student_visible_quiz_filters,
    )

    return {
        "v1_visible_quiz_ids": sorted(
            row.id
            for row in db.query(Quiz).filter(*v1_student_visible_quiz_filters()).all()
        ),
        "all_visible_quiz_ids": sorted(
            row.id
            for row in db.query(Quiz).filter(*student_visible_quiz_filters()).all()
        ),
    }


def check_v1_safety(report: Report, db, baseline_path: str | None) -> None:
    section = "V1 safety"
    current = v1_baseline(db)
    report.add(
        section,
        "quizzes visible to V1 students",
        PASS,
        str(len(current["v1_visible_quiz_ids"])),
    )
    if not baseline_path:
        report.add(
            section, "baseline comparison", SKIP, "pass --compare-baseline to compare"
        )
        return
    try:
        with open(baseline_path, encoding="utf-8") as handle:
            before = json.load(handle)
    except OSError as exc:
        report.add(section, "baseline comparison", FAIL, f"unreadable baseline: {exc}")
        return

    added = sorted(
        set(current["v1_visible_quiz_ids"]) - set(before.get("v1_visible_quiz_ids", []))
    )
    removed = sorted(
        set(before.get("v1_visible_quiz_ids", [])) - set(current["v1_visible_quiz_ids"])
    )
    report.add(
        section,
        "no V1 quiz newly visible",
        PASS if not added else FAIL,
        "none" if not added else f"newly visible quiz ids: {added}",
    )
    report.add(
        section,
        "no V1 quiz lost visibility",
        PASS if not removed else FAIL,
        "none" if not removed else f"quiz ids no longer visible: {removed}",
    )


# --------------------------------------------------------------------------- #


def build_session(database_url: str | None):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    if database_url:
        url = database_url
    else:
        from app.database import DATABASE_URL as configured_url

        url = configured_url

    engine_url = url
    connect_args = {}
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        path = url.removeprefix("sqlite:///")
        absolute_path = path if path.startswith("/") else os.path.abspath(path)
        engine_url = f"sqlite:///file:{quote(absolute_path, safe='/')}?mode=ro&uri=true"
        connect_args = {"check_same_thread": False, "uri": True}

    engine = create_engine(engine_url, connect_args=connect_args)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    if not url.startswith("sqlite"):
        from sqlalchemy import text

        session.execute(text("SET TRANSACTION READ ONLY"))
    return session, url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--database-url", help="target database (default: backend config)"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="probe required external resource URLs (network)",
    )
    parser.add_argument("--link-timeout", type=float, default=10.0)
    parser.add_argument(
        "--baseline", metavar="PATH", help="write a V1 visibility baseline and exit"
    )
    parser.add_argument(
        "--compare-baseline",
        metavar="PATH",
        help="compare V1 visibility against a baseline file",
    )
    args = parser.parse_args()

    db, url = build_session(args.database_url)
    try:
        if args.baseline:
            with open(args.baseline, "w", encoding="utf-8") as handle:
                json.dump(v1_baseline(db), handle, indent=2)
            print(f"baseline written to {args.baseline}")
            return 0

        report = Report()
        report.add("Target", "database", PASS, _redact(url))
        check_schema(report, db, url)
        curriculum = check_curriculum(report, db)
        check_assessments(report, db, curriculum["visible_modules"])
        check_editorial(report, db)
        check_service_desk(report, db)
        check_practicals(report, db)
        check_resources(
            report, db, check_links=args.check_links, timeout=args.link_timeout
        )
        check_stable_keys(report, db)
        check_orphans(report, db)
        check_v1_safety(report, db, args.compare_baseline)
    finally:
        # Never leave a transaction open against a production database.
        db.rollback()
        db.close()

    if args.json:
        counts = report.counts
        print(
            json.dumps(
                {
                    "checks": report.checks,
                    "summary": {
                        status.lower(): counts[status]
                        for status in (PASS, WARN, FAIL, SKIP)
                    },
                    "passed": not report.failed,
                },
                indent=2,
            )
        )
    else:
        print(report.render())
    return 1 if report.failed else 0


def _redact(url: str) -> str:
    """Never print credentials from a database URL."""
    parsed = urlsplit(url)
    if parsed.password:
        return url.replace(parsed.password, "***")
    return url


if __name__ == "__main__":
    sys.exit(main())
