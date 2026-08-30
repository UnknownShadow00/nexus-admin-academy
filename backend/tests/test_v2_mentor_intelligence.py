"""Phase 2C mentor progress intelligence for the frozen IP module."""

from __future__ import annotations

from conftest import auth_headers, make_client, make_student

from app.models.app_setting import AppSetting
from app.models.certification import InterviewPrompt, LearningResource, StudentResourceActivity
from app.models.grading import PendingGrade
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptGrade,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.training import TrainingWeek
from app.models.v2_progress import V2ExplainSubmission, V2ModuleActivity
from app.routers.admin_v2_mentor import router
from app.services.grading_queue import apply_mentor_override, submit_for_grading
from app.services.v2_content_loader import load_module
from app.services.v2_mentor_service import cohort_progress, module_report
from app.services.v2_progress_service import record_activity

MODULE_KEY = "module.aplus.core1.ip_configuration"


def _loaded(db):
    load_module(db, commit=True)
    return db


def _question(db, text_fragment):
    from app.models.quiz import Question

    return db.query(Question).filter(Question.question_text.contains(text_fragment)).one()


def _quiz_attempt(db, student_id, attempts):
    record_activity(
        db,
        student_id=student_id,
        module_key=MODULE_KEY,
        activity_type="module_quiz",
        ref_key="assess.aplus.ipcfg.module_quiz",
        status="failed",
        score=50,
        passed=False,
        detail={"attempts": attempts},
        merge_detail=False,
        commit=True,
    )


def _miss(question, answer="A"):
    return {
        "question_id": question.id,
        "question_text": question.question_text,
        "student_answer": answer,
        "is_correct": False,
        "correct_answer": question.all_correct_answers,
        "explanation": question.explanation,
    }


def test_report_counts_repeated_misses_and_keeps_objectives_isolated(db):
    _loaded(db)
    student = make_student(db, "mentor_detail")
    dns = _question(db, "What does DNS do?")
    apipa = _question(db, "user's PC has the address 169.254")
    _quiz_attempt(
        db,
        student.id,
        [
            {"attempt_number": 1, "score": 40, "passed": False, "results": [_miss(dns), _miss(apipa)]},
            {"attempt_number": 2, "score": 60, "passed": False, "results": [_miss(dns)]},
        ],
    )

    report = module_report(db, student.id, MODULE_KEY)
    dns_row = next(row for row in report["missed_questions"] if row["question_id"] == dns.id)
    assert dns_row["times_missed"] == 2
    assert dns_row["question_text"] == dns.question_text
    assert dns_row["student_answer"] == "A"
    assert dns_row["correct_answer"]
    assert dns_row["explanation"]
    assert dns_row["objective_text"]
    assert dns_row["topic"] == "DNS troubleshooting"
    assert sum(row["missed_count"] for row in report["weak_objectives"]) == 3
    assert report["current_position"]["title"]


def test_cohort_aggregation_is_student_based_deterministic_and_external_scores_do_not_count(db):
    _loaded(db)
    one = make_student(db, "cohort_one")
    two = make_student(db, "cohort_two")
    three = make_student(db, "cohort_three")
    dns = _question(db, "What does DNS do?")
    apipa = _question(db, "user's PC has the address 169.254")
    _quiz_attempt(db, one.id, [{"attempt_number": 1, "results": [_miss(dns), _miss(apipa)]}])
    _quiz_attempt(db, two.id, [{"attempt_number": 1, "results": [_miss(apipa)]}, {"attempt_number": 2, "results": [_miss(apipa)]}])

    resource = db.query(LearningResource).filter(LearningResource.resource_key.like("res.aplus.ipcfg.%")).first()
    db.add(StudentResourceActivity(student_id=three.id, resource_id=resource.id, completed=True, reported_score=0, confusing_topic="DNS troubleshooting", question_for_mentor="Why can websites fail by name?"))
    db.commit()

    cohort = cohort_progress(db, MODULE_KEY)
    topics = {row["topic"]: row for row in cohort["weak_areas"]}
    assert topics["DHCP and APIPA"]["students_affected"] == 2
    assert topics["DHCP and APIPA"]["total_misses"] == 3
    assert topics["DNS troubleshooting"]["students_affected"] == 1
    assert cohort["suggested_review_topics"][0]["topic"] == "DHCP and APIPA"
    assert cohort["suggested_review_topics"][0]["reason"] == "2 students showing difficulty"
    assert any(note["question_for_mentor"] for note in cohort["student_questions"])
    assert cohort["student_count"] == 3


def test_explain_detail_and_override_history_are_composed(db):
    _loaded(db)
    student = make_student(db, "explain_mentor")
    out = submit_for_grading(
        db,
        student_id=student.id,
        source_type="interview_explain",
        source_key="interview.aplus.ipcfg.what_does_169_254_tell_you",
        submission_ref="v2-explain:test",
        submitted_answer="It uses a fallback when the server does not reply.",
        question_type="interview_explain",
        question_text="Explain APIPA.",
        expected_concepts=["APIPA", "DHCP failure"],
        rubric={"pass": "Connect APIPA to DHCP failure"},
        rubric_version="ipcfg-v1",
    )
    job = db.get(PendingGrade, out["pending_grade_id"])
    apply_mentor_override(db, job, reason="Correct causal explanation.", override_score=0.8, override_passed=True)

    report = module_report(db, student.id, MODULE_KEY)
    item = next(row for row in report["explain_responses"] if row["submission_ref"] == "v2-explain:test")
    assert item["prompt"] == "Explain APIPA."
    assert item["submitted_answer"].startswith("It uses")
    assert item["expected_concepts"] == ["APIPA", "DHCP failure"]
    assert item["resolved"]["grade_source"] == "mentor"
    assert item["mentor_overrides"][0]["reason"] == "Correct causal explanation."
    assert "last_error_message" not in item


