"""Content integrity and disposable learner journey for the new beginner path."""

from collections import Counter
from datetime import date, timedelta
import hashlib
from pathlib import Path
import re

import pytest
import yaml

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import (
    CertificationModule, CertificationVersion, LearningResource, LearningResourceLink, LessonV2Meta,
    ModuleAssessment,
)
from app.models.flashcard import FlashcardReview
from app.models.quiz import Question, Quiz
from app.models.lab import LabRun, LabTemplate
from app.models.v2_evidence import V2EvidenceRequirement
from app.models.v2_interaction import V2InteractionDefinition
from app.models.v2_continuation import V2BeginnerContinuationGrant
from app.routers.flashcards import router as flashcards_router
from app.routers.v2_curriculum import router
from app.routers.labs import router as labs_router
from app.routers.admin_content import router as admin_content_router
from app.services.v2_beginner_path import STAGE_KEYS
from app.services.v2_content_loader import (
    ContentValidationError, _beginner_question_rows, load_module, valid_external_url,
)
from app.services.v2_curriculum_service import entry_view, resource_activity
from app.services.v2_interaction_loader import load_interactions
from app.services.v2_interaction_service import validate_definition
from app.services.quiz_visibility import v1_student_visible_quiz_filters
from app.services.v2_progress_service import module_progress, record_activity
from app.services.question_validation import validate_question_row

ROOT = Path(__file__).resolve().parents[1]
INTERACTIONS = ROOT / "content/interactions/nexus-beginner-aplus-v1.yaml"
API = "/api/v2/curriculum/modules"


