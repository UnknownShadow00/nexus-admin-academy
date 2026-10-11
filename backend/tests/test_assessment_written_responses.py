"""Phase 3 assessment policy; real handlers/ORM, disposable test database only."""
import pytest
from conftest import auth_headers, enroll_v2, make_client, make_student
from app.models.grading import PendingGrade
from app.models.v2_progress import V2AssessmentAttempt, V2AssessmentAttemptQuestion
from app.models.xp_ledger import XPLedger
from app.routers.v2_curriculum import router
from app.services.deterministic_grader import grade_assessment_written_response, grade_short_answer
from app.services.grading_queue import apply_mentor_override
from app.services.v2_content_loader import load_module


def test_assessment_policy_does_not_change_other_grading_callers():
    assert grade_short_answer("The answer is port 443", ["443"])["passed"] is True
    assert grade_assessment_written_response("It is not port 443", question_type="short_answer", acceptable_answers=["443"])["passed"] is None


@pytest.mark.parametrize("wording", ["It hands out the network settings", "leases addresses", "  It supplies connection details.\nI would check the lease.  "])
def test_unmatched_wording_is_not_an_automatic_failure(wording):
    result = grade_assessment_written_response(wording, question_type="short_answer", acceptable_answers=["DHCP"])
    assert result["status"] == "needs_review" and result["passed"] is None


@pytest.mark.parametrize("given,accepted,passed", [("443", ["443"], True), ("8080", ["443"], False), ("ipconfig", ["ipconfig"], True), ("ping", ["ipconfig"], False), ("", ["DHCP"], False)])
def test_unambiguous_answers_still_have_real_grades(given, accepted, passed):
    assert grade_assessment_written_response(given, question_type="short_answer", acceptable_answers=accepted)["passed"] is passed


@pytest.mark.parametrize("wording", ["lease", "I would compare the workstation settings", "DHCP supplies settings but the other concept is differently worded", "DHCP is not used here and DNS does not resolve names", "DHCP prints pages and DNS deletes documents"])
def test_incomplete_or_ambiguous_concept_matching_waits_for_review(wording):
    result = grade_assessment_written_response(wording, question_type="free_response", expected_concepts=["DHCP", "DNS"])
    assert result["passed"] is None and result["status"] == "needs_review"


def assessment(db, monkeypatch):
    load_module(db, commit=True)
    student = make_student(db, username="phase3_written")
    enroll_v2(monkeypatch, student)
    client = make_client(router)
    path = "/api/v2/curriculum/modules/module.aplus.core1.hardware_support/assessments/assess.aplus.hardware.qc.platform"
    data = client.get(path, headers=auth_headers(student)).json()["data"]
    short = next(item for item in data["questions"] if item["type"] == "short_answer")
    return student, client, path, data, short


def test_submission_preserves_wording_pending_is_idempotent_and_cannot_award_mastery(db, monkeypatch):
    student, client, path, data, short = assessment(db, monkeypatch)
    original = "  The platform brings the parts together so they can communicate.\nI would examine the connectors.  "
    before_xp = db.query(XPLedger).count()
    payload = {"attempt_id": data["attempt"]["id"], "answers": {str(short["id"]): original}}
    response = client.post(path + "/submit", json=payload, headers=auth_headers(student))
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["grading_state"] == "pending" and result["score"] is None and result["passed"] is not True
    assert all(not row["correct_answer"] and not row["explanation"] for row in result["results"])
    row = db.query(V2AssessmentAttemptQuestion).filter_by(attempt_id=data["attempt"]["id"], question_id=short["id"]).one()
    job = db.get(PendingGrade, row.pending_grade_id)
    assert row.submitted_answer == job.submitted_answer == original
    assert db.query(XPLedger).count() == before_xp
    duplicate = client.post(path + "/submit", json=payload, headers=auth_headers(student))
    assert duplicate.json()["data"] == result
    assert db.query(PendingGrade).filter_by(student_id=student.id).count() == 1
    other = make_student(db, username="phase3_other")
    enroll_v2(monkeypatch, other)
    assert client.post(path + "/submit", json=payload, headers=auth_headers(other)).status_code == 404
    other_data = client.get(path, headers=auth_headers(other)).json()["data"]
    assert "result" not in other_data
    assert original not in str(other_data)
    # Existing mentor override/reconciliation resolves the real stored question.
    apply_mentor_override(db, job, override_score=1.0, override_passed=True, reason="Verified conceptual explanation", mentor_label="phase3-test")
    db.refresh(row)
    assert row.grading_status == "graded" and row.passed is True
    attempt = db.get(V2AssessmentAttempt, data["attempt"]["id"])
    assert attempt.grading_state == "graded"  # unanswered other questions still score zero
    enroll_v2(monkeypatch, student)
    assert client.get(path, headers=auth_headers(student)).json()["data"]["result"]["grading_state"] == "graded"