def test_deterministically_graded_explain_submission_is_still_visible(db):
    _loaded(db)
    student = make_student(db, "det_explain")
    prompt = db.query(InterviewPrompt).filter_by(
        prompt_key="interview.aplus.ipcfg.what_does_dhcp_do"
    ).one()
    submission = V2ExplainSubmission(
        student_id=student.id, prompt_id=prompt.id,
        submitted_answer="DHCP automatically leases network settings to clients.",
        attempt_number=1,
    )
    db.add(submission)
    db.flush()
    record_activity(
        db, student_id=student.id, module_key=MODULE_KEY,
        activity_type="explain", ref_key=prompt.prompt_key, status="passed",
        score=100, passed=True,
        detail={"submission_id": submission.id, "grading_state": "graded", "score": 100, "passed": True},
        commit=True,
    )

    report = module_report(db, student.id, MODULE_KEY)
    assert len(report["explain_responses"]) == 1
    assert report["explain_responses"][0]["submitted_answer"].startswith("DHCP")
    assert report["explain_responses"][0]["resolved"]["grade_source"] == "deterministic"


def test_focus_and_mentor_routes_are_flagged_and_admin_only(db, monkeypatch):
    _loaded(db)
    student = make_student(db, "route_student")
    client = make_client(router)
    monkeypatch.setenv("ADMIN_API_KEY", "mentor-key")

    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "false")
    disabled = client.get(f"/api/admin/v2/mentor/cohort/{MODULE_KEY}", headers={"X-Admin-Key": "mentor-key"})
    assert disabled.status_code == 404

    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    assert client.get(f"/api/admin/v2/mentor/cohort/{MODULE_KEY}").status_code == 403
    assert client.get(f"/api/admin/v2/mentor/cohort/{MODULE_KEY}", headers=auth_headers(student)).status_code == 403
    allowed = client.get(f"/api/admin/v2/mentor/cohort/{MODULE_KEY}", headers={"X-Admin-Key": "mentor-key"})
    assert allowed.status_code == 200

    updated = client.put(
        "/api/admin/v2/mentor/cohort-focus",
        headers={"X-Admin-Key": "mentor-key"},
        json={"module_key": MODULE_KEY},
    )
    assert updated.status_code == 200
    focus = db.get(AppSetting, "v2_cohort_focus")
    assert focus.value["module_key"] == MODULE_KEY


def test_no_legacy_progression_interaction(db):
    _loaded(db)
    student = make_student(db, "legacy_guard")
    legacy_before = db.query(TrainingWeek).count()
    report = cohort_progress(db, MODULE_KEY)
    assert report["students"][0]["student_id"] == student.id
    assert db.query(TrainingWeek).count() == legacy_before
    assert db.query(V2ModuleActivity).count() == 0


def test_service_desk_authoritative_breakdown_is_composed(db):
    _loaded(db)
    student = make_student(db, "service_detail")
    scenario = ServiceDeskScenario(stable_key="phase2c", title="IP issue", category="network", difficulty=1, status="active")
    db.add(scenario)
    db.flush()
    version = ServiceDeskScenarioVersion(
        scenario_id=scenario.id, version_number=1, definition_json={},
        definition_hash="a" * 64, validation_status="valid", status="draft",
    )
    db.add(version)
    db.flush()
    attempt = ServiceDeskAttempt(
        student_id=student.id, scenario_version_id=version.id, mode="simulation",
        experience_mode="assessment", status="failed", current_state={},
        current_state_hash="b" * 64, state_version=1, attempt_number=1,
        score=55, passed=False,
    )
    db.add(attempt)
    db.flush()
    db.add(ServiceDeskAttemptGrade(
        attempt_id=attempt.id, scenario_version_id=version.id, rubric_version="process-v1",
        technical_complete=False, critical_failure=False, overall_score=55, passed=False,
        feedback_summary="Verification and documentation need work.",
        details_json={"objective_checks": {"investigation": True, "diagnosis": True, "remediation": True, "verification": False, "documentation": False}, "process_weights": {"investigation": 15, "diagnosis": 25, "remediation": 30, "verification": 20, "documentation": 10}},
    ))
    record_activity(
        db, student_id=student.id, module_key=MODULE_KEY,
        activity_type="service_desk", ref_key="assess.aplus.ipcfg.service_desk",
        status="failed", score=55, passed=False, detail={"attempt_id": attempt.id}, commit=True,
    )

    report = module_report(db, student.id, MODULE_KEY)
    assert report["service_desk"]["score"] == 55
    breakdown = {row["key"]: row for row in report["service_desk"]["breakdown"]}
    assert breakdown["investigation"]["met"] is True
    assert breakdown["verification"]["met"] is False
    assert report["service_desk"]["review_url"].endswith(str(attempt.id))
