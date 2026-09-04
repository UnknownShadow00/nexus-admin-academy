"""Phase 2B student presentation API and progression contract."""

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import QuestionV2Meta
from app.models.grading import PendingGrade
from app.models.v2_progress import V2AssessmentAttempt, V2ExplainSubmission
from app.models.service_desk import ServiceDeskAssignment
from app.routers.v2_curriculum import router
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import module_view, resource_activity
from app.services.v2_progress_service import record_activity

MODULE = "module.aplus.core1.network_services_troubleshooting"
LESSON = "lesson.aplus.network.ports_protocols"


def _ready(db, monkeypatch):
    load_module(db, commit=True)
    student = make_student(db, username="v2_api_student")
    enroll_v2(monkeypatch, student)
    return student, make_client(router)


def test_feature_flag_is_off_by_default(db, monkeypatch):
    monkeypatch.delenv("V2_CURRICULUM_ENABLED", raising=False)
    student = make_student(db, username="v2_flag_off")
    response = make_client(router).get("/api/v2/curriculum", headers=auth_headers(student))
    assert response.status_code == 404
    assert response.json()["detail"] == "This learning experience is not available."


def test_entry_and_module_are_composed_from_loaded_data(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    entry = client.get("/api/v2/curriculum", headers=auth_headers(student))
    assert entry.status_code == 200
    current = entry.json()["data"]["current"]
    assert current["module"]["key"] == "module.aplus.core1.hardware_support"
    assert MODULE in {item["module"]["key"] for item in entry.json()["data"]["modules"]}
    module = client.get(f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student)).json()["data"]
    assert module["lessons"][0]["title"]
    assert module["continue"]["route"].endswith(LESSON)


def test_lesson_returns_markdown_resources_and_no_hidden_grading_data(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    response = client.get(f"/api/v2/curriculum/modules/{MODULE}/lessons/{LESSON}", headers=auth_headers(student))
    assert response.status_code == 200
    lesson = response.json()["data"]["lesson"]
    assert lesson["content_markdown"].strip()
    assert any(resource["required"] for resource in lesson["resources"])
    assert "rubric" not in str(response.json()).lower()
    assert "acceptable_answers" not in str(response.json())


def test_resource_and_lesson_completion_persist_and_move_continue(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    lesson = client.get(f"/api/v2/curriculum/modules/{MODULE}/lessons/{LESSON}", headers=auth_headers(student)).json()["data"]["lesson"]
    resource = next(row for row in lesson["resources"] if row["required"])
    client.post(f"/api/v2/curriculum/modules/{MODULE}/resources/{resource['key']}/activity", json={"opened": True}, headers=auth_headers(student))
    client.post(f"/api/v2/curriculum/modules/{MODULE}/resources/{resource['key']}/activity", json={"completed": True}, headers=auth_headers(student))
    client.post(f"/api/v2/curriculum/modules/{MODULE}/lessons/{LESSON}/complete", headers=auth_headers(student))
    reloaded = client.get(f"/api/v2/curriculum/modules/{MODULE}/lessons/{LESSON}", headers=auth_headers(student)).json()["data"]["lesson"]
    assert reloaded["progress"]["status"] == "completed"
    assert next(row for row in reloaded["resources"] if row["key"] == resource["key"])["completed"] is True


def test_quick_check_uses_bank_supports_short_answer_and_records_attempt(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    module_key = "module.aplus.core1.hardware_support"
    key = "assess.aplus.hardware.qc.platform"
    assessment = client.get(f"/api/v2/curriculum/modules/{module_key}/assessments/{key}", headers=auth_headers(student)).json()["data"]
    assert assessment["questions"]
    assert all("correct_answer" not in question for question in assessment["questions"])
    short = next(question for question in assessment["questions"] if question["type"] == "short_answer")
    meta = db.query(QuestionV2Meta).filter_by(question_id=short["id"]).one()
    response = client.post(
        f"/api/v2/curriculum/modules/{module_key}/assessments/{key}/submit",
        json={"attempt_id": assessment["attempt"]["id"], "answers": {str(short["id"]): meta.acceptable_answers[0]}},
        headers=auth_headers(student),
    )
    assert response.status_code == 200
    result = next(row for row in response.json()["data"]["results"] if row["question_id"] == short["id"])
    assert result["is_correct"] is True
    assert db.query(V2AssessmentAttempt).filter_by(student_id=student.id).count() == 1
    reloaded = client.get(
        f"/api/v2/curriculum/modules/{module_key}/assessments/{key}",
        headers=auth_headers(student),
    ).json()["data"]
    assert reloaded["result"]["attempt_id"] == assessment["attempt"]["id"]
    assert reloaded["result"]["score"] == response.json()["data"]["score"]


def test_explain_submission_is_committed_before_pending_grade(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    prompt = "explain.aplus.network.dns_dhcp"
    response = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt}/submit",
        json={"answer": "I would investigate the workstation carefully and verify the result with the user."},
        headers=auth_headers(student),
    )
    assert response.status_code == 200
    assert response.json()["data"]["state"] == "pending"
    submission = db.query(V2ExplainSubmission).filter_by(student_id=student.id).one()
    job = db.query(PendingGrade).filter_by(submission_ref=f"v2-explain:{submission.id}").one()
    assert submission.submitted_answer == job.submitted_answer
    status = client.get(f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt}", headers=auth_headers(student)).json()["data"]
    assert status["submissions"][0]["message"] == "Your response was saved and is waiting to be graded."
    duplicate = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt}/submit",
        json={"answer": "This accidental duplicate must not be stored."},
        headers=auth_headers(student),
    )
    assert duplicate.status_code == 200
    assert "already saved" in duplicate.json()["data"]["message"]
    assert db.query(V2ExplainSubmission).filter_by(student_id=student.id).count() == 1


