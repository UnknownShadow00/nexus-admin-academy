"""Focused tests for the permanent Nexus V2 curriculum inbox."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
import pytest
import yaml

from app.services.curriculum_intake import (
    CurriculumIntakeProcessor,
    _normalize_question_row,
    _quick_check_rows,
    safe_extract_zip,
)


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


def _plain_overview(package: Path, title: str = "Client Support Workflow") -> None:
    (package / "module_overview.md").write_text(
        f"# Test Certification — Module\n\n## Module title\n{title}\n\nApproved overview prose.\n",
        encoding="utf-8",
    )


def _inline_service_desk(package: Path, *, title: str = "Approval-bound access") -> dict:
    definition = {
        "title": title,
        "mode": "Learning Mode",
        "objectives": ["1.1", "1.2"],
        "ticket": {
            "requester": "New coordinator",
            "complaint": "The approved shared service is missing.",
            "business_impact": "Orientation can continue while access is pending.",
            "initial_priority": "Low/standard request",
            "twist": "Required approval is not yet recorded.",
        },
        "stages": {
            "Investigation": ["Confirm identity and intended access."],
            "Diagnosis": ["Identify missing authorized access."],
            "Remediation": ["Follow the approval and escalation path."],
            "Verification": ["Verify access only after approval."],
            "Documentation": ["Record the pending or completed outcome."],
        },
        "grading_anchors": [
            {"name": "investigation", "weight": 20},
            {"name": "diagnosis", "weight": 20},
            {"name": "safe_action_or_escalation", "weight": 20},
            {"name": "verification", "weight": 20},
            {"name": "documentation", "weight": 20},
        ],
        "correct_failure_behavior": (
            "If approval is unavailable, escalation/pending with a user update is correct; "
            "unauthorized access is not."
        ),
        "hints": ["Check approval.", "Respect the permission boundary.", "Document the handoff."],
    }
    _write_yaml(package / "service_desk.yaml", definition)
    return definition


def _author_friendly_inline_service_desk(package: Path) -> dict:
    definition = {
        "scenario_key": "service_desk.test.device_and_sync",
        "title": "Device and sync symptoms",
        "module_key": "module.test.client_support",
        "objectives": ["1.1", "1.2"],
        "reinforces": ["1.1"],
        "requester": {
            "name": "Jordan Lee",
            "department": "Field Operations",
            "role": "Coordinator",
            "device": "Managed phone",
            "location": "Remote",
        },
        "complaint": "Charging is intermittent and mail is stale.",
        "business_impact": "The user needs reliable mobile access later today.",
        "initial_facts": ["A known-good cable has the same symptom."],
        "stages": [
            {"stage": "Investigation", "expectations": ["Collect both symptom sets."]},
            {"stage": "Diagnosis", "expectations": ["Separate the likely causes."]},
            {"stage": "Remediation", "expectations": ["Use safe authorized actions."]},
            {"stage": "Verification", "expectations": ["Verify both workflows."]},
            {"stage": "Documentation", "expectations": ["Record the outcome."]},
        ],
        "correct_outcomes": [
            "Repair the physical fault and verify sync.",
            "Escalate safely when authority is unavailable.",
        ],
        "incorrect_outcomes": ["Force the damaged connector."],
        "hints": ["Separate symptoms.", "Check authority.", "Verify independently."],
        "grading_anchors": {
            "investigation": "Collects both symptom sets.",
            "diagnosis": "Separates the causes.",
            "remediation": "Uses safe actions.",
            "verification": "Verifies both outcomes.",
            "documentation": "Records the result.",
        },
    }
    _write_yaml(package / "service_desk.yaml", definition)
    return definition


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


def test_package_runtime_validation_ignores_unrelated_baseline_references(intake):
    processor, dropbox, *_ = intake
    _package(dropbox)
    processor.runtime_validator = lambda _content, _manifest: {
        "references": {
            "content_engine_unresolved": ["baseline.optional.quick_check"],
            "package_content_engine_unresolved": [],
        }
    }
    assert processor.process(mode="check")[0]["status"] == "VALID_WITH_NORMALIZATION"


def test_package_runtime_validation_rejects_its_own_unresolved_reference(intake):
    processor, dropbox, *_ = intake
    _package(dropbox)
    processor.runtime_validator = lambda _content, _manifest: {
        "references": {
            "content_engine_unresolved": ["baseline.optional.quick_check"],
            "package_content_engine_unresolved": ["incoming.module_quiz"],
        }
    }
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert "incoming.module_quiz" in result["errors"][0]["message"]


def test_valid_folder_discovery(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    assert processor.discover() == [package]


def test_module_overview_with_frontmatter_still_routes(intake):
    processor, dropbox, *_ = intake
    _package(dropbox)
    result = processor.process(mode="check")[0]
    assert result["manifest"]["certification_key"] == "test_cert"
    assert result["manifest"]["version_key"] == "test_cert_v1"
    assert result["manifest"]["module_key"] == "module.test.client_support"


def test_explicit_lesson_order_works(intake):
    processor, dropbox, *_ = intake
    _package(dropbox)
    assert processor.process(mode="check")[0]["status"] == "VALID_WITH_NORMALIZATION"


def test_numbered_filename_derives_missing_lesson_order(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    lesson = package / "lessons" / "01-evidence.md"
    lesson.write_text(re.sub(r"^lesson_order:.*\n", "", lesson.read_text(), flags=re.MULTILINE))
    result = processor.process(mode="check")[0]
    assert result["status"] == "VALID_WITH_NORMALIZATION"
    assert "01-evidence.md: lesson_order 1 derived from filename prefix" in result["normalizations"]


def test_six_numbered_files_derive_contiguous_sequence(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    original = package / "lessons" / "01-evidence.md"
    template = re.sub(r"^lesson_order:.*\n", "", original.read_text(), flags=re.MULTILINE)
    original.write_text(template)
    for order in range(2, 7):
        (package / "lessons" / f"{order:02d}-evidence.md").write_text(
            template.replace(
                "lesson.test.client_support.evidence",
                f"lesson.test.client_support.evidence_{order}",
            ).replace("title: Collect Evidence", f"title: Collect Evidence {order}")
        )
    result = processor.process(mode="check")[0]
    assert result["status"] == "VALID_WITH_NORMALIZATION"
    assert result["manifest"]["lesson_count"] == 6
    assert sum("derived from filename prefix" in note for note in result["normalizations"]) == 6


def test_explicit_order_conflicting_with_filename_fails(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    lesson = package / "lessons" / "01-evidence.md"
    lesson.write_text(lesson.read_text().replace("lesson_order: 1", "lesson_order: 5"))
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert result["errors"][0]["field"] == "lesson_order"
    assert "conflicting" in result["errors"][0]["message"]


def test_duplicate_derived_lesson_orders_fail(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    lesson = package / "lessons" / "01-evidence.md"
    template = re.sub(r"^lesson_order:.*\n", "", lesson.read_text(), flags=re.MULTILINE)
    lesson.write_text(template)
    (package / "lessons" / "01-duplicate.md").write_text(
        template.replace("lesson.test.client_support.evidence", "lesson.test.client_support.duplicate")
    )
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert "duplicate lesson_order 1" in result["errors"][0]["message"]


def test_missing_order_without_numeric_evidence_fails(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    lesson = package / "lessons" / "01-evidence.md"
    text = re.sub(r"^lesson_order:.*\n", "", lesson.read_text(), flags=re.MULTILINE)
    lesson.rename(package / "lessons" / "evidence.md")
    (package / "lessons" / "evidence.md").write_text(text)
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert result["errors"][0]["field"] == "lesson_order"


def test_derived_order_changes_runtime_copy_not_approved_source(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    lesson = package / "lessons" / "01-evidence.md"
    lesson.write_text(re.sub(r"^lesson_order:.*\n", "", lesson.read_text(), flags=re.MULTILINE))
    result = processor.process(mode="apply")[0]
    approved = Path(result["approved_destination"]) / "source" / "lessons" / "01-evidence.md"
    runtime = next((processor.content_dir / "curriculum").rglob("01-evidence.md"))
    assert "lesson_order:" not in approved.read_text()
    assert "lesson_order: 1" in runtime.read_text()


def test_aggregate_check_reports_independent_component_findings(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox, service_desk=True)

    lesson = package / "lessons" / "01-evidence.md"
    text = re.sub(r"^lesson_order:.*\n", "", lesson.read_text(), flags=re.MULTILINE)
    lesson.unlink()
    (package / "lessons" / "evidence.md").write_text(text)

    rows = _question_rows("module.test.client_support", objective="9.9")
    _write_workbook(package / "questions_and_editorial_review.xlsx", rows)
    resources = yaml.safe_load((package / "resources.yaml").read_text())
    resources["resources"][0]["links"][0]["lesson_key"] = "lesson.unknown"
    _write_yaml(package / "resources.yaml", resources)
    prompts = yaml.safe_load((package / "explain_prompts.yaml").read_text())
    prompts["prompts"][0].pop("objectives")
    _write_yaml(package / "explain_prompts.yaml", prompts)
    (package / "practical.yaml").write_text("practical: [unterminated")
    _write_yaml(package / "service_desk.yaml", {"title": "Inline scenario"})
    _write_yaml(
        package / "module_quiz_blueprint.yaml",
        {
            "title": "Friendly quiz",
            "question_count": 10,
            "pools": [{"objective": "1.1", "choose": 10, "pool": ["Q999"]}],
        },
    )

    result = processor.process(mode="check")[0]
    error_files = {item["file"] for item in result["errors"]}
    assert result["status"] == "INVALID"
    assert result["component_summary"]["questions"]["count"] == 20
    assert result["component_summary"]["resources"]["count"] == 1
    assert {
        "evidence.md",
        "questions_and_editorial_review.xlsx",
        "resources.yaml",
        "explain_prompts.yaml",
        "practical.yaml",
        "service_desk.yaml",
        "module_quiz_blueprint.yaml",
    }.issubset(error_files)


def test_check_categorizes_normalizations_and_blockers(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    lesson = package / "lessons" / "01-evidence.md"
    lesson.write_text(re.sub(r"^lesson_order:.*\n", "", lesson.read_text(), flags=re.MULTILINE))
    result = processor.process(mode="check")[0]
    categories = {item["category"] for item in result["findings"]}
    assert "NORMALIZABLE" in categories
    assert not any(category.startswith("BLOCKING_") for category in categories)


def test_plain_module_overview_routes_from_unanimous_lessons(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package)
    result = processor.process(mode="check")[0]
    assert result["status"] == "VALID_WITH_NORMALIZATION"
    assert result["manifest"]["certification_key"] == "test_cert"
    assert result["manifest"]["version_key"] == "test_cert_v1"
    assert result["manifest"]["domain_key"] == "1.0"
    assert result["manifest"]["module_key"] == "module.test.client_support"


def test_plain_overview_conflicting_lesson_module_keys_fail(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package)
    lesson = package / "lessons" / "01-evidence.md"
    duplicate = package / "lessons" / "02-conflict.md"
    duplicate.write_text(lesson.read_text().replace("module.test.client_support", "module.test.conflict"))
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert result["errors"][0]["field"] == "module_key"
    assert "conflicting" in result["errors"][0]["message"]


def test_plain_overview_conflicting_certification_versions_fail(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package)
    lesson = package / "lessons" / "01-evidence.md"
    duplicate = package / "lessons" / "02-conflict.md"
    duplicate.write_text(lesson.read_text().replace("test_cert_v1", "test_cert_v2"))
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert result["errors"][0]["field"] == "certification_version"


def test_plain_overview_conflicting_domains_fail(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package)
    lesson = package / "lessons" / "01-evidence.md"
    duplicate = package / "lessons" / "02-conflict.md"
    duplicate.write_text(lesson.read_text().replace("domain: '1.0'", "domain: '2.0'"))
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert result["errors"][0]["field"] == "domain"


def test_certification_is_resolved_from_version_hierarchy(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package)
    result = processor.process(mode="check")[0]
    assert result["manifest"]["certification_key"] == "test_cert"
    assert "certification resolved from test_cert_v1 -> test_cert" in result["normalizations"]


def test_plain_markdown_module_title_is_display_metadata(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package, "Friendly Display Title")
    result = processor.process(mode="check")[0]
    assert result["manifest"]["module_title"] == "Friendly Display Title"


def test_plain_overview_with_insufficient_structured_routing_fails(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _plain_overview(package)
    lesson = package / "lessons" / "01-evidence.md"
    text = lesson.read_text()
    for field in ("certification_version", "domain", "module"):
        text = re.sub(rf"^{field}:.*\n", "", text, flags=re.MULTILINE)
    lesson.write_text(text)
    result = processor.process(mode="check")[0]
    assert result["status"] == "INVALID"
    assert result["errors"][0]["field"] in {"certification_version", "domain", "module_key"}


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
    lesson = package / "lessons" / "01-evidence.md"
    lesson.write_text(lesson.read_text().replace("module: module.test.client_support\n", ""))
    # The synthetic provenance has no module key; all structured evidence is now absent.
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


def test_title_case_workbook_headers_and_editorial_values_normalize(tmp_path):
    notes: set[str] = set()
    row = _normalize_question_row(
        {
            "Question ID": "Q001",
            "Type": "single_choice",
            "Objective(s)": "1.1,1.2",
            "Lesson Key": "lesson.test.one",
            "Prompt": "Which action is safe?",
            "Option A": "Collect evidence",
            "Option B": "Guess",
            "Correct Answer": "A",
            "Editorial Status": "EDIT",
            "Provenance": "Reviewed source",
        },
        notes,
    )
    assert row["question_id"] == "Q001"
    assert row["question_type"] == "single"
    assert row["objective_code"] == "1.1,1.2"
    assert row["lesson_id"] == "lesson.test.one"
    assert row["question_text"] == "Which action is safe?"
    assert row["option_a"] == "Collect evidence"
    assert row["correct_answers"] == "A"
    assert row["source_name"] == "Reviewed source"
    assert row["final_validation_status"] == "APPROVED_AFTER_EDIT"

    workbook = openpyxl.Workbook()
    quick = workbook.active
    quick.title = "Quick Checks"
    quick.append(
        ["Lesson Order", "Lesson Key", "Lesson Title", "Quick Check Question IDs", "Count"]
    )
    quick.append([1, "lesson.test.one", "Lesson One", "Q001, Q002", 2])
    path = tmp_path / "questions.xlsx"
    workbook.save(path)
    assert _quick_check_rows(path) == [
        {
            "lesson_order": 1,
            "lesson_key": "lesson.test.one",
            "lesson_title": "Lesson One",
            "question_ids": "Q001, Q002",
            "count": 2,
        }
    ]


def test_plain_text_free_response_rubric_is_wrapped_without_rewriting():
    approved = "Full credit requires safe handling and explicit verification."
    notes: set[str] = set()
    row = _normalize_question_row(
        {
            "Type": "free_response",
            "Prompt": "Explain the safe workflow.",
            "Expected Concepts": "safety; verification",
            "Minimum Concepts": "2 of 2",
            "Rubric": approved,
            "Rubric Version": "reviewed-v1",
        },
        notes,
    )
    assert row["rubric"] == {"approved_text": approved}
    assert row["min_concepts_for_pass"] == 2
    assert "plain-text free-response rubric -> rubric.approved_text" in notes


def test_optional_resource_can_link_to_module_without_lesson(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    resources_path = package / "resources.yaml"
    resources = yaml.safe_load(resources_path.read_text())
    resources["resources"][0]["links"] = [
        {
            "module_key": "module.test.client_support",
            "required": False,
            "order": 99,
        }
    ]
    _write_yaml(resources_path, resources)
    result = processor.process(mode="check")[0]
    assert result["status"].startswith("VALID")
    assert result["component_summary"]["resources"]["lesson_mappings"] == {
        "res.test.client_support.reference": [""]
    }


def test_owner_permitted_resource_label_normalizes_to_loader_enum(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    resources_path = package / "resources.yaml"
    resources = yaml.safe_load(resources_path.read_text())
    resources["resources"][0]["permission_status"] = "owner-permitted third-party"
    _write_yaml(resources_path, resources)
    result = processor.process(mode="check")[0]
    assert result["status"] == "VALID_WITH_NORMALIZATION"
    assert "owner-permitted third-party -> permitted" in result["normalizations"]


def test_plain_text_explain_rubric_preserves_explicit_constraints(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    prompts_path = package / "explain_prompts.yaml"
    prompts = yaml.safe_load(prompts_path.read_text())
    prompt = prompts["prompts"][0]
    prompt["rubric"] = "Passing requires evidence and verification."
    prompt["minimum_concepts"] = 2
    prompt["must_include"] = ["evidence", "verification"]
    _write_yaml(prompts_path, prompts)
    result = processor.process(mode="check")[0]
    assert result["status"] == "VALID_WITH_NORMALIZATION"
    assert any(
        "plain-text rubric and explicit constraints -> rubric metadata" in note
        for note in result["normalizations"]
    )


@pytest.mark.parametrize("missing", ["service_desk", "practical"])
def test_optional_service_desk_and_practical(intake, missing):
    processor, dropbox, *_ = intake
    _package(dropbox, service_desk=False, practical=missing != "practical")
    result = processor.process(mode="check")[0]
    assert result["status"].startswith("VALID")


def test_inline_service_desk_generates_stable_key_and_preserves_definition(intake):
    processor, dropbox, approved, content = intake
    package = _package(dropbox)
    source = _inline_service_desk(package)
    result = processor.process(mode="apply")[0]
    assert result["status"] == "IMPORTED"
    key = result["manifest"]["service_desk_keys"][0]
    assert key == "curriculum-test-client-support-service-desk-01"
    runtime = next((content / "service-desk-scenarios").glob("*.yaml"))
    stored = yaml.safe_load(runtime.read_text())["scenarios"][0]
    assert stored["stable_key"] == key
    assert stored["definition"]["curriculum"]["stages"] == source["stages"]
    assert stored["definition"]["curriculum"]["grading_anchors"] == source["grading_anchors"]
    assert stored["definition"]["successful_professional_outcomes"] == [
        "pending",
        "escalated",
        "handed_off",
    ]
    approved_source = Path(result["approved_destination"]) / "source" / "service_desk.yaml"
    assert yaml.safe_load(approved_source.read_text()) == source


def test_inline_service_desk_key_is_deterministic_and_changed_content_is_detected(intake):
    processor, dropbox, *_ = intake
    package = _package(dropbox)
    _inline_service_desk(package)
    first = processor.process(mode="check")[0]
    key = first["manifest"]["service_desk_keys"][0]
    package.rename(dropbox / "saved")
    second_package = _package(dropbox)
    _inline_service_desk(second_package, title="Changed approved title")
    second = processor.process(mode="check")
    changed = next(row for row in second if row["source"] == second_package.name)
    assert changed["manifest"]["service_desk_keys"] == [key]
    assert first["package_hash"] != changed["package_hash"]


def test_author_friendly_inline_service_desk_with_explicit_key_is_promoted(intake):
    processor, dropbox, approved, content = intake
    package = _package(dropbox)
    source = _author_friendly_inline_service_desk(package)

    checked = processor.process(mode="check")[0]
    assert checked["status"] == "VALID_WITH_NORMALIZATION"
    assert checked["manifest"]["service_desk_keys"] == [source["scenario_key"]]
    assert checked["component_summary"]["service_desk"]["rubric_dimensions"] == [
        "Investigation",
        "Diagnosis",
        "Remediation",
        "Verification",
        "Documentation",
    ]

    applied = processor.process(mode="apply")[0]
    assert applied["status"] == "IMPORTED"
    runtime = next((content / "service-desk-scenarios").glob("*.yaml"))
    stored = yaml.safe_load(runtime.read_text())["scenarios"][0]
    assert stored["stable_key"] == source["scenario_key"]
    assert stored["definition"]["curriculum"] == source
    assert stored["definition"]["successful_professional_outcomes"] == source[
        "correct_outcomes"
    ]
    assert stored["definition"]["grading_anchors"] == source["grading_anchors"]
    approved_source = Path(applied["approved_destination"]) / "source" / "service_desk.yaml"
    assert yaml.safe_load(approved_source.read_text()) == source


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
