"""Safe, certification-agnostic intake for externally approved V2 curriculum.

The inbox is not a second curriculum engine.  This service validates and
normalizes an author-friendly package into the files consumed by the existing
V2 loaders.  Educational prose and answers are never rewritten.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable
from zipfile import BadZipFile, ZipFile

import yaml

from app.services.question_importer import TEMPLATE_COLUMNS, parse_csv_file, parse_xlsx_file, row_to_payload
from app.services.question_validation import validate_question

MAX_ZIP_FILES = 2_000
MAX_ZIP_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
APPROVALS_FILE = "editorial-approvals.yaml"

FIELD_ALIASES = {
    "question": "question_text",
    "correct_answer": "correct_answers",
    "objective": "objective_code",
    "accepted_variants": "acceptable_answers",
    "min_concepts_pass": "min_concepts_for_pass",
}
QUESTION_TYPE_ALIASES = {
    "single-choice": "single",
    "single_choice": "single",
    "multiple-choice": "single",
    "multi-select": "multi",
    "multi_select": "multi",
    "short-answer": "short_answer",
    "free-response": "free_response",
    "true-false": "true_false",
}
IMPORTANCE_ALIASES = {
    "job critical": "job_critical",
    "job-critical": "job_critical",
    "working knowledge": "working_knowledge",
    "working-knowledge": "working_knowledge",
    "awareness": "awareness",
    "know_it": "working_knowledge",
}
RELATIONSHIP_ALIASES = {
    "new": "new",
    "review": "review",
    "review of": "review",
    "review_of": "review",
    "deep dive": "deep_dive",
    "deep-dive": "deep_dive",
    "deep_dive": "deep_dive",
}


class IntakeError(ValueError):
    """A package-local validation error suitable for an owner-facing report."""

    def __init__(self, message: str, *, file: str = "package", field: str = "package"):
        super().__init__(message)
        self.file = file
        self.field = field

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "row": None,
            "key": None,
            "field": self.field,
            "expected": None,
            "actual": None,
            "message": str(self),
        }


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def safe_extract_zip(archive_path: Path, destination: Path) -> None:
    """Extract a ZIP only after every member passes traversal/link/size checks."""
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ZIP_FILES:
                raise IntakeError(f"ZIP contains more than {MAX_ZIP_FILES} files", file=archive_path.name)
            if sum(member.file_size for member in members) > MAX_ZIP_UNCOMPRESSED_BYTES:
                raise IntakeError("ZIP uncompressed size exceeds the 50 MB safety limit", file=archive_path.name)
            for member in members:
                raw_name = member.filename
                posix = PurePosixPath(raw_name)
                windows = PureWindowsPath(raw_name)
                unix_mode = member.external_attr >> 16
                unsafe = (
                    not raw_name
                    or "\\" in raw_name
                    or posix.is_absolute()
                    or windows.is_absolute()
                    or windows.drive
                    or ".." in posix.parts
                    or stat.S_ISLNK(unix_mode)
                    or not _within(destination / Path(*posix.parts), destination)
                )
                if unsafe:
                    raise IntakeError(
                        f"unsafe ZIP member rejected: {raw_name!r}",
                        file=archive_path.name,
                        field="zip_member",
                    )
            corrupt = archive.testzip()
            if corrupt:
                raise IntakeError(f"ZIP member failed integrity check: {corrupt}", file=archive_path.name)
            for member in members:
                target = destination / Path(*PurePosixPath(member.filename).parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except BadZipFile as exc:
        raise IntakeError("file is not a valid ZIP archive", file=archive_path.name) from exc


def _read_yaml(path: Path) -> dict:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise IntakeError(f"invalid YAML: {exc}", file=path.name) from exc
    if not isinstance(value, dict):
        raise IntakeError("YAML document must be a mapping", file=path.name)
    return value


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise IntakeError("Markdown must begin with YAML frontmatter", file=str(path), field="frontmatter")
    # Only horizontal whitespace belongs to the fence.  ``\s`` would consume
    # the blank line after it and therefore alter approved Markdown bodies.
    match = re.search(r"^---[ \t]*$", text[3:], flags=re.MULTILINE)
    if not match:
        raise IntakeError("Markdown frontmatter is not closed", file=str(path), field="frontmatter")
    end = 3 + match.end()
    try:
        meta = yaml.safe_load(text[3 : 3 + match.start()]) or {}
    except yaml.YAMLError as exc:
        raise IntakeError(f"invalid Markdown frontmatter: {exc}", file=str(path), field="frontmatter") from exc
    if not isinstance(meta, dict):
        raise IntakeError("Markdown frontmatter must be a mapping", file=str(path), field="frontmatter")
    return meta, text[end:]


def _render_frontmatter(meta: dict, untouched_body: str) -> str:
    return f"---\n{yaml.safe_dump(meta, sort_keys=False)}---{untouched_body}"


def _tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise IntakeError("symbolic links are not accepted in curriculum folders", file=str(item))
        if item.is_file():
            relative = item.relative_to(path).as_posix().encode()
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            digest.update(item.read_bytes())
    return digest.hexdigest()


def _source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else _tree_hash(path)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _normalize_scalar(value, aliases: dict[str, str], notes: set[str]):
    raw = str(value or "").strip()
    normalized = aliases.get(raw.casefold(), raw.lower().replace(" ", "_"))
    if raw and raw != normalized:
        notes.add(f"{raw} -> {normalized}")
    return normalized


def _json_cell(value) -> str:
    if value in (None, ""):
        return ""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")) if isinstance(value, (list, dict)) else str(value)


class CurriculumIntakeProcessor:
    """Discover, validate, stage, archive, and integrate independent packages."""

    def __init__(
        self,
        *,
        dropbox_dir: Path,
        approved_dir: Path,
        content_dir: Path,
        backend_dir: Path,
        runtime_validator: Callable[[Path, dict], dict] | None = None,
        service_desk_keys: set[str] | None = None,
    ):
        self.dropbox_dir = Path(dropbox_dir)
        self.approved_dir = Path(approved_dir)
        self.content_dir = Path(content_dir)
        self.backend_dir = Path(backend_dir)
        self.runtime_validator = runtime_validator or self._validate_in_scratch_database
        self.service_desk_keys = service_desk_keys

    def discover(self) -> list[Path]:
        self.dropbox_dir.mkdir(parents=True, exist_ok=True)
        ignored = {"README.md", ".gitkeep", ".reports"}
        return sorted(
            [p for p in self.dropbox_dir.iterdir() if p.name not in ignored and (p.is_dir() or p.suffix.lower() == ".zip")],
            key=lambda p: p.name.casefold(),
        )

    def process(self, *, mode: str, allow_changed: bool = False) -> list[dict]:
        if mode not in {"check", "apply"}:
            raise ValueError("mode must be 'check' or 'apply'")
        results = []
        for source in self.discover():
            try:
                results.append(self._process_one(source, mode=mode, allow_changed=allow_changed))
            except Exception as exc:  # isolate one bad package from its siblings
                issue = exc.as_dict() if isinstance(exc, IntakeError) else IntakeError(str(exc)).as_dict()
                result = {
                    "source": source.name,
                    "status": "INVALID",
                    "errors": [issue],
                    "normalizations": [],
                    "package_hash": None,
                    "approved_destination": None,
                }
                self._write_report(source.name, result)
                results.append(result)
        return results

    def _process_one(self, source: Path, *, mode: str, allow_changed: bool) -> dict:
        if source.is_symlink():
            raise IntakeError("symbolic links are not accepted as inbox packages", file=source.name)
        package_hash = _source_hash(source)
        with tempfile.TemporaryDirectory(prefix="nexus-curriculum-intake-") as tmp:
            workspace = Path(tmp)
            if source.is_file():
                extracted = workspace / "extracted"
                safe_extract_zip(source, extracted)
                root = self._locate_package_root(extracted)
            else:
                root = self._locate_package_root(source)
            normalized = self._normalize_and_validate(root, source.name, package_hash)
            module_root = (
                self.approved_dir
                / normalized["manifest"]["certification_key"]
                / normalized["manifest"]["version_key"]
                / normalized["manifest"]["module_key"]
            )
            classification = self._classify(module_root, package_hash)
            base = {
                "source": source.name,
                "errors": [],
                "normalizations": sorted(normalized["normalizations"]),
                "package_hash": package_hash,
                "approved_destination": str(module_root / package_hash),
                "classification": classification,
            }
            staged_content = workspace / "content"
            shutil.copytree(self.content_dir, staged_content)
            runtime_destinations = self._write_runtime(normalized, staged_content)
            loader_result = self.runtime_validator(staged_content, normalized["manifest"])
            unresolved = loader_result.get("references", {}).get("content_engine_unresolved", [])
            if unresolved:
                raise IntakeError(f"runtime references did not resolve: {unresolved}", field="assessments")
            service_unresolved = loader_result.get("references", {}).get("package_service_desk_unresolved", [])
            if service_unresolved:
                raise IntakeError(
                    f"Service Desk references did not resolve: {service_unresolved}",
                    field="service_desk",
                )

            if classification == "CHANGED" and not allow_changed:
                result = {**base, "status": "CHANGED_REQUIRES_REVIEW", "runtime_destinations": runtime_destinations}
                self._write_report(source.name, result)
                return result

            if mode == "check":
                if classification == "UNCHANGED":
                    status = "UNCHANGED"
                else:
                    status = "VALID_WITH_NORMALIZATION" if normalized["normalizations"] else "VALID"
                result = {**base, "status": status, "runtime_destinations": runtime_destinations}
                self._write_report(source.name, result)
                return result

            archive_destination = module_root / package_hash
            rollback = self._promote_runtime(staged_content, runtime_destinations)
            if classification == "UNCHANGED":
                try:
                    self._verify_archive(archive_destination, package_hash)
                    self._remove_inbox_item(source)
                except Exception:
                    self._rollback_runtime(rollback)
                    raise
                result = {**base, "status": "UNCHANGED", "runtime_destinations": runtime_destinations}
                self._write_report(source.name, result)
                return result
            try:
                receipt = self._archive(
                    source,
                    archive_destination,
                    normalized["manifest"],
                    loader_result,
                    runtime_destinations,
                    classification,
                )
                self._verify_archive(archive_destination, package_hash)
                if receipt["validation_result"] != "VALID":
                    raise IntakeError("receipt verification failed", field="receipt")
                self._remove_inbox_item(source)
            except Exception:
                self._rollback_runtime(rollback)
                if archive_destination.exists():
                    shutil.rmtree(archive_destination)
                raise
            result = {**base, "status": "IMPORTED", "runtime_destinations": runtime_destinations}
            self._write_report(source.name, result)
            return result

    @staticmethod
    def _locate_package_root(root: Path) -> Path:
        if (root / "module_overview.md").is_file():
            return root
        candidates = [p.parent for p in root.rglob("module_overview.md")]
        if len(candidates) != 1:
            raise IntakeError("package must contain exactly one module_overview.md", field="module_overview")
        return candidates[0]

    def _registry(self) -> dict:
        registry: dict[str, dict] = {}
        cert_dir = self.content_dir / "certifications"
        for path in sorted(cert_dir.glob("*.y*ml")):
            doc = _read_yaml(path)
            cert_key = str((doc.get("certification") or {}).get("cert_key") or "")
            if not cert_key:
                continue
            versions = {}
            for version in doc.get("versions") or []:
                version_key = str(version.get("version_key") or "")
                objective_file = self.content_dir / "objectives" / str(version.get("objectives_file") or "")
                objective_doc = _read_yaml(objective_file) if objective_file.is_file() else {}
                objectives = {str(row.get("code") or row.get("objective_code")) for row in objective_doc.get("objectives") or []}
                versions[version_key] = {
                    "data": version,
                    "objectives": objectives,
                    "domains": {str(row.get("domain_key")) for row in version.get("domains") or []},
                }
            registry[cert_key] = {"path": path, "doc": doc, "versions": versions}
        return registry

    def _normalize_and_validate(self, root: Path, original_name: str, package_hash: str) -> dict:
        notes: set[str] = set()
        overview_path = root / "module_overview.md"
        overview, _overview_body = _split_frontmatter(overview_path)
        required = ("certification", "certification_version", "domain", "module_key", "title", "skill_promise")
        for field in required:
            if not str(overview.get(field) or "").strip():
                raise IntakeError(f"required package metadata '{field}' is missing", file="module_overview.md", field=field)

        cert_key = str(overview["certification"]).strip()
        version_key = str(overview["certification_version"]).strip()
        domain = str(overview["domain"]).strip()
        module_key = str(overview["module_key"]).strip()
        registry = self._registry()
        if cert_key not in registry:
            raise IntakeError(f"certification '{cert_key}' is not in Nexus certification data", field="certification")
        if version_key not in registry[cert_key]["versions"]:
            raise IntakeError(f"version '{version_key}' does not belong to '{cert_key}'", field="certification_version")
        version = registry[cert_key]["versions"][version_key]
        if domain not in version["domains"]:
            raise IntakeError(f"domain '{domain}' does not belong to '{version_key}'", field="domain")

        lessons: list[tuple[str, str]] = []
        lesson_keys: set[str] = set()
        objective_codes: set[str] = set()
        lesson_dir = root / "lessons"
        if not lesson_dir.is_dir():
            raise IntakeError("lessons/ directory is required", field="lessons")
        lesson_meta_rows = []
        for path in sorted(lesson_dir.glob("*.md")):
            meta, body = _split_frontmatter(path)
            for field in ("lesson_key", "title", "lesson_order", "importance", "learning_relationship", "objectives"):
                if meta.get(field) in (None, "", []):
                    raise IntakeError(f"lesson field '{field}' is required", file=path.name, field=field)
            if str(meta.get("certification_version")) != version_key or str(meta.get("module")) != module_key:
                raise IntakeError("lesson version/module does not match package metadata", file=path.name, field="module")
            meta["domain"] = str(meta.get("domain") or domain)
            meta["importance"] = _normalize_scalar(meta["importance"], IMPORTANCE_ALIASES, notes)
            meta["learning_relationship"] = _normalize_scalar(meta["learning_relationship"], RELATIONSHIP_ALIASES, notes)
            lesson_objectives = [str(value) for value in meta.get("objectives") or []]
            self._validate_objectives(lesson_objectives, version["objectives"], path.name)
            objective_codes.update(lesson_objectives)
            key = str(meta["lesson_key"])
            if key in lesson_keys:
                raise IntakeError(f"duplicate lesson key '{key}'", file=path.name, field="lesson_key")
            lesson_keys.add(key)
            lessons.append((path.name, _render_frontmatter(meta, body)))
            lesson_meta_rows.append(meta)
        if not lessons:
            raise IntakeError("at least one lesson Markdown file is required", field="lessons")

        question_path = self._question_path(root)
        raw_rows = parse_xlsx_file(question_path.read_bytes()) if question_path.suffix.lower() in {".xlsx", ".xlsm"} else parse_csv_file(question_path.read_bytes())
        normalized_rows = []
        for row_number, raw in enumerate(raw_rows, 2):
            row = {}
            for key, value in raw.items():
                canonical = FIELD_ALIASES.get(str(key).strip(), str(key).strip())
                if canonical != str(key).strip():
                    notes.add(f"{key} -> {canonical}")
                row[canonical] = value
            row["question_type"] = _normalize_scalar(row.get("question_type"), QUESTION_TYPE_ALIASES, notes)
            row["importance"] = _normalize_scalar(row.get("importance"), IMPORTANCE_ALIASES, notes)
            row["certification"] = cert_key
            row["certification_version"] = version_key
            row["domain"] = domain
            row["module"] = module_key
            if row.get("published") in (None, ""):
                row["published"] = "true"
                notes.add("blank published -> true for validated package")
            payload = row_to_payload(row)
            validation = validate_question(payload)
            if not validation.valid:
                message = "; ".join(issue.message for issue in validation.errors)
                raise IntakeError(message, file=question_path.name, field=f"row {row_number}")
            objective = str(row.get("objective_code") or "").strip()
            self._validate_objectives([objective], version["objectives"], question_path.name)
            objective_codes.add(objective)
            normalized_rows.append({key: _json_cell(row.get(key)) for key in TEMPLATE_COLUMNS})
        if not normalized_rows:
            raise IntakeError("question bank is empty", file=question_path.name, field="questions")

        provenance = _read_yaml(root / "provenance.yaml") if (root / "provenance.yaml").is_file() else {}
        editorial = str(provenance.get("editorial_status") or overview.get("editorial_status") or "").lower()
        if editorial != "validated":
            raise IntakeError("package must have validated editorial status", file="provenance.yaml", field="editorial_status")
        reviewed_count = int(provenance.get("reviewed_question_count") or len(normalized_rows))
        if reviewed_count != len(normalized_rows):
            raise IntakeError("reviewed question count does not match workbook rows", file="provenance.yaml", field="reviewed_question_count")

        quiz = _read_yaml(root / "module_quiz_blueprint.yaml")
        quiz_title = str(quiz.get("quiz_title") or normalized_rows[0].get("quiz_title") or "").strip()
        if not quiz_title:
            raise IntakeError("module quiz title is required", file="module_quiz_blueprint.yaml", field="quiz_title")
        for entry in quiz.get("question_blueprint") or []:
            self._validate_objectives([str(x) for x in entry.get("objective_codes") or []], version["objectives"], "module_quiz_blueprint.yaml")
        self._validate_assessment_pools(lesson_meta_rows, quiz, normalized_rows)

        resources = self._normalize_resources(root, version_key, lesson_keys)
        prompts = self._normalize_prompts(root, version_key, module_key, domain, version["objectives"], notes)
        labs, practical_title = self._normalize_practical(root)
        service_desk_key = self._service_desk(root)
        assessments = self._build_assessments(module_key, lesson_meta_rows, quiz, quiz_title, practical_title, service_desk_key, bool(prompts))
        module = {
            "module_key": module_key,
            "title": str(overview["title"]),
            "skill_promise": str(overview["skill_promise"]),
            "certification_domain_key": domain,
            "importance_hint": _normalize_scalar(overview.get("importance", "working_knowledge"), IMPORTANCE_ALIASES, notes),
            "display_order": int(overview.get("display_order") or 1),
            "assessments": assessments,
        }
        manifest = {
            "manifest_version": 1,
            "source_package_hash": package_hash,
            "original_filename": original_name,
            "certification_key": cert_key,
            "version_key": version_key,
            "domain_key": domain,
            "module_key": module_key,
            "module_title": module["title"],
            "lessons": sorted(lesson_keys),
            "objectives": sorted(objective_codes),
            "lesson_count": len(lessons),
            "question_count": len(normalized_rows),
            "resource_count": len(resources),
            "explain_count": len(prompts),
            "practical_present": bool(labs),
            "service_desk_present": bool(service_desk_key),
            "provenance": provenance,
        }
        return {
            "manifest": manifest,
            "normalizations": notes,
            "registry_path": registry[cert_key]["path"].name,
            "module": module,
            "lessons": lessons,
            "questions": normalized_rows,
            "quiz_title": quiz_title,
            "resources": resources,
            "prompts": prompts,
            "labs": labs,
        }

    @staticmethod
    def _validate_objectives(codes: list[str], valid: set[str], filename: str) -> None:
        for code in codes:
            if not code or code not in valid:
                raise IntakeError(f"objective '{code}' is not defined for this certification version", file=filename, field="objective")

    @staticmethod
    def _question_path(root: Path) -> Path:
        candidates = [
            root / "questions_and_editorial_review.xlsx",
            root / "questions_and_editorial_review.csv",
            root / "questions.xlsx",
            root / "questions.csv",
        ]
        found = [path for path in candidates if path.is_file()]
        if len(found) != 1:
            raise IntakeError("package must contain exactly one supported question workbook", field="questions")
        return found[0]

    @staticmethod
    def _validate_assessment_pools(lessons: list[dict], quiz: dict, questions: list[dict]) -> None:
        def candidates(selector: dict) -> int:
            wanted_objectives = {str(value) for value in selector.get("objective_codes") or []}
            wanted_tags = {str(value).casefold() for value in selector.get("tags_any") or []}
            count = 0
            for row in questions:
                row_tags = {tag.strip().casefold() for tag in str(row.get("tags") or "").split(",") if tag.strip()}
                if wanted_objectives and str(row.get("objective_code")) not in wanted_objectives:
                    continue
                if wanted_tags and not row_tags.intersection(wanted_tags):
                    continue
                count += 1
            return count

        for lesson in lessons:
            quick = lesson.get("quick_check")
            if not quick:
                continue
            required = int(quick.get("displayed_count") or 3)
            if candidates(quick) < required:
                raise IntakeError(
                    f"Quick Check requests {required} questions but its filters match only {candidates(quick)}",
                    file="lessons",
                    field="quick_check",
                )
        blueprint = quiz.get("question_blueprint") or []
        requested = 0
        for entry in blueprint:
            required = int(entry.get("count") or 0)
            requested += required
            available = candidates(entry)
            if available < required:
                raise IntakeError(
                    f"Module Quiz blueprint requests {required} questions but its filters match only {available}",
                    file="module_quiz_blueprint.yaml",
                    field="question_blueprint",
                )
        displayed = int(quiz.get("displayed_count") or requested or 10)
        if displayed > len(questions) or (blueprint and requested != displayed):
            raise IntakeError(
                "Module Quiz displayed_count must equal its blueprint total and fit the bank",
                file="module_quiz_blueprint.yaml",
                field="displayed_count",
            )
        pass_percent = int(quiz.get("pass_percent") or 70)
        if not 1 <= pass_percent <= 100:
            raise IntakeError("pass_percent must be between 1 and 100", file="module_quiz_blueprint.yaml", field="pass_percent")

    def _normalize_resources(self, root: Path, version_key: str, lesson_keys: set[str]) -> list[dict]:
        path = root / "resources.yaml"
        if not path.is_file():
            return []
        rows = deepcopy(_read_yaml(path).get("resources") or [])
        for row in rows:
            if "type" in row and "resource_type" not in row:
                row["resource_type"] = row.pop("type")
            row["certification_version"] = version_key
            for link in row.get("links") or []:
                if str(link.get("lesson_key")) not in lesson_keys:
                    raise IntakeError("resource links to an unknown package lesson", file=path.name, field="lesson_key")
        return rows

    def _normalize_prompts(self, root: Path, version_key: str, module_key: str, domain: str, valid_objectives: set[str], notes: set[str]) -> list[dict]:
        path = root / "explain_prompts.yaml"
        if not path.is_file():
            return []
        rows = deepcopy(_read_yaml(path).get("prompts") or [])
        for row in rows:
            row["certification_version"] = version_key
            row["module"] = module_key
            row["domain"] = domain
            row["importance"] = _normalize_scalar(row.get("importance", "working_knowledge"), IMPORTANCE_ALIASES, notes)
            self._validate_objectives([str(x) for x in row.get("objectives") or []], valid_objectives, path.name)
            for field in ("prompt_key", "prompt", "expected_concepts", "rubric", "rubric_version"):
                if row.get(field) in (None, "", []):
                    raise IntakeError(f"Explain field '{field}' is required", file=path.name, field=field)
        return rows

    @staticmethod
    def _normalize_practical(root: Path) -> tuple[list[dict], str | None]:
        path = root / "practical.yaml"
        if not path.is_file():
            return [], None
        doc = _read_yaml(path)
        rows = deepcopy(doc.get("labs") or ([doc["practical"]] if doc.get("practical") else []))
        if len(rows) != 1 or not str(rows[0].get("title") or "").strip():
            raise IntakeError("practical must define one titled LabTemplate", file=path.name, field="practical")
        rows[0].setdefault("lab_type", "guided")
        rows[0].setdefault("is_published", True)
        return rows, str(rows[0]["title"])

    def _service_desk(self, root: Path) -> str | None:
        path = root / "service_desk.yaml"
        if not path.is_file():
            return None
        doc = _read_yaml(path)
        key = str(doc.get("scenario_key") or "").strip()
        if not key:
            raise IntakeError("Service Desk intake currently requires a stable reference to an existing Nexus scenario", file=path.name, field="scenario_key")
        if self.service_desk_keys is not None and key not in self.service_desk_keys:
            raise IntakeError(f"Service Desk scenario '{key}' is not registered", file=path.name, field="scenario_key")
        return key

    @staticmethod
    def _build_assessments(module_key: str, lessons: list[dict], quiz: dict, quiz_title: str, practical_title: str | None, service_desk_key: str | None, has_prompts: bool) -> list[dict]:
        short = _slug(module_key.removeprefix("module."))
        rows = []
        for order, lesson in enumerate(sorted(lessons, key=lambda x: int(x.get("lesson_order") or 0)), 1):
            quick = lesson.get("quick_check")
            if not quick:
                continue
            config = {key: deepcopy(value) for key, value in quick.items() if key not in {"title", "displayed_count", "pass_percent"}}
            rows.append({
                "assessment_key": f"assess.{short}.qc.{_slug(str(lesson['lesson_key']).split('.')[-1])}",
                "assessment_role": "quick_check",
                "title": quick.get("title") or f"Quick Check — {lesson['title']}",
                "lesson_key": lesson["lesson_key"],
                "quiz_ref": quiz_title,
                "displayed_count": int(quick.get("displayed_count") or 3),
                "pass_percent": int(quick.get("pass_percent") or 60),
                "config": config,
                "display_order": order,
            })
        next_order = len(rows) + 1
        rows.append({
            "assessment_key": f"assess.{short}.module_quiz",
            "assessment_role": "module_quiz",
            "title": quiz.get("title") or f"Module Quiz — {quiz_title.removesuffix(' — Module Bank')}",
            "quiz_ref": quiz_title,
            "displayed_count": int(quiz.get("displayed_count") or 10),
            "pass_percent": int(quiz.get("pass_percent") or 70),
            "config": {"question_blueprint": deepcopy(quiz.get("question_blueprint") or [])},
            "display_order": next_order,
        })
        if practical_title:
            next_order += 1
            rows.append({"assessment_key": f"assess.{short}.practical", "assessment_role": "practical", "title": practical_title, "lab_ref": practical_title, "pass_percent": 70, "display_order": next_order})
        if service_desk_key:
            next_order += 1
            rows.append({"assessment_key": f"assess.{short}.service_desk", "assessment_role": "service_desk", "title": f"Service Desk — {service_desk_key}", "service_desk_ref": service_desk_key, "pass_percent": 70, "display_order": next_order})
        if has_prompts:
            next_order += 1
            rows.append({"assessment_key": f"assess.{short}.explain", "assessment_role": "explain", "title": "Explain", "pass_percent": 70, "display_order": next_order})
        return rows

    @staticmethod
    def _classify(module_root: Path, package_hash: str) -> str:
        if (module_root / package_hash / "IMPORT_RECEIPT.json").is_file():
            return "UNCHANGED"
        if module_root.is_dir() and any(path.is_dir() for path in module_root.iterdir()):
            return "CHANGED"
        return "NEW"

    def _write_runtime(self, normalized: dict, content: Path) -> list[str]:
        manifest = normalized["manifest"]
        cert_path = content / "certifications" / normalized["registry_path"]
        cert_doc = _read_yaml(cert_path)
        version = next(row for row in cert_doc["versions"] if row["version_key"] == manifest["version_key"])
        modules = version.setdefault("modules", [])
        existing = next((index for index, row in enumerate(modules) if row.get("module_key") == manifest["module_key"]), None)
        if existing is None:
            modules.append(normalized["module"])
        else:
            modules[existing] = normalized["module"]
        cert_path.write_text(yaml.safe_dump(cert_doc, sort_keys=False, allow_unicode=True), encoding="utf-8")

        slug = _slug(manifest["module_key"])
        lesson_root = content / "curriculum" / manifest["certification_key"] / manifest["version_key"] / slug
        # A changed package owns this module's runtime lesson directory.  Clear
        # the staged copy so removed lessons cannot survive as stale content.
        if lesson_root.exists():
            shutil.rmtree(lesson_root)
        lesson_root.mkdir(parents=True, exist_ok=True)
        for filename, rendered in normalized["lessons"]:
            (lesson_root / filename).write_text(rendered, encoding="utf-8")

        question_name = f"{slug}.csv"
        question_path = content / "questions" / question_name
        question_path.parent.mkdir(parents=True, exist_ok=True)
        with question_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TEMPLATE_COLUMNS)
            writer.writeheader()
            writer.writerows(normalized["questions"])
        approval_path = content / "questions" / APPROVALS_FILE
        approvals = _read_yaml(approval_path) if approval_path.exists() else {"approvals": []}
        approval = {
            "filename": question_name,
            "quiz_title": normalized["quiz_title"],
            "sha256": hashlib.sha256(question_path.read_bytes()).hexdigest(),
            "reviewed_question_count": manifest["question_count"],
            "editorial_status": "validated",
            "reviewed_at": datetime.now(timezone.utc).date().isoformat(),
            "review_note": f"External approved package {manifest['source_package_hash']}",
        }
        approvals["approvals"] = [row for row in approvals.get("approvals") or [] if row.get("filename") != question_name] + [approval]
        approval_path.write_text(yaml.safe_dump(approvals, sort_keys=False, allow_unicode=True), encoding="utf-8")

        destinations = [str(cert_path.relative_to(content)), str(lesson_root.relative_to(content)), str(question_path.relative_to(content)), str(approval_path.relative_to(content))]
        for folder, filename, key, rows in (
            ("resources", f"{slug}.yaml", "resources", normalized["resources"]),
            ("interview-prompts", f"{slug}.yaml", "prompts", normalized["prompts"]),
            ("labs", f"{slug}.yaml", "labs", normalized["labs"]),
        ):
            path = content / folder / filename
            if rows:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(yaml.safe_dump({key: rows}, sort_keys=False, allow_unicode=True), encoding="utf-8")
            elif path.exists():
                path.unlink()
            # Include absent optional targets so apply removes stale files from
            # an earlier approved version of the same module.
            destinations.append(str(path.relative_to(content)))
        return destinations

    def _promote_runtime(self, staged: Path, relative_paths: list[str]) -> list[tuple[Path, bytes | None]]:
        rollback = []
        expanded: set[Path] = set()
        for relative in relative_paths:
            source = staged / relative
            if source.is_dir():
                expanded.update(path.relative_to(staged) for path in source.rglob("*") if path.is_file())
                destination_dir = self.content_dir / relative
                if destination_dir.is_dir():
                    expanded.update(path.relative_to(self.content_dir) for path in destination_dir.rglob("*") if path.is_file())
            else:
                expanded.add(Path(relative))
        try:
            for relative in sorted(expanded):
                source = staged / relative
                destination = self.content_dir / relative
                rollback.append((destination, destination.read_bytes() if destination.exists() else None))
                if not source.exists():
                    destination.unlink(missing_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name(f".{destination.name}.intake-{os.getpid()}")
                temporary.write_bytes(source.read_bytes())
                os.replace(temporary, destination)
        except Exception:
            self._rollback_runtime(rollback)
            raise
        return rollback

    @staticmethod
    def _rollback_runtime(rollback: list[tuple[Path, bytes | None]]) -> None:
        for destination, previous in reversed(rollback):
            if previous is None:
                destination.unlink(missing_ok=True)
            else:
                destination.write_bytes(previous)

    def _archive(self, source: Path, destination: Path, manifest: dict, loader_result: dict, runtime_destinations: list[str], classification: str) -> dict:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.parent / f".{destination.name}.pending-{os.getpid()}"
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir()
        if source.is_file():
            shutil.copy2(source, temp / source.name)
        else:
            shutil.copytree(source, temp / "source")
        (temp / "NORMALIZED_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count_source = loader_result.get("first", loader_result)
        totals = {
            key: int(count_source.get(key, 0)) if isinstance(count_source, dict) else 0
            for key in ("created", "updated", "unchanged")
        }
        receipt = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "package_hash": manifest["source_package_hash"],
            "original_filename": manifest["original_filename"],
            "certification": manifest["certification_key"],
            "version": manifest["version_key"],
            "domain": manifest["domain_key"],
            "module_key": manifest["module_key"],
            "module_title": manifest["module_title"],
            "lesson_count": manifest["lesson_count"],
            "question_count": manifest["question_count"],
            "resource_count": manifest["resource_count"],
            "practical_present": manifest["practical_present"],
            "service_desk_present": manifest["service_desk_present"],
            "explain_count": manifest["explain_count"],
            "objective_codes": manifest["objectives"],
            "approved_destination": str(destination),
            "runtime_destinations": runtime_destinations,
            "loader_importer_results": loader_result,
            **totals,
            "classification": classification,
            "validation_result": "VALID",
            "tool_version": "nexus-curriculum-intake/1",
        }
        (temp / "IMPORT_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, destination)
        return receipt

    @staticmethod
    def _verify_archive(destination: Path, package_hash: str) -> None:
        receipt_path = destination / "IMPORT_RECEIPT.json"
        if not receipt_path.is_file():
            raise IntakeError("approved archive receipt is missing", field="receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("package_hash") != package_hash:
            raise IntakeError("approved archive hash does not match inbox package", field="package_hash")
        source_dir = destination / "source"
        if source_dir.is_dir():
            archived_hash = _tree_hash(source_dir)
        else:
            archives = [path for path in destination.glob("*.zip") if path.is_file()]
            if len(archives) != 1:
                raise IntakeError("approved archive does not contain exactly one preserved source", field="approved_source")
            archived_hash = hashlib.sha256(archives[0].read_bytes()).hexdigest()
        if archived_hash != package_hash:
            raise IntakeError("preserved approved source failed its SHA-256 verification", field="package_hash")

    def _remove_inbox_item(self, source: Path) -> None:
        if not _within(source, self.dropbox_dir) or source.parent.resolve() != self.dropbox_dir.resolve():
            raise IntakeError("refusing to remove an item outside the dropbox", field="cleanup")
        if source.is_dir():
            shutil.rmtree(source)
        else:
            source.unlink()

    def _write_report(self, source_name: str, result: dict) -> None:
        report_dir = self.dropbox_dir / ".reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / f"{_slug(source_name) or 'package'}.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _validate_in_scratch_database(self, content: Path, manifest: dict) -> dict:
        """Run real V2 loaders twice against a fresh migrated disposable DB."""
        with tempfile.TemporaryDirectory(prefix="nexus-curriculum-db-") as tmp:
            database = Path(tmp) / "intake.db"
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{database}"
            env["NEXUS_CONTENT_DIR"] = str(content)
            env["NEXUS_MODULE_KEY"] = manifest["module_key"]
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=self.backend_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            script = """
import json, os
from app.database import SessionLocal
from app.models.certification import CertificationModule, ModuleAssessment
from app.services.v2_content_loader import load_module
from seed import seed_service_desk_scenarios
root = os.environ['NEXUS_CONTENT_DIR']
kw = {name: os.path.join(root, folder) for name, folder in {
 'cert_dir':'certifications','objectives_dir':'objectives','curriculum_dir':'curriculum',
 'resources_dir':'resources','interview_prompts_dir':'interview-prompts',
 'questions_dir':'questions','labs_dir':'labs'}.items()}
db = SessionLocal()
try:
 seed_service_desk_scenarios(db)
 db.commit()
 first = load_module(db, commit=True, **kw)
 second = load_module(db, commit=True, **kw)
 if second['created'] or second['updated']:
  raise RuntimeError(f"second V2 loader pass was not idempotent: {second}")
 module = db.query(CertificationModule).filter_by(module_key=os.environ['NEXUS_MODULE_KEY']).one()
 sd = db.query(ModuleAssessment).filter_by(certification_module_id=module.id, assessment_role='service_desk').all()
 references = dict(second['references'])
 references['package_service_desk_unresolved'] = [row.assessment_key for row in sd if not row.service_desk_scenario_id]
 print(json.dumps({'first': first, 'second': second, 'references': references}))
finally:
 db.close()
"""
            completed = subprocess.run(
                [sys.executable, "-c", script], cwd=self.backend_dir, env=env,
                check=True, capture_output=True, text=True,
            )
            return json.loads(completed.stdout.strip().splitlines()[-1])