def test_service_desk_launch_creates_only_a_validated_existing_system_assignment(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    response = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/service-desk/assess.aplus-core1-network-services-troubleshooting.service_desk/launch",
        headers=auth_headers(student),
    )
    assert response.status_code == 200
    assert response.json()["data"]["launch_url"].startswith("/service-desk/tickets/")
    assert response.json()["data"]["launch_url"].endswith(f"?returnTo=/learning-v2/modules/{MODULE}")
    assert response.json()["data"]["experience_mode"] == "guided"
    assignment = db.query(ServiceDeskAssignment).filter_by(student_id=student.id).one()
    assert assignment.mode == "learning"
    assert assignment.assigned_by.startswith("v2_curriculum:")


def test_module_completion_requires_full_v2_formula_without_legacy_weeks(db, monkeypatch):
    student, _client = _ready(db, monkeypatch)
    initial = module_view(db, student.id, MODULE)
    assert initial["progress"]["module_complete"] is False
    assert initial["progress"]["explain_prompts"]["total"] == 4
    # Completion decisions are entirely V2 activity/reference driven.
    assert "week" not in initial["continue"]["kind"]


def test_continue_walks_every_required_stage_and_optional_resources_do_not_block(db, monkeypatch):
    student, _client = _ready(db, monkeypatch)
    view = module_view(db, student.id, MODULE)

    for lesson in view["lessons"]:
        for resource in lesson["resources"]:
            if resource["required"]:
                resource_activity(
                    db, student.id, MODULE, resource["key"], completed=True
                )
        record_activity(
            db, student_id=student.id, module_key=MODULE,
            activity_type="lesson", ref_key=lesson["key"],
            status="completed", commit=True,
        )
        record_activity(
            db, student_id=student.id, module_key=MODULE,
            activity_type="quick_check", ref_key=lesson["quick_check"]["key"],
            status="passed", passed=True, commit=True,
        )

    view = module_view(db, student.id, MODULE)
    assert view["continue"]["kind"] == "module_quiz"
    assert view["progress"]["module_complete"] is False

    for role, expected_next, status in (
        ("module_quiz", "practical", "passed"),
        ("practical", "service_desk", "completed"),
        ("service_desk", "explain", "passed"),
    ):
        assessment = next(row for row in view["assessments"] if row["role"] == role)
        record_activity(
            db, student_id=student.id, module_key=MODULE,
            activity_type=role, ref_key=assessment["key"], status=status,
            passed=True, commit=True,
        )
        view = module_view(db, student.id, MODULE)
        assert view["continue"]["kind"] == expected_next
        assert view["progress"]["module_complete"] is False

    for prompt in view["explain_prompts"]:
        record_activity(
            db, student_id=student.id, module_key=MODULE,
            activity_type="explain", ref_key=prompt["key"],
            status="passed", passed=True, commit=True,
        )

    complete = module_view(db, student.id, MODULE)
    assert complete["continue"]["kind"] == "complete"
    assert complete["progress"]["module_complete"] is True
    assert complete["progress"]["resources"]["completed"] < complete["progress"]["resources"]["total"]


def test_unknown_module_is_a_student_safe_404(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    response = client.get("/api/v2/curriculum/modules/not-a-module", headers=auth_headers(student))
    assert response.status_code == 404
    assert "not-a-module" not in response.text
