"""Content integrity and disposable learner journey for the new beginner path."""

from datetime import date, timedelta
from pathlib import Path
import re

import yaml

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import (
    CertificationModule, LearningResource, LearningResourceLink, LessonV2Meta,
    ModuleAssessment,
)
from app.models.flashcard import FlashcardReview
from app.models.quiz import Question, Quiz
from app.models.v2_evidence import V2EvidenceRequirement
from app.models.v2_interaction import V2InteractionDefinition
from app.routers.flashcards import router as flashcards_router
from app.routers.v2_curriculum import router
from app.services.v2_beginner_path import STAGE_KEYS
from app.services.v2_content_loader import load_module, valid_external_url
from app.services.v2_curriculum_service import entry_view, resource_activity
from app.services.v2_interaction_loader import load_interactions
from app.services.v2_interaction_service import validate_definition
from app.services.v2_progress_service import module_progress, record_activity
from app.services.question_validation import validate_question_row

ROOT = Path(__file__).resolve().parents[1]
INTERACTIONS = ROOT / "content/interactions/nexus-beginner-aplus-v1.yaml"
API = "/api/v2/curriculum/modules"


def _load(db):
    load_module(db, commit=True)
    load_interactions(db, path=str(INTERACTIONS), commit=True)


def _correct_interaction_response(definition):
    config = definition.config
    if definition.interaction_type == "matching":
        return {"matches": {pair["id"]: pair["right_id"] for pair in config["pairs"]}}
    if definition.interaction_type == "ordering":
        return {"order": [step["id"] for step in config["steps"]]}
    if definition.interaction_type == "typed_answer":
        return {"answer": config["accepted_answers"][0]}
    return {"choice_id": config["correct_choice_id"]}


def _submit_check(client, student, db, module_key, assessment_key, *, fail_first=False):
    url = f"{API}/{module_key}/assessments/{assessment_key}"
    headers = auth_headers(student)
    opened = client.get(url, headers=headers)
    assert opened.status_code == 200, opened.text
    attempt = opened.json()["data"]
    if fail_first:
        wrong = {str(q["id"]): "Z" for q in attempt["questions"]}
        failed = client.post(url + "/submit", json={"attempt_id": attempt["attempt"]["id"], "answers": wrong}, headers=headers)
        assert failed.status_code == 200, failed.text
        assert failed.json()["data"]["passed"] is False
        assert module_progress(db, student.id, module_key)["module_complete"] is False
        attempt = client.post(url + "/attempts", headers=headers).json()["data"]
    answers = {
        str(q["id"]): ",".join(db.get(Question, q["id"]).all_correct_answers)
        for q in attempt["questions"]
    }
    passed = client.post(url + "/submit", json={"attempt_id": attempt["attempt"]["id"], "answers": answers}, headers=headers)
    assert passed.status_code == 200, passed.text
    assert passed.json()["data"]["score"] == 100
    assert passed.json()["data"]["passed"] is True


def test_beginner_content_loads_on_existing_systems_and_is_pedagogically_bounded(db, monkeypatch):
    _load(db)
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
    assert len(authored) == 10
    assert len({(row["key"], row["version"]) for row in authored}) == len(authored)
    assert {row["type"] for row in authored} == {
        "matching", "image_identification", "ordering", "command_output",
        "typed_answer", "safe_action",
    }
    for definition in authored:
        validate_definition(definition)
    assert sum(row["required"] for row in authored) == 9

    all_student_text = []
    for module_key in STAGE_KEYS:
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


def test_disposable_student_retries_and_unlocks_stages_in_order(db, monkeypatch):
    _load(db)
    student = make_student(db, username="beginner_journey")
    enroll_v2(monkeypatch, student)
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    client = make_client(router, flashcards_router)
    headers = auth_headers(student)
    assert client.get(f"{API}/{STAGE_KEYS[1]}", headers=headers).status_code == 403
    assert "Finish Stage 1" in client.get(f"{API}/{STAGE_KEYS[1]}", headers=headers).json()["detail"]
    assert entry_view(db, student.id)["current"]["module"]["key"] == STAGE_KEYS[0]

    for stage_index, module_key in enumerate(STAGE_KEYS):
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
        if stage_index < 2:
            assert entry_view(db, student.id)["current"]["module"]["key"] == STAGE_KEYS[stage_index + 1]
            assert client.get(f"{API}/{STAGE_KEYS[stage_index + 1]}", headers=headers).status_code == 200

    # The optional command-output preview was never attempted and did not block Stage 3.
    assert db.query(V2EvidenceRequirement).filter_by(ref_key="interaction.nexus.beginner.s3.whoami_preview").one().is_required is False
    optional = next(item for item in module_progress(db, student.id, STAGE_KEYS[1])["resources"]["items"] if item["resource_key"] == "res.nexus.beginner.s2.hardware_software_recap")
    assert optional["required"] is False and optional["exposure_satisfied"] is False
    assert all(module_progress(db, student.id, key)["module_complete"] for key in STAGE_KEYS)
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
