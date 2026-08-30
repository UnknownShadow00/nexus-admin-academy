"""Focused tests for the permanent Nexus V2 curriculum inbox."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
import pytest
import yaml

from app.services.curriculum_intake import CurriculumIntakeProcessor, safe_extract_zip


def _write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _frontmatter(meta: dict, body: str) -> str:
    return f"---\n{yaml.safe_dump(meta, sort_keys=False)}---\n\n{body}"


def _registry(content: Path) -> None:
    _write_yaml(
        content / "certifications" / "test-cert.yaml",
        {
            "certification": {
                "cert_key": "test_cert",
                "name": "Test Certification",
                "provider": "Nexus Tests",
            },
            "versions": [
                {
                    "version_key": "test_cert_v1",
                    "label": "Test Certification V1",
                    "exam_codes": ["TEST-1"],
                    "objectives_file": "test-cert-v1.yaml",
                    "domains": [{"domain_key": "1.0", "title": "Support"}],
                    "modules": [],
                }
            ],
        },
    )
    _write_yaml(
        content / "objectives" / "test-cert-v1.yaml",
        {
            "version_key": "test_cert_v1",
            "objectives": [
                {"code": "1.1", "domain_key": "1.0", "text": "Support a client."},
                {"code": "1.2", "domain_key": "1.0", "text": "Verify a solution."},
            ],
        },
    )
    for name in ("curriculum", "questions", "resources", "interview-prompts", "labs"):
        (content / name).mkdir(parents=True, exist_ok=True)


def _question_rows(module_key: str, *, objective: str = "1.1", friendly: bool = True) -> list[dict]:
    rows = []
    for index in range(20):
        rows.append(
            {
                "quiz_title": "Test Client Support — Module Bank",
                "question_type": "single-choice" if friendly else "single",
                "question": f"Which safe action is correct in scenario {index + 1}?",
                "option_a": "Collect evidence",
                "option_b": "Make random changes",
                "correct_answer": "A",
                "explanation": "Collecting evidence supports a controlled diagnosis.",
                "difficulty": 2,
                "tags": "evidence,support",
                "objective": objective,
                "importance": "Job Critical",
                "source_name": "Synthetic test curriculum",
                "permission_status": "owned",
                "module": module_key,
            }
        )
    return rows


def _write_workbook(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    headers = list(rows[0])
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    workbook.save(path)


def _package(
    root: Path,
    *,
    name: str = "client-support",
    module_key: str = "module.test.client_support",
    certification: str = "test_cert",
    version: str = "test_cert_v1",
    objective: str = "1.1",
    practical: bool = True,
    service_desk: bool = False,
    explain: bool = True,
    resources: bool = True,
) -> Path:
    package = root / name
    package.mkdir(parents=True)
    overview = {
        "certification": certification,
        "certification_version": version,
        "domain": "1.0",
        "module_key": module_key,
        "title": "Client Support Workflow",
        "skill_promise": "Use an evidence-led support workflow.",
        "importance": "Job Critical",
        "display_order": 50,
        "editorial_status": "validated",
    }
    (package / "module_overview.md").write_text(
        _frontmatter(overview, "# Client Support Workflow\n\nApproved overview.\n"),
        encoding="utf-8",
    )
    lesson_meta = {
        "lesson_key": "lesson.test.client_support.evidence",
        "title": "Collect Evidence",
        "certification_version": version,
        "domain": "1.0",
        "module": module_key,
        "lesson_order": 1,
        "importance": "Working Knowledge",
        "learning_relationship": "New",
        "objectives": [objective],
        "quick_check": {
            "title": "Quick Check — Evidence",
            "displayed_count": 3,
            "pass_percent": 60,
            "tags_any": ["evidence"],
        },
    }
    body = "## 1. What is this?\n\nDo not rewrite this approved lesson body.\n"
    (package / "lessons").mkdir()
    (package / "lessons" / "01-evidence.md").write_text(
        _frontmatter(lesson_meta, body), encoding="utf-8"
    )
    _write_workbook(
        package / "questions_and_editorial_review.xlsx",
        _question_rows(module_key, objective=objective),
    )
    _write_yaml(
        package / "module_quiz_blueprint.yaml",
        {
            "quiz_title": "Test Client Support — Module Bank",
            "displayed_count": 10,
            "pass_percent": 70,
            "question_blueprint": [{"objective_codes": [objective], "count": 10}],
        },
    )
    _write_yaml(
        package / "provenance.yaml",
        {
            "editorial_status": "validated",
            "reviewed_question_count": 20,
            "source_name": "Synthetic test curriculum",
        },
    )
    if resources:
        _write_yaml(
            package / "resources.yaml",
            {
                "resources": [
                    {
                        "resource_key": "res.test.client_support.reference",
                        "title": "Client Support Reference",
                        "type": "documentation",
                        "provider": "Nexus Tests",
                        "url": "https://example.test/support",
                        "permission_status": "permitted",
                        "links": [
                            {
                                "lesson_key": "lesson.test.client_support.evidence",
                                "required": False,
                            }
                        ],
                    }
                ]
            },
        )
    if explain:
        _write_yaml(
            package / "explain_prompts.yaml",
            {
                "prompts": [
                    {
                        "prompt_key": "interview.test.client_support.evidence",
                        "prompt": "Explain how you collect evidence before making a change.",
                        "objectives": [objective],
                        "importance": "Job Critical",
                        "expected_concepts": ["baseline", "controlled change", "verification"],
                        "rubric": {"pass": "Explains evidence and verification."},
                        "rubric_version": "test-1",
                    }
                ]
            },
        )
    if practical:
        _write_yaml(
            package / "practical.yaml",
            {
                "practical": {
                    "title": "Test Practical — Evidence Record",
                    "description": "Record evidence and verify one safe change.",
                    "difficulty": 1,
                    "required_evidence": {"notes": True},
                    "success_criteria": {"verified": True},
                    "model_solution": "Capture a baseline, change one item, and retest.",
                }
            },
        )
    if service_desk:
        _write_yaml(package / "service_desk.yaml", {"scenario_key": "existing-scenario"})
    return package


def _zip(source: Path, destination: Path) -> Path:
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, f"{source.name}/{path.relative_to(source).as_posix()}")
    return destination


@pytest.fixture()
def intake(tmp_path):
    dropbox = tmp_path / "references" / "curriculum-dropbox"
    approved = tmp_path / "references" / "curriculum-approved"
    content = tmp_path / "backend" / "content"
    dropbox.mkdir(parents=True)
    approved.mkdir(parents=True)
    _registry(content)

    def validator(_content, _manifest):
        return {
            "created": 25,
            "updated": 0,
            "unchanged": 0,
            "references": {"content_engine_unresolved": []},
        }

    processor = CurriculumIntakeProcessor(
        dropbox_dir=dropbox,
        approved_dir=approved,
        content_dir=content,
        backend_dir=tmp_path / "backend",
        runtime_validator=validator,
        service_desk_keys={"existing-scenario"},
    )
    return processor, dropbox, approved, content


def test_empty_dropbox(intake):
    processor, *_ = intake
    assert processor.process(mode="check") == []


def test_valid_folder_discovery(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    assert processor.discover() == [package]


def test_valid_zip_discovery_and_wrapped_root(intake):
    processor, dropbox, *_ = intake
    source = _package(dropbox, name="source")
    archive = _zip(source, dropbox / "module.zip")
    shutil.rmtree(source)
    result = processor.process(mode="check")
    assert [row["source"] for row in result] == [archive.name]
    assert result[0]["status"] == "VALID_WITH_NORMALIZATION"


def test_safe_zip_extraction(tmp_path):
    source = _package(tmp_path, name="safe")
    archive = _zip(source, tmp_path / "safe.zip")
    target = tmp_path / "out"
    safe_extract_zip(archive, target)
    assert (target / "safe" / "module_overview.md").is_file()


def test_zip_traversal_attack_rejected(intake):
    processor, dropbox, *_ = intake
    archive = dropbox / "attack.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr("../escape.txt", "no")
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert "unsafe ZIP member" in result["errors"][0]["message"]


def test_random_invalid_zip_rejected(intake):
    processor, dropbox, *_ = intake
    (dropbox / "bad.zip").write_bytes(b"not a zip")
    assert processor.process(mode="check")[0]["status"] == "INVALID"


def test_missing_required_package_metadata(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    overview = package / "module_overview.md"
    overview.write_text(overview.read_text().replace("module_key: module.test.client_support\n", ""))
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert any(error["field"] == "module_key" for error in result["errors"])


@pytest.mark.parametrize(
    "field,value",
    [("certification", "missing_cert"), ("certification_version", "missing_version")],
)
def test_invalid_certification_or_version(intake, field, value):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    overview = package / "module_overview.md"
    overview.write_text(overview.read_text().replace(f"{field}: test_{'cert' if field == 'certification' else 'cert_v1'}", f"{field}: {value}"))
    assert processor.process(mode="check")[0]["status"] == "INVALID"


def test_invalid_objective(intake):
    processor, dropbox, *_ = intake
    _package(dropbox, objective="9.9")
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert any(error["field"] == "objective" for error in result["errors"])


def test_enum_and_workbook_field_normalization(intake):
    processor, dropbox, *_ = intake
    _package(dropbox)
    result = processor.process(mode="check")[0]
    assert result["status"] == "VALID_WITH_NORMALIZATION"
    assert "Job Critical -> job_critical" in result["normalizations"]
    assert "single-choice -> single" in result["normalizations"]
    assert "question -> question_text" in result["normalizations"]
    assert "objective -> objective_code" in result["normalizations"]


@pytest.mark.parametrize("missing", ["service_desk", "practical"])
def test_optional_service_desk_and_practical(intake, missing):
    processor, dropbox, *_ = intake
    _package(dropbox, service_desk=False, practical=missing != "practical")
    result = processor.process(mode="check")[0]
    assert result["status"].startswith("VALID")


def test_unsupported_service_desk_definition_fails_without_rewriting(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _write_yaml(package / "service_desk.yaml", {"definition": {"title": "New scenario"}})
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert "stable reference" in result["errors"][0]["message"]


def test_success_preserves_approved_package_and_cleans_inbox(intake):
    processor, dropbox, approved, _ = intake
    source = _package(dropbox)
    result = processor.process(mode="apply")[0]
    assert result["status"] == "IMPORTED"
    assert not source.exists()
    destination = Path(result["approved_destination"])
    assert destination.is_dir()
    assert (destination / "source" / "module_overview.md").is_file()
    assert (destination / "IMPORT_RECEIPT.json").is_file()


def test_duplicate_hash_and_identical_rerun_are_idempotent(intake):
    processor, dropbox, *_ = intake
    source = _package(dropbox)
    saved = source.parent.parent / "saved"
    shutil.copytree(source, saved)
    first = processor.process(mode="apply")[0]
    shutil.copytree(saved, dropbox / "client-support")
    second = processor.process(mode="apply")[0]
    assert first["status"] == "IMPORTED"
    assert second["status"] == "UNCHANGED"
    assert not (dropbox / "client-support").exists()


def test_changed_package_requires_explicit_apply_and_preserves_history(intake):
    processor, dropbox, approved, _ = intake
    _package(dropbox)
    processor.process(mode="apply")
    changed = _package(dropbox)
    lesson = changed / "lessons" / "01-evidence.md"
    lesson.write_text(lesson.read_text().replace("approved lesson body", "approved changed body"))
    checked = processor.process(mode="check")[0]
    assert checked["status"] == "CHANGED_REQUIRES_REVIEW"
    blocked = processor.process(mode="apply")[0]
    assert blocked["status"] == "CHANGED_REQUIRES_REVIEW"
    assert changed.exists()
    imported = processor.process(mode="apply", allow_changed=True)[0]
    assert imported["status"] == "IMPORTED"
    module_root = approved / "test_cert" / "test_cert_v1" / "module.test.client_support"
    assert len([path for path in module_root.iterdir() if path.is_dir()]) == 2


def test_failure_keeps_inbox_and_previous_approved_version(intake):
    processor, dropbox, approved, _ = intake
    processor.process(mode="apply") if _package(dropbox) else None
    prior = list(approved.rglob("IMPORT_RECEIPT.json"))
    broken = _package(dropbox)
    (broken / "provenance.yaml").write_text("editorial_status: draft\n")
    result = processor.process(mode="apply", allow_changed=True)[0]
    assert result["status"] == "INVALID"
    assert broken.exists()
    assert list(approved.rglob("IMPORT_RECEIPT.json")) == prior


def test_package_failures_are_isolated_and_multiple_packages_discovered(intake):
    processor, dropbox, *_ = intake
    _package(dropbox, name="good", module_key="module.test.good")
    bad = _package(dropbox, name="bad", module_key="module.test.bad")
    (bad / "provenance.yaml").write_text("editorial_status: draft\n")
    results = processor.process(mode="apply")
    assert {row["source"] for row in results} == {"good", "bad"}
    assert next(row for row in results if row["source"] == "good")["status"] == "IMPORTED"
    assert next(row for row in results if row["source"] == "bad")["status"] == "INVALID"
    assert bad.exists()


def test_no_accidental_curriculum_rewriting(intake):
    processor, dropbox, _, content = intake
    package = _package(dropbox)
    original = (package / "lessons" / "01-evidence.md").read_text().split("---", 2)[2]
    processor.process(mode="apply")
    runtime = next((content / "curriculum").rglob("01-evidence.md"))
    assert runtime.read_text().split("---", 2)[2] == original


def test_approved_directory_not_ignored_and_dropbox_payload_ignored():
    root = Path(__file__).resolve().parents[2]
    ignore = (root / ".gitignore").read_text()
    assert "/references/curriculum-dropbox/*" in ignore
    assert "/references/curriculum-approved" not in ignore


def test_receipt_generation_has_no_student_or_secret_data(intake):
    processor, dropbox, *_ = intake
    _package(dropbox)
    result = processor.process(mode="apply")[0]
    receipt = json.loads((Path(result["approved_destination"]) / "IMPORT_RECEIPT.json").read_text())
    assert receipt["package_hash"] == result["package_hash"]
    assert receipt["lesson_count"] == 1
    assert receipt["question_count"] == 20
    assert "students" not in receipt
    assert "secrets" not in receipt


def test_check_mode_makes_no_permanent_change(intake):
    processor, dropbox, approved, content = intake
    _package(dropbox)
    before = sorted(path.relative_to(content) for path in content.rglob("*") if path.is_file())
    processor.process(mode="check")
    after = sorted(path.relative_to(content) for path in content.rglob("*") if path.is_file())
    assert before == after
    assert not list(approved.rglob("IMPORT_RECEIPT.json"))


def test_receipt_for_zip_preserves_original_archive(intake):
    processor, dropbox, *_ = intake
    source = _package(dropbox, name="zip-source")
    archive = _zip(source, dropbox / "approved-module.zip")
    archive_bytes = archive.read_bytes()
    shutil.rmtree(source)
    result = processor.process(mode="apply")[0]
    preserved = Path(result["approved_destination"]) / "approved-module.zip"
    assert preserved.read_bytes() == archive_bytes


def test_real_v2_loaders_validate_staged_content_twice(tmp_path):
    dropbox = tmp_path / "dropbox"
    approved = tmp_path / "approved"
    content = tmp_path / "content"
    dropbox.mkdir()
    approved.mkdir()
    _registry(content)
    package = _package(dropbox, service_desk=True)
    _write_yaml(package / "service_desk.yaml", {"scenario_key": "inc2403"})
    processor = CurriculumIntakeProcessor(
        dropbox_dir=dropbox,
        approved_dir=approved,
        content_dir=content,
        backend_dir=Path(__file__).resolve().parents[1],
    )

    result = processor.process(mode="check")[0]

    assert result["status"] == "VALID_WITH_NORMALIZATION"