@pytest.mark.parametrize("answer", ["x" * 10001, "hello\x00world", "hello\x1bworld"])
def test_response_limits_are_validation_not_hidden_keywords(db, monkeypatch, answer):
    student, client, path, data, short = assessment(db, monkeypatch)
    response = client.post(path + "/submit", json={"attempt_id": data["attempt"]["id"], "answers": {str(short["id"]): answer}}, headers=auth_headers(student))
    assert response.status_code == 422
    assert db.query(PendingGrade).count() == 0


def test_disabled_worker_preserves_pending_answer_until_authorized_reconciliation(db, monkeypatch):
    """Real assessment/admin handlers and worker, with no external grading provider."""
    from app.routers.admin_grading import router as admin_router
    from app.services.grading_queue import run_pending_batch

    monkeypatch.setenv("AI_GRADING_ENABLED", "false")
    monkeypatch.setenv("ADMIN_API_KEY", "disposable-worker-regression-key")
    student, _, path, data, short = assessment(db, monkeypatch)
    client = make_client(router, admin_router)
    original = "  I would examine how the platform connects the components.\nThen verify those connections.  "
    attempt_id = data["attempt"]["id"]
    payload = {"attempt_id": attempt_id, "answers": {str(short["id"]): original}}
    before_xp = db.query(XPLedger).count()
    submitted = client.post(path + "/submit", json=payload, headers=auth_headers(student))
    assert submitted.status_code == 200
    assert submitted.json()["data"]["grading_state"] == "pending"

    # The disabled worker can find the durable job, but cannot invent a grade.
    assert run_pending_batch(db) == {"claimed": 1, "needs_review": 1}
    assert run_pending_batch(db) == {"claimed": 0}
    db.expire_all()
    row = db.query(V2AssessmentAttemptQuestion).filter_by(attempt_id=attempt_id, question_id=short["id"]).one()
    job = db.get(PendingGrade, row.pending_grade_id)
    assert job.status == "needs_review" and job.resolved_passed is None
    assert row.submitted_answer == job.submitted_answer == original
    result = client.get(path, headers=auth_headers(student)).json()["data"]["result"]
    assert result["grading_state"] == "pending" and result["score"] is None
    assert all(not item["correct_answer"] and not item["explanation"] for item in result["results"])
    assert db.query(XPLedger).count() == before_xp

    override_path = f"/api/admin/grading/{job.id}/override"
    decision = {"reason": "Verified the original conceptual explanation", "score": 1.0, "passed": True}
    assert client.post(override_path, json=decision, headers=auth_headers(student)).status_code == 403
    assert client.get("/api/admin/grading/queue", headers=auth_headers(student)).status_code == 403
    admin = {"X-Admin-Key": "disposable-worker-regression-key"}
    queue = client.get("/api/admin/grading/queue", headers=admin).json()["data"]
    assert any(item["pending_grade_id"] == job.id for item in queue)
    assert client.post(override_path, json=decision, headers=admin).status_code == 200
    db.expire_all()
    assert db.get(V2AssessmentAttempt, attempt_id).grading_state == "graded"
    assert db.get(PendingGrade, job.id).submitted_answer == original
    assert db.query(XPLedger).count() == before_xp  # Other unanswered questions still prevent a pass.