def _disposable_approval_dir(tmp_path):
    """Isolate approved content inside a disposable test DB."""
    questions_dir = tmp_path / "disposable-approved-questions"
    questions_dir.mkdir()
    approvals = []
    for bank in sorted((ROOT / "content/questions").glob("beginner-stage-*.yaml")):
        raw = bank.read_bytes()
        (questions_dir / bank.name).write_bytes(raw)
        source = yaml.safe_load(raw)
        approvals.append({
            "filename": bank.name,
            "quiz_title": source["quiz_title"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "reviewed_question_count": len(source["questions"]),
            "editorial_status": "validated",
            "review_note": "Simulated approval for disposable tests only; no human sign-off",
        })
    (questions_dir / "editorial-approvals.yaml").write_text(
        yaml.safe_dump({"approvals": approvals}), encoding="utf-8"
    )
    return questions_dir


def _load(db, tmp_path):
    load_module(db, commit=True)
    load_module(db, questions_dir=str(_disposable_approval_dir(tmp_path)), commit=True)
    load_interactions(db, path=str(INTERACTIONS), commit=True)


def test_beginner_banks_require_exact_human_approval_bytes(db, tmp_path):
    manifest = yaml.safe_load((ROOT / "content/questions/editorial-approvals.yaml").read_text())
    approvals = {row["filename"]: row for row in manifest["approvals"] if row["filename"].startswith("beginner-stage-")}
    assert set(approvals) == {f"beginner-stage-{stage}.yaml" for stage in range(1, 5)}
    assert {name: row["sha256"] for name, row in approvals.items()} == {
        "beginner-stage-1.yaml": "9812091942edf5885ce2fbb9418ba006be0af8f3f05d9237810e3cd9eeece2ad",
        "beginner-stage-2.yaml": "280ea340a45b6386ecdb536593ee465f1186567cc21c1f9cf7f2cddf948aafb9",
        "beginner-stage-3.yaml": "d4d6c1b500ccabcf0b8e46a0d8a07326072d337848a7fe5998859f35993ad363",
        "beginner-stage-4.yaml": "295fcc93f0d117f1db7b91c9b2371e872d4bd5ebe17e19a428dac946f591cdd0",
    }
    stage4_approval = approvals["beginner-stage-4.yaml"]
    assert stage4_approval == {
        "filename": "beginner-stage-4.yaml",
        "quiz_title": "Nexus Beginner Stage 4 — Checkpoint Bank",
        "sha256": "295fcc93f0d117f1db7b91c9b2371e872d4bd5ebe17e19a428dac946f591cdd0",
        "reviewed_question_count": 15,
        "editorial_status": "validated",
        "reviewed_at": "2026-09-29",
        "review_note": "Human editorial approval — Nexus V2 Phase 3B Stage 4",
    }
    legacy_approvals = [row for row in manifest["approvals"] if not row["filename"].startswith("beginner-stage-")]
    assert len(legacy_approvals) == 15
    assert hashlib.sha256(yaml.safe_dump(legacy_approvals, sort_keys=True, allow_unicode=True).encode()).hexdigest() == (
        "b5a27464907eafa0f59d95db316549b504f10e40f522f4cedb9ff6e5ca8846d0"
    )

    unreviewed = tmp_path / "unreviewed-questions"
    unreviewed.mkdir()
    for stage in range(1, 5):
        bank = ROOT / f"content/questions/beginner-stage-{stage}.yaml"
        (unreviewed / bank.name).write_bytes(bank.read_bytes())
    load_module(db, questions_dir=str(unreviewed), commit=True)
    for stage in range(1, 5):
        bank = yaml.safe_load((ROOT / f"content/questions/beginner-stage-{stage}.yaml").read_text())
        quiz = db.query(Quiz).filter_by(title=bank["quiz_title"]).one()
        assert quiz.status != "published"
        assert quiz.editorial_status != "validated"
        assert quiz.answer_keys_validated is False
        assert quiz.explanations_complete is False
    approved = tmp_path / "approved-questions"
    approved.mkdir()
    for stage in range(1, 5):
        bank = ROOT / f"content/questions/beginner-stage-{stage}.yaml"
        (approved / bank.name).write_bytes(bank.read_bytes())
    (approved / "editorial-approvals.yaml").write_text(
        yaml.safe_dump({"approvals": list(approvals.values())}, allow_unicode=True), encoding="utf-8"
    )
    load_module(db, questions_dir=str(approved), commit=True)
    for stage in range(1, 5):
        bank = yaml.safe_load((ROOT / f"content/questions/beginner-stage-{stage}.yaml").read_text())
        quiz = db.query(Quiz).filter_by(title=bank["quiz_title"]).one()
        assert quiz.status == "published" and quiz.editorial_status == "validated"
        assert quiz.answer_keys_validated and quiz.explanations_complete
        assert quiz.show_in_practice_library is False
        legacy_visible_ids = {
            row[0] for row in db.query(Quiz.id).filter(*v1_student_visible_quiz_filters()).all()
        }
        assert quiz.id not in legacy_visible_ids
        if stage == 4:
            questions = db.query(Question).filter_by(quiz_id=quiz.id).all()
            assert len(questions) == 15
            assert all(question.explanation and len(question.all_correct_answers) == 1 for question in questions)

    changed_bank = approved / "beginner-stage-1.yaml"
    changed_bank.write_bytes(changed_bank.read_bytes() + b"\n# unapproved edit\n")
    with pytest.raises(ContentValidationError, match="content changed after editorial approval"):
        load_module(db, questions_dir=str(approved), commit=True)


@pytest.mark.parametrize("mutation", ["extra_byte", "changed_question"])
def test_stage4_approval_rejects_any_changed_bank_bytes(db, tmp_path, mutation):
    approved = tmp_path / "stage4-mutated-questions"
    approved.mkdir()
    for stage in range(1, 5):
        bank = ROOT / f"content/questions/beginner-stage-{stage}.yaml"
        (approved / bank.name).write_bytes(bank.read_bytes())
    manifest = yaml.safe_load((ROOT / "content/questions/editorial-approvals.yaml").read_text())
    beginner_approvals = [row for row in manifest["approvals"] if row["filename"].startswith("beginner-stage-")]
    (approved / "editorial-approvals.yaml").write_text(
        yaml.safe_dump({"approvals": beginner_approvals}, allow_unicode=True), encoding="utf-8"
    )
    bank = approved / "beginner-stage-4.yaml"
    original = bank.read_bytes()
    if mutation == "extra_byte":
        changed = original + b"\n"
    else:
        assert original.count(b"A named file is absent") == 1
        changed = original.replace(b"A named file is absent", b"A named tile is absent", 1)
    bank.write_bytes(changed)
    assert len(changed) == len(original) + (mutation == "extra_byte")
    if mutation == "changed_question":
        assert sum(left != right for left, right in zip(original, changed)) == 1
    with pytest.raises(ContentValidationError, match="beginner-stage-4.yaml: content changed after editorial approval"):
        load_module(db, questions_dir=str(approved), commit=True)


def test_stage4_approval_rejects_wrong_reviewed_question_count(db, tmp_path):
    approved = tmp_path / "stage4-wrong-count"
    approved.mkdir()
    for stage in range(1, 5):
        bank = ROOT / f"content/questions/beginner-stage-{stage}.yaml"
        (approved / bank.name).write_bytes(bank.read_bytes())
    manifest = yaml.safe_load((ROOT / "content/questions/editorial-approvals.yaml").read_text())
    beginner_approvals = [row.copy() for row in manifest["approvals"] if row["filename"].startswith("beginner-stage-")]
    stage4 = next(row for row in beginner_approvals if row["filename"] == "beginner-stage-4.yaml")
    stage4["reviewed_question_count"] = 14
    (approved / "editorial-approvals.yaml").write_text(
        yaml.safe_dump({"approvals": beginner_approvals}, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(ContentValidationError, match="beginner-stage-4.yaml: reviewed 14 questions but imported 15"):
        load_module(db, questions_dir=str(approved), commit=True)


def test_beginner_answer_positions_are_varied_and_fixed_choice_cannot_pass():
    """Check authored and imported order for new banks only, not legacy banks."""
    for stage in range(1, 5):
        path = ROOT / f"content/questions/beginner-stage-{stage}.yaml"
        bank = yaml.safe_load(path.read_text())
        questions = bank["questions"]
        assert len(questions) == 15
        source_positions = [question["answer"] for question in questions]
        imported = _beginner_question_rows(path.read_bytes(), path.name)
        assert len(imported) == len(questions)
        displayed_positions = ["ABCD".index(row["correct_answers"]) for row in imported]
        for positions in (source_positions, displayed_positions):
            counts = Counter(positions)
            assert set(counts) <= {0, 1, 2, 3}
            assert len(counts) >= 3
            assert max(counts.values()) * 2 <= len(questions)

        for question, row in zip(questions, imported):
            letter = row["correct_answers"].lower()
            assert row[f"option_{letter}"] == question["choices"][question["answer"]]

        groups = {question["group"] for question in questions}
        assert len(groups) == 3
        for group in groups:
            indices = [index for index, question in enumerate(questions) if question["group"] == group]
            assert len(indices) == 5
            # Each checkpoint requires 4/5 correct (80%). No fixed choice passes.
            for positions in (source_positions, displayed_positions):
                assert max(Counter(positions[index] for index in indices).values()) < 4


def test_stage4_is_beginner_only_locked_despite_editorial_approval(db, monkeypatch):
    load_module(db, commit=True)
    load_interactions(db, path=str(INTERACTIONS), commit=True)
    student = make_student(db, username="stage4_gate")
    enroll_v2(monkeypatch, student)
    client = make_client(router, labs_router)
    headers = auth_headers(student)
    stage4 = STAGE_KEYS[3]
    module = db.query(CertificationModule).filter_by(module_key=stage4).one()
    assert db.get(CertificationVersion, module.certification_version_id).version_key == "nexus_beginner_aplus_v1"
    assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id, active=True).all()
    assert len(assessments) == 4
    assert {item.assessment_key for item in assessments} == {
        "assess.nexus.beginner.s4.find_protect", "assess.nexus.beginner.s4.access",
        "assess.nexus.beginner.s4.clues", "assess.nexus.beginner.s4.windows_observation",
    }
    bank = yaml.safe_load((ROOT / "content/questions/beginner-stage-4.yaml").read_text())
    assert len(bank["questions"]) == 15
    assert Counter(row["group"] for row in bank["questions"]) == {
        "s4-find-protect": 5, "s4-access": 5, "s4-clues": 5,
    }
    assert all(row["explanation"].strip() for row in bank["questions"])
    manifest = yaml.safe_load((ROOT / "content/questions/editorial-approvals.yaml").read_text())
    assert "beginner-stage-4.yaml" in {row["filename"] for row in manifest["approvals"]}
    quiz = db.query(Quiz).filter_by(title=bank["quiz_title"]).one()
    assert quiz.status == "published" and quiz.editorial_status == "validated"
    assert quiz.answer_keys_validated is True
    assert quiz.explanations_complete is True
    lessons = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).all()
    assert len(lessons) == 3
    links = db.query(LearningResourceLink).filter(LearningResourceLink.lesson_v2_meta_id.in_([row.id for row in lessons])).all()
    assert sum(row.is_required for row in links) == 3
    assert sum(not row.is_required for row in links) == 1
    definitions = db.query(V2InteractionDefinition).filter_by(module_id=module.id).all()
    assert {row.interaction_type for row in definitions} == {"ordering", "safe_action", "matching"}
    assert len(definitions) == 3 and all(row.required for row in definitions)

    practical = next(item for item in assessments if item.assessment_role == "practical")
    lab = db.get(LabTemplate, practical.lab_template_id)
    params = {"v2_module_key": stage4, "v2_assessment_key": practical.assessment_key}
    lab_url = f"/api/labs/{lab.id}"
    legacy = "module.aplus.core1.ip_configuration"
    assert client.get(f"{API}/{legacy}", headers=headers).status_code == 200
    assert stage4 not in {row["module"]["key"] for row in entry_view(db, student.id)["modules"]}
    assert client.get(f"{API}/{stage4}", headers=headers).status_code == 404
    assert client.get(lab_url, params=params, headers=headers).status_code == 404
    assert client.post(lab_url + "/start", params=params, headers=headers).status_code == 404

    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    row = next(row for row in entry_view(db, student.id)["modules"] if row["module"]["key"] == stage4)
    assert row["locked"] is True and row["lock_reason"] == "Finish Stage 1 before starting Stage 4."
    routes = (
        f"{API}/{stage4}",
        f"{API}/{stage4}/lessons/lesson.nexus.beginner.s4.find_protect",
        f"{API}/{stage4}/interactions/interaction.nexus.beginner.s4.find_protect",
        f"{API}/{stage4}/assessments/assess.nexus.beginner.s4.find_protect",
    )
    assert all(client.get(route, headers=headers).status_code == 403 for route in routes)
    assert client.get(lab_url, params=params, headers=headers).status_code == 403
    assert client.post(lab_url + "/start", params=params, headers=headers).status_code == 403


def _correct_interaction_response(definition):
    config = definition.config
    if definition.interaction_type == "matching":
        return {"matches": {pair["id"]: pair["right_id"] for pair in config["pairs"]}}
    if definition.interaction_type == "ordering":
        return {"order": [step["id"] for step in config["steps"]]}
    if definition.interaction_type == "typed_answer":
        return {"answer": config["accepted_answers"][0]}
    return {"choice_id": config["correct_choice_id"]}


def _submit_check(client, student, db, module_key, assessment_key, *, fail_first=False, one_miss=False):
    url = f"{API}/{module_key}/assessments/{assessment_key}"
    headers = auth_headers(student)
    opened = client.get(url, headers=headers)
    assert opened.status_code == 200, opened.text
    attempt = opened.json()["data"]
    if fail_first:
        wrong = {
            str(q["id"]): "Z" if index < 2 else ",".join(db.get(Question, q["id"]).all_correct_answers)
            for index, q in enumerate(attempt["questions"])
        }
        failed = client.post(url + "/submit", json={"attempt_id": attempt["attempt"]["id"], "answers": wrong}, headers=headers)
        assert failed.status_code == 200, failed.text
        assert failed.json()["data"]["passed"] is False
        assert failed.json()["data"]["score"] == 60
        assert module_progress(db, student.id, module_key)["module_complete"] is False
        attempt = client.post(url + "/attempts", headers=headers).json()["data"]
    answers = {
        str(q["id"]): ",".join(db.get(Question, q["id"]).all_correct_answers)
        for q in attempt["questions"]
    }
    if one_miss:
        answers[str(attempt["questions"][0]["id"])] = "Z"
    passed = client.post(url + "/submit", json={"attempt_id": attempt["attempt"]["id"], "answers": answers}, headers=headers)
    assert passed.status_code == 200, passed.text
    assert passed.json()["data"]["score"] == (80 if one_miss else 100)
    assert passed.json()["data"]["passed"] is True


def test_beginner_content_loads_on_existing_systems_and_is_pedagogically_bounded(db, monkeypatch, tmp_path):
    _load(db, tmp_path)
    repeat = load_module(db, commit=True)
    assert repeat["created"] == repeat["updated"] == 0
    assert load_interactions(db, path=str(INTERACTIONS), commit=True)["created"] == 0
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    student = make_student(db, username="beginner_content_audit")
    modules = db.query(CertificationModule).filter(CertificationModule.module_key.in_(STAGE_KEYS)).all()
    assert {module.module_key for module in modules} == set(STAGE_KEYS)
    assert [module.module_key for module in sorted(modules, key=lambda row: row.display_order)] == list(STAGE_KEYS)

    authored = yaml.safe_load(INTERACTIONS.read_text())["interactions"]
    cert = yaml.safe_load((ROOT / "content/certifications/nexus_beginner_aplus.yaml").read_text())
    resources = yaml.safe_load((ROOT / "content/resources/nexus-beginner-aplus-v1.yaml").read_text())["resources"]
    lesson_keys = [
        re.search(r"^lesson_key: (.+)$", path.read_text(), re.MULTILINE).group(1)
        for path in (ROOT / "content/curriculum/nexus-beginner-aplus-v1").rglob("*.md")
    ]
    stable_keys = (
        [row["module_key"] for row in cert["versions"][0]["modules"]]
        + [row["assessment_key"] for module in cert["versions"][0]["modules"] for row in module["assessments"]]
        + [row["resource_key"] for row in resources]
        + lesson_keys
        + [row["key"] for row in authored]
    )
    assert len(stable_keys) == len(set(stable_keys))
    assert len(authored) == 13
    assert len({(row["key"], row["version"]) for row in authored}) == len(authored)
    assert {row["type"] for row in authored} == {
        "matching", "image_identification", "ordering", "command_output",
        "typed_answer", "safe_action",
    }
    for definition in authored:
        validate_definition(definition)
    assert sum(row["required"] for row in authored) == 12

    all_student_text = []
    for module_key in STAGE_KEYS[:3]:
        module = next(row for row in modules if row.module_key == module_key)
        lessons = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).all()
        assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id, active=True).all()
        definitions = db.query(V2InteractionDefinition).filter_by(module_id=module.id, status="published").all()
        links = db.query(LearningResourceLink).filter(
            LearningResourceLink.lesson_v2_meta_id.in_([lesson.id for lesson in lessons])
        ).all()
        assert len(lessons) == len(assessments) == 3
        assert len(definitions) >= 3
        assert sum(link.is_required for link in links) == 3
        assert sum(not link.is_required for link in links) == (1 if module_key == STAGE_KEYS[1] else 0)
        assert all(valid_external_url(db.get(LearningResource, link.resource_id).url) for link in links)
        assert all(assessment.pass_percent == 80 for assessment in assessments)
        assert {assessment.assessment_role for assessment in assessments} == {"quick_check", "module_quiz"}
        assert all(assessment.quiz_id and assessment.displayed_count == 5 for assessment in assessments)
        for assessment in assessments:
            quiz = db.get(Quiz, assessment.quiz_id)
            assert quiz.status == "published" and quiz.answer_keys_validated and quiz.explanations_complete
            tag = assessment.config["tags_any"][0]
            questions = db.query(Question).filter_by(quiz_id=quiz.id).all()
            selected = [question for question in questions if tag in (question.tags or [])]
            assert len(selected) == 5
            assert all(question.explanation and len(question.all_correct_answers) == 1 for question in selected)
            assert all(validate_question_row(question).valid for question in selected)
        required = [row for row in definitions if row.required]
        assert len(required) == 3
        requirements = db.query(V2EvidenceRequirement).filter_by(module_id=module.id, evidence_type="interaction", active=True).all()
        assert {row.ref_key for row in requirements if row.is_required} == {row.interaction_key for row in required}
        assert module_progress(db, student.id, module_key)["module_complete"] is False
        all_student_text += [lesson.content_body for lesson in lessons]
    assert sum("review-core" in (question.tags or []) for question in db.query(Question).all()) == 10
    for bank in (ROOT / "content/questions").glob("beginner-stage-*.yaml"):
        for question in yaml.safe_load(bank.read_text())["questions"]:
            all_student_text.extend([question["text"], question["explanation"], *question["choices"]])
    for interaction in authored:
        all_student_text.extend([interaction["title"], interaction["instructions"], str(interaction["config"])])
    assert not re.search(r"\b(cisco|dns|dhcp|nic|bios|uefi|registry|msp|vpn|cli|domain|directory)\b|root cause|ip address", " ".join(all_student_text), re.IGNORECASE)
    first = STAGE_KEYS[0]
    first_module = next(module for module in modules if module.module_key == first)
    first_lessons = db.query(LessonV2Meta).filter_by(certification_module_id=first_module.id).all()
    for lesson in first_lessons:
        link = db.query(LearningResourceLink).filter_by(lesson_v2_meta_id=lesson.id, is_required=True).one()
        resource_activity(db, student.id, first, db.get(LearningResource, link.resource_id).resource_key, opened=True)
        record_activity(db, student_id=student.id, module_key=first, activity_type="lesson", ref_key=lesson.lesson_key, status="completed", commit=True)
    assert module_progress(db, student.id, first)["module_complete"] is False
    assert module_progress(db, student.id, first)["next_action"] == "Try interactive practice"
    assert [item["module"]["key"] for item in entry_view(db, student.id)["modules"]] == list(STAGE_KEYS)


def test_disposable_student_retries_and_unlocks_stages_in_order(db, monkeypatch, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, username="beginner_journey")
    enroll_v2(monkeypatch, student)
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    client = make_client(router, flashcards_router)
    headers = auth_headers(student)
    assert client.get(f"{API}/{STAGE_KEYS[1]}", headers=headers).status_code == 403
    assert "Finish Stage 1" in client.get(f"{API}/{STAGE_KEYS[1]}", headers=headers).json()["detail"]
    assert entry_view(db, student.id)["current"]["module"]["key"] == STAGE_KEYS[0]

    for stage_index, module_key in enumerate(STAGE_KEYS[:3]):
        module_response = client.get(f"{API}/{module_key}", headers=headers)
        assert module_response.status_code == 200, module_response.text
        if stage_index == 0:
            assert module_response.json()["data"]["continue"]["kind"] == "resource"
        lessons = module_response.json()["data"]["lessons"]
        assert len(lessons) == 3
        for group_index, lesson in enumerate(lessons):
            detail = client.get(f"{API}/{module_key}/lessons/{lesson['key']}", headers=headers).json()["data"]
            assert detail["lesson"]["content_markdown"].strip()
            resource = next(item for item in detail["lesson"]["resources"] if item["required"])
            opened = client.post(f"{API}/{module_key}/resources/{resource['key']}/activity", json={"opened": True}, headers=headers)
            assert opened.status_code == 200, opened.text
            assert module_progress(db, student.id, module_key)["module_complete"] is False
            interaction = next(item for item in detail["interactions"] if item["interaction"]["required"])
            key = interaction["interaction"]["key"]
            url = f"{API}/{module_key}/interactions/{key}"
            if stage_index == 0 and group_index == 0:
                next_step = client.get(f"{API}/{module_key}", headers=headers).json()["data"]["continue"]
                assert next_step["kind"] == "interaction" and next_step["route"].endswith(key)
            public = client.get(url, headers=headers).json()["data"]["interaction"]
            definition = db.get(V2InteractionDefinition, public["version_id"])
            if stage_index == 0 and group_index == 0:
                wrong_matches = _correct_interaction_response(definition)["matches"]
                wrong_matches["hardware"], wrong_matches["software"] = wrong_matches["software"], wrong_matches["hardware"]
                failed = client.post(url + "/submit", json={
                    "version_id": definition.id, "response": {"matches": wrong_matches},
                }, headers=headers)
                assert failed.status_code == 200
                assert failed.json()["data"]["submission_result"]["passed"] is False
                assert client.get(f"{API}/{STAGE_KEYS[1]}", headers=headers).status_code == 403
            passed = client.post(url + "/submit", json={
                "version_id": definition.id, "response": _correct_interaction_response(definition),
            }, headers=headers)
            assert passed.status_code == 200, passed.text
            assert passed.json()["data"]["submission_result"]["passed"] is True
            if stage_index == 0 and group_index == 0:
                next_step = client.get(f"{API}/{module_key}", headers=headers).json()["data"]["continue"]
                assert next_step["kind"] == "quick_check"
            if lesson["quick_check"]:
                _submit_check(client, student, db, module_key, lesson["quick_check"]["key"], fail_first=stage_index == 0 and group_index == 0)
                if stage_index == 0 and group_index == 0:
                    due = client.get("/api/flashcards/due", headers=headers).json()["data"]
                    assert 1 <= len(due) <= 5
                    assert all("review-core" in (db.get(Question, card["question_id"]).tags or []) for card in due)
        quiz = next(item for item in module_response.json()["data"]["assessments"] if item["role"] == "module_quiz")
        _submit_check(client, student, db, module_key, quiz["key"])
        assert module_progress(db, student.id, module_key)["module_complete"] is True
        assert module_progress(db, student.id, module_key)["continuation_granted"] is True
        if stage_index < 2:
            assert entry_view(db, student.id)["current"]["module"]["key"] == STAGE_KEYS[stage_index + 1]
            assert client.get(f"{API}/{STAGE_KEYS[stage_index + 1]}", headers=headers).status_code == 200
            if stage_index == 1:
                still_locked = client.get(f"{API}/{STAGE_KEYS[3]}", headers=headers)
                assert still_locked.status_code == 403
                assert "Finish Stage 3" in still_locked.json()["detail"]

    # The optional command-output preview was never attempted and did not block Stage 3.
    assert db.query(V2EvidenceRequirement).filter_by(ref_key="interaction.nexus.beginner.s3.whoami_preview").one().is_required is False
    optional = next(item for item in module_progress(db, student.id, STAGE_KEYS[1])["resources"]["items"] if item["resource_key"] == "res.nexus.beginner.s2.hardware_software_recap")
    assert optional["required"] is False and optional["exposure_satisfied"] is False
    assert all(module_progress(db, student.id, key)["module_complete"] for key in STAGE_KEYS[:3])
    assert entry_view(db, student.id)["current"]["module"]["key"] == STAGE_KEYS[3]
    cards = db.query(FlashcardReview).filter_by(student_id=student.id).all()
    assert len(cards) == 10
    assert any(card.due_date == date.today() for card in cards)
    assert any(card.due_date == date.today() + timedelta(days=1) for card in cards)
    preview_key = "interaction.nexus.beginner.s3.whoami_preview"
    preview_url = f"{API}/{STAGE_KEYS[2]}/interactions/{preview_key}"
    preview = client.get(preview_url, headers=headers).json()["data"]["interaction"]
    result = client.post(preview_url + "/submit", json={
        "version_id": preview["version_id"], "response": {"choice_id": "sam"},
    }, headers=headers)
    assert result.status_code == 200
    assert result.json()["data"]["submission_result"]["passed"] is True
    assert module_progress(db, student.id, STAGE_KEYS[2])["module_complete"] is True

    # Stage 4 is the same path, with a real guided lab as the final gate.
    stage4 = STAGE_KEYS[3]
    stage4_view = client.get(f"{API}/{stage4}", headers=headers)
    assert stage4_view.status_code == 200
    assert len(stage4_view.json()["data"]["lessons"]) == 3
    assert {item["role"] for item in stage4_view.json()["data"]["assessments"]} == {"quick_check", "module_quiz", "practical"}
    for index, lesson in enumerate(stage4_view.json()["data"]["lessons"]):
        detail = client.get(f"{API}/{stage4}/lessons/{lesson['key']}", headers=headers).json()["data"]
        resource = next(item for item in detail["lesson"]["resources"] if item["required"])
        visit = client.post(f"{API}/{stage4}/resources/{resource['key']}/activity", json={"opened": True}, headers=headers)
        assert visit.status_code == 200 and visit.json()["data"]["status"] == "viewed"
        opened = client.get(f"{API}/{stage4}/lessons/{lesson['key']}", headers=headers).json()["data"]
        required_resource = next(item for item in opened["lesson"]["resources"] if item["required"])
        assert required_resource["status"] == "viewed" and required_resource["exposure_satisfied"] is True
        assert opened["lesson"]["group_status"] == "viewed"
        assert client.get(f"{API}/{stage4}", headers=headers).json()["data"]["lessons"][index]["group_status"] == "viewed"
        assert module_progress(db, student.id, stage4)["groups"]["items"][index]["complete"] is False
        public = next(item for item in detail["interactions"] if item["interaction"]["required"])["interaction"]
        key = public["key"]
        url = f"{API}/{stage4}/interactions/{key}"
        definition = db.get(V2InteractionDefinition, public["version_id"])
        correct = _correct_interaction_response(definition)
        if definition.interaction_type == "ordering":
            wrong = {"order": list(reversed(correct["order"]))}
        elif definition.interaction_type == "matching":
            wrong_matches = dict(correct["matches"])
            pair_ids = list(wrong_matches)
            wrong_matches[pair_ids[0]], wrong_matches[pair_ids[1]] = wrong_matches[pair_ids[1]], wrong_matches[pair_ids[0]]
            wrong = {"matches": wrong_matches}
        else:
            wrong = {"choice_id": "borrow"}
        failed = client.post(url + "/submit", json={"version_id": definition.id, "response": wrong}, headers=headers)
        assert failed.status_code == 200 and failed.json()["data"]["submission_result"]["passed"] is False
        passed = client.post(url + "/submit", json={"version_id": definition.id, "response": correct}, headers=headers)
        assert passed.status_code == 200 and passed.json()["data"]["submission_result"]["passed"] is True
        if lesson["quick_check"]:
            _submit_check(client, student, db, stage4, lesson["quick_check"]["key"], fail_first=index == 0, one_miss=index == 1)
        assert module_progress(db, student.id, stage4)["groups"]["items"][index]["status"] == "completed"
    final = next(item for item in stage4_view.json()["data"]["assessments"] if item["role"] == "module_quiz")
    _submit_check(client, student, db, stage4, final["key"])
    assert module_progress(db, student.id, stage4)["module_complete"] is False
    assert module_progress(db, student.id, stage4)["next_action"] == "Apply your learning"
    assert module_progress(db, student.id, stage4)["continuation_granted"] is False
    optional = next(item for item in module_progress(db, student.id, stage4)["resources"]["items"] if item["resource_key"] == "res.nexus.beginner.s4.note_recap")
    assert optional["required"] is False and optional["exposure_satisfied"] is False

    practical = db.query(ModuleAssessment).filter_by(assessment_key="assess.nexus.beginner.s4.windows_observation").one()
    lab = db.get(LabTemplate, practical.lab_template_id)
    assert lab.proxmox_template_vmid is None
    assert lab.lab_type == "guided"
    lab_client = make_client(labs_router, admin_content_router)
    params = {"v2_module_key": stage4, "v2_assessment_key": practical.assessment_key}
    lab_url = f"/api/labs/{lab.id}"
    assert lab_client.get(lab_url, headers=headers).status_code == 404
    started = lab_client.post(lab_url + "/start", params=params, headers=headers)
    assert started.status_code == 200, started.text
    run_id = started.json()["data"]["run_id"]
    guided_note = {"reported": "File not found and browser behaved oddly", "checked": "Own Downloads path and browser window", "found": "Sample file visible; browser open", "verified_or_not_verified": "User has not confirmed the reported behavior", "next_step": "Ask user to confirm; escalate if it repeats"}
    labels = {"reported": "Reported", "checked": "Checked", "found": "Found", "verified_or_not_verified": "Verified / Not verified", "next_step": "Next step"}
    for payload in ({}, {"notes": "Old free-text evidence"}, {"guided_note": {}}):
        missing_note = lab_client.post(lab_url + "/submit", params=params, json=payload, headers=headers)
        assert missing_note.status_code == 400 and missing_note.json()["detail"] == "Complete the Reported field"
    for field, label in labels.items():
        invalid = {**guided_note, field: "  "}
        bad = lab_client.post(lab_url + "/submit", params=params, json={"guided_note": invalid}, headers=headers)
        assert bad.status_code == 400 and bad.json()["detail"] == f"Complete the {label} field"
        missing_key = lab_client.post(lab_url + "/submit", params=params, json={"guided_note": {key: value for key, value in guided_note.items() if key != field}}, headers=headers)
        assert missing_key.status_code == 400 and missing_key.json()["detail"] == f"Complete the {label} field"
    missing_path = lab_client.post(lab_url + "/submit", params=params, json={"guided_note": guided_note}, headers=headers)
    assert missing_path.status_code == 400 and missing_path.json()["detail"] == "Upload a File/path evidence screenshot before submitting"
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    path_upload = lab_client.post(f"/api/labs/{run_id}/evidence", headers=headers, data={"artifact_type": "file_path"}, files={"file": ("path.png", b"test-image", "image/png")})
    assert path_upload.status_code == 200, path_upload.text
    missing_observation = lab_client.post(lab_url + "/submit", params=params, json={"guided_note": guided_note}, headers=headers)
    assert missing_observation.status_code == 400 and missing_observation.json()["detail"] == "Upload a Windows/application observation screenshot before submitting"
    observation_upload = lab_client.post(f"/api/labs/{run_id}/evidence", headers=headers, data={"artifact_type": "windows_observation"}, files={"file": ("application.png", b"test-image", "image/png")})
    assert observation_upload.status_code == 200, observation_upload.text
    submitted = lab_client.post(lab_url + "/submit", params=params, json={"guided_note": guided_note}, headers=headers)
    assert submitted.status_code == 200, submitted.text
    expected_note = "\n".join(f"{label}: {guided_note[field]}" for field, label in labels.items())
    assert submitted.json()["data"]["notes"] == expected_note
    db.expire_all()
    assert db.get(LabRun, run_id).notes == expected_note
    assert submitted.json()["data"]["review"]["status"] == "awaiting_mentor_review"
    assert module_progress(db, student.id, stage4)["practical"]["activity"]["status"] == "needs_review"
    assert module_progress(db, student.id, stage4)["module_complete"] is False
    assert module_progress(db, student.id, stage4)["status"] == "awaiting_mentor_review"
    grant = db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=practical.certification_module_id).one()
    grant_id = grant.id
    assert grant.grant_reason == "requirements_satisfied"
    assert module_progress(db, student.id, stage4)["continuation_granted"] is True
    assert entry_view(db, student.id)["current"]["continue"]["kind"] == "review_pending"
    monkeypatch.setenv("ADMIN_API_KEY", "stage4-review-key")
    admin_headers = {"X-Admin-Key": "stage4-review-key"}
    queue = lab_client.get("/api/admin/labs/runs/review", headers=admin_headers)
    assert queue.status_code == 200
    assert queue.json()["data"][0]["lab_run_id"] == run_id
    assert queue.json()["data"][0]["notes"] == expected_note
    assert queue.json()["data"][0]["status"] == "awaiting_mentor_review"
    assert queue.json()["data"][0]["stage_title"]
    assert set(queue.json()["data"][0]["mentor_rubric"]) == set(lab.success_criteria["mentor_rubric"])
    review_url = f"/api/admin/labs/runs/{run_id}/v2-review"
    assert lab_client.post(review_url, json={"decision": "approve", "feedback": "Needs rubric"}, headers=admin_headers).status_code == 400
    rubric = lab.success_criteria["mentor_rubric"]
    approved = lab_client.post(review_url, json={"decision": "approve", "feedback": "Observed, safe, and redacted", "rubric_results": dict.fromkeys(rubric, True)}, headers=admin_headers)
    assert approved.status_code == 200, approved.text
    assert module_progress(db, student.id, stage4)["module_complete"] is True
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=practical.certification_module_id).one().id == grant_id
    assert entry_view(db, student.id)["current"]["module"]["key"] == stage4
    reopened = lab_client.post(lab_url + "/start", params=params, headers=headers)
    assert reopened.status_code == 200, reopened.text
    assert module_progress(db, student.id, stage4)["module_complete"] is False
    assert module_progress(db, student.id, stage4)["continuation_granted"] is True
    assert lab_client.post(lab_url + "/submit", params=params, json={"guided_note": guided_note}, headers=headers).status_code == 200
    assert module_progress(db, student.id, stage4)["status"] == "awaiting_mentor_review"
    rejected = lab_client.post(review_url, json={"decision": "reject", "feedback": "Please show the application view"}, headers=admin_headers)
    assert rejected.status_code == 200, rejected.text
    assert module_progress(db, student.id, stage4)["status"] == "needs_correction"
    assert module_progress(db, student.id, stage4)["module_complete"] is False
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=practical.certification_module_id).one().id == grant_id
    assert entry_view(db, student.id)["corrections"][0]["feedback"] == "Please show the application view"
    assert lab_client.get(lab_url, params=params, headers=headers).json()["data"]["review"]["status"] == "needs_correction"
    assert lab_client.post(lab_url + "/start", params=params, headers=headers).status_code == 200
    assert module_progress(db, student.id, stage4)["status"] == "needs_correction"
    assert entry_view(db, student.id)["corrections"][0]["feedback"] == "Please show the application view"
    resubmitted = lab_client.post(lab_url + "/submit", params=params, json={"guided_note": guided_note}, headers=headers)
    assert resubmitted.status_code == 200, resubmitted.text
    assert module_progress(db, student.id, stage4)["status"] == "awaiting_mentor_review"
    assert entry_view(db, student.id)["corrections"] == []
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=practical.certification_module_id).count() == 1
    assert lab_client.post(review_url, json={"decision": "approve", "feedback": "Now verified", "rubric_results": dict.fromkeys(rubric, True)}, headers=admin_headers).status_code == 200
    assert module_progress(db, student.id, stage4)["status"] == "mastered"
    assert entry_view(db, student.id)["corrections"] == []
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=practical.certification_module_id).one().id == grant_id
