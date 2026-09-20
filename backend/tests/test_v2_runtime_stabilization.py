"""Regression contracts for the Nexus V2 runtime stabilization sprint."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.certification import (
    CertificationModule,
    InterviewPrompt,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
)
from app.models.grading import GRADE_JOB_PROCESSING, PendingGrade
from app.models.lab import LabRun, LabTemplate
from app.models.quiz import Question, Quiz
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.v2_progress import (
    V2AssessmentAttempt,
    V2AssessmentAttemptQuestion,
    V2ModuleActivity,
    V2ExplainSubmission,
)
from app.models.vm_assignment import VmAssignment
from app.routers.v2_curriculum import router as curriculum_router
from app.routers.v2_progress import router as progress_router
from app.routers.labs import router as labs_router
from app.routers.service_desk import router as service_desk_router
from app.routers.grading import router as grading_router
from app.routers.admin_grading import router as admin_grading_router
from app.routers.admin_v2_mentor import router as admin_v2_router
from app.routers.admin_curriculum import router as admin_curriculum_router
from app.services.grading_provider import OUTCOME_OK, ProviderResult
from app.services.grading_queue import apply_mentor_override, claim_due_jobs, process_pending_grade
from app.services.grading_schema import AIGradeResponse, GRADING_SCHEMA_VERSION
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import (
    explain_view,
    module_view,
    resource_activity,
    submit_assessment,
    submit_explain,
)
from app.services.v2_progress_service import reconcile_v2_service_desk_attempt, record_activity
from app.services.service_desk_progression import build_service_desk_progression
from conftest import auth_headers, enroll_v2, make_client, make_student


MODULE = "module.aplus.core1.network_services_troubleshooting"


def _ready(db, monkeypatch):
    # Seed the INC25xx / INC2403 realism scenarios before load_module, exactly
    # like seed_v2_foundation.run, so the Wave 3 service_desk_ref bindings
    # (inc2504/2505/2506/2508) resolve and reconcile back to active and the
    # grading-profile gate sees real definitions.
    from app.services.service_desk_realism import fixture_catalog
    from seed import seed_service_desk_scenarios

    seed_service_desk_scenarios(db, ticket_ids=set(fixture_catalog()) | {"INC2403"})
    load_module(db, commit=True)
    student = make_student(db, username="runtime_student")
    enroll_v2(monkeypatch, student)
    return student, make_client(curriculum_router, progress_router)


def _seeded_inc2503(db):
    """The real seeded inc2503 scenario + its published version.

    Post-P0 the grading-profile gate rejects a hand-rolled stub with an empty
    ``definition_json``; these tests exercise assignment/reconciliation flows,
    not scenario authoring, so they reuse the seeded realism scenario.
    """
    scenario = (
        db.query(ServiceDeskScenario).filter_by(stable_key="inc2503").one()
    )
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id, status="published")
        .order_by(ServiceDeskScenarioVersion.version_number.desc())
        .first()
    )
    return scenario, version


def _quiz_key(db):
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    return db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="module_quiz"
    ).one().assessment_key


def _correct_answers(db, questions):
    answers = {}
    for public in questions:
        question = db.get(Question, public["id"])
        if public["type"] == "short_answer":
            answers[str(question.id)] = db.query(QuestionV2Meta).filter_by(
                question_id=question.id
            ).one().acceptable_answers[0]
        else:
            answers[str(question.id)] = ",".join(question.all_correct_answers)
    return answers


def _complete_module_except_first_explain(db, student):
    view = module_view(db, student.id, MODULE)
    for lesson in view["lessons"]:
        for resource in lesson["resources"]:
            if resource["required"]:
                resource_activity(db, student.id, MODULE, resource["key"], completed=True)
        record_activity(
            db, student_id=student.id, module_key=MODULE, activity_type="lesson",
            ref_key=lesson["key"], status="completed",
        )
        if lesson["quick_check"]:
            record_activity(
                db, student_id=student.id, module_key=MODULE, activity_type="quick_check",
                ref_key=lesson["quick_check"]["key"], status="passed", passed=True,
            )
    for assessment in view["assessments"]:
        if assessment["role"] in {"module_quiz", "practical", "service_desk"}:
            record_activity(
                db, student_id=student.id, module_key=MODULE,
                activity_type=assessment["role"], ref_key=assessment["key"],
                status="passed", score=100, passed=True,
            )
    for prompt in view["explain_prompts"][1:]:
        record_activity(
            db, student_id=student.id, module_key=MODULE, activity_type="explain",
            ref_key=prompt["key"], status="passed", score=100, passed=True,
        )
    db.commit()
    return view["explain_prompts"][0]["key"]


def test_constrained_quiz_start_submit_fidelity_repeated_twenty_times(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    key = _quiz_key(db)
    seen_attempt_ids = set()
    for _ in range(20):
        payload = client.get(
            f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}",
            headers=auth_headers(student),
        ).json()["data"]
        attempt_id = payload["attempt"]["id"]
        seen_attempt_ids.add(attempt_id)
        response = client.post(
            f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}/submit",
            json={"attempt_id": attempt_id, "answers": _correct_answers(db, payload["questions"])},
            headers=auth_headers(student),
        )
        assert response.status_code == 200
        assert response.json()["data"]["score"] == 100
    assert len(seen_attempt_ids) == 20
    assert db.query(V2AssessmentAttempt).filter_by(student_id=student.id).count() == 20


def test_refresh_reuses_selection_and_retry_creates_new_attempt(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    key = _quiz_key(db)
    url = f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}"
    first = client.get(url, headers=auth_headers(student)).json()["data"]
    refreshed = client.get(url, headers=auth_headers(student)).json()["data"]
    assert refreshed["attempt"] == first["attempt"]
    assert [q["id"] for q in refreshed["questions"]] == [q["id"] for q in first["questions"]]
    client.post(
        f"{url}/submit",
        json={"attempt_id": first["attempt"]["id"], "answers": _correct_answers(db, first["questions"])},
        headers=auth_headers(student),
    )
    retry = client.post(f"{url}/attempts", headers=auth_headers(student)).json()["data"]
    assert retry["attempt"]["id"] != first["attempt"]["id"]
    assert retry["attempt"]["attempt_number"] == 2


def test_started_attempt_submits_stored_snapshot_after_bank_is_unpublished(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    key = _quiz_key(db)
    url = f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}"
    started = client.get(url, headers=auth_headers(student)).json()["data"]
    assessment = db.query(ModuleAssessment).filter_by(assessment_key=key).one()
    db.get(Quiz, assessment.quiz_id).status = "draft"
    db.commit()

    submitted = client.post(
        f"{url}/submit",
        json={
            "attempt_id": started["attempt"]["id"],
            "answers": _correct_answers(db, started["questions"]),
        },
        headers=auth_headers(student),
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["score"] == 100
    assert client.get(url, headers=auth_headers(student)).status_code == 404


def test_double_submit_is_idempotent_and_does_not_lose_history(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    key = _quiz_key(db)
    url = f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}"
    started = client.get(url, headers=auth_headers(student)).json()["data"]
    body = {"attempt_id": started["attempt"]["id"], "answers": _correct_answers(db, started["questions"])}
    first = client.post(f"{url}/submit", json=body, headers=auth_headers(student))
    second = client.post(f"{url}/submit", json=body, headers=auth_headers(student))
    assert first.json()["data"] == second.json()["data"]
    assert db.query(V2AssessmentAttempt).filter_by(student_id=student.id).count() == 1


def test_persisted_question_selection_is_immutable(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    key = _quiz_key(db)
    started = client.get(
        f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}",
        headers=auth_headers(student),
    ).json()["data"]
    selected = db.query(V2AssessmentAttemptQuestion).filter_by(
        attempt_id=started["attempt"]["id"], position=0,
    ).one()
    selected.position = 99
    with pytest.raises(ValueError, match="selection is immutable"):
        db.flush()
    db.rollback()


def test_ambiguous_short_answer_becomes_pending_not_zero(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    module_key = "module.aplus.core1.hardware_support"
    assessment_key = "assess.aplus.hardware.qc.platform"
    url = f"/api/v2/curriculum/modules/{module_key}/assessments/{assessment_key}"
    started = client.get(url, headers=auth_headers(student)).json()["data"]
    short = next(q for q in started["questions"] if q["type"] == "short_answer")
    response = client.post(
        f"{url}/submit",
        json={"attempt_id": started["attempt"]["id"], "answers": {str(short["id"]): "This is a plausible response written in different words that is much longer than a normal short answer."}},
        headers=auth_headers(student),
    )
    assert response.json()["data"]["grading_state"] == "pending"
    attempt = db.get(V2AssessmentAttempt, started["attempt"]["id"])
    assert attempt.status == "needs_review"
    assert attempt.score is None
    job = next(
        db.get(PendingGrade, row.pending_grade_id)
        for row in attempt.questions if row.pending_grade_id
    )
    apply_mentor_override(
        db, job, reason="Alternate wording is acceptable", override_score=1.0,
        override_passed=True,
    )
    db.refresh(attempt)
    assert attempt.grading_state == "graded"
    assert attempt.score is not None


def test_assessment_submission_and_pending_job_roll_back_together(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    module_key = "module.aplus.core1.hardware_support"
    assessment_key = "assess.aplus.hardware.qc.platform"
    url = f"/api/v2/curriculum/modules/{module_key}/assessments/{assessment_key}"
    started = client.get(url, headers=auth_headers(student)).json()["data"]
    short = next(q for q in started["questions"] if q["type"] == "short_answer")

    def interrupted(*_args, **_kwargs):
        raise RuntimeError("injected interruption before atomic commit")

    monkeypatch.setattr("app.services.v2_curriculum_service.record_activity", interrupted)
    with pytest.raises(RuntimeError, match="injected interruption"):
        submit_assessment(
            db, student.id, module_key, assessment_key,
            started["attempt"]["id"],
            {str(short["id"]): "A plausible but ambiguous alternate explanation."},
        )
    db.rollback()

    attempt = db.get(V2AssessmentAttempt, started["attempt"]["id"])
    assert attempt.status == "in_progress"
    assert attempt.submitted_at is None
    assert db.query(PendingGrade).count() == 0
    assert all(row.submitted_answer is None for row in attempt.questions)


def test_explain_submission_and_pending_job_roll_back_together(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    prompt_key = module_view(db, student.id, MODULE)["explain_prompts"][0]["key"]

    def interrupted(*_args, **_kwargs):
        raise RuntimeError("injected interruption before atomic commit")

    monkeypatch.setattr("app.services.v2_curriculum_service.record_activity", interrupted)
    with pytest.raises(RuntimeError, match="injected interruption"):
        submit_explain(
            db, student.id, MODULE, prompt_key,
            "A plausible response that intentionally requires mentor judgment.",
        )
    db.rollback()

    assert db.query(V2ExplainSubmission).filter_by(student_id=student.id).count() == 0
    assert db.query(PendingGrade).filter_by(student_id=student.id).count() == 0


def test_explain_history_preserves_each_deterministic_result(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    prompt_key = module_view(db, student.id, MODULE)["explain_prompts"][0]["key"]
    prompt = db.query(InterviewPrompt).filter_by(prompt_key=prompt_key).one()
    concepts = [
        item if isinstance(item, str) else item.get("concept", "")
        for item in (prompt.expected_concepts or [])
    ]
    first = submit_explain(db, student.id, MODULE, prompt_key, ". ".join(concepts))
    assert first["state"] == "graded"
    assert first["passed"] is True

    prompt.expected_concepts = ["concept that is absent", "another absent concept"]
    db.commit()
    second = submit_explain(
        db, student.id, MODULE, prompt_key,
        "A later ambiguous retry requiring mentor review.",
    )
    assert second["state"] == "pending"

    history = explain_view(db, student.id, MODULE, prompt_key)["submissions"]
    assert history[0]["id"] == first["submission_id"]
    assert history[0]["state"] == "graded"
    assert history[0]["score"] == 100
    assert history[0]["passed"] is True
    assert history[1]["id"] == second["submission_id"]
    assert history[1]["state"] == "pending"


def test_mentor_override_cannot_resolve_without_score_and_pass_result(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    prompt_key = module_view(db, student.id, MODULE)["explain_prompts"][0]["key"]
    submitted = submit_explain(
        db, student.id, MODULE, prompt_key,
        "A plausible response that intentionally requires mentor judgment.",
    )
    job = db.query(PendingGrade).filter_by(
        submission_ref=f"v2-explain:{submitted['submission_id']}"
    ).one()
    monkeypatch.setenv("ADMIN_API_KEY", "complete-override-key")
    admin = make_client(admin_grading_router)

    response = admin.post(
        f"/api/admin/grading/{job.id}/override",
        headers={"X-Admin-Key": "complete-override-key"},
        json={"reason": "Incomplete mentor decision"},
    )

    assert response.status_code == 422
    db.refresh(job)
    assert job.status != "graded"
    assert job.resolved_passed is None
    assert job.overrides == []


def test_explain_mentor_resolution_reconciles_progress(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    prompt_key = _complete_module_except_first_explain(db, student)
    submitted = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt_key}/submit",
        json={"answer": "This answer is deliberately ambiguous and needs a human decision."},
        headers=auth_headers(student),
    ).json()["data"]
    job = db.query(PendingGrade).filter_by(submission_ref=f"v2-explain:{submitted['submission_id']}").one()
    apply_mentor_override(db, job, reason="Meets the rubric", override_score=1.0, override_passed=True)
    activity = db.query(V2ModuleActivity).filter_by(
        student_id=student.id, activity_type="explain", ref_key=prompt_key
    ).one()
    assert activity.status == "passed"
    assert activity.passed is True
    completed = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student),
    ).json()["data"]
    assert completed["progress"]["module_complete"] is True
    assert completed["continue"]["kind"] == "complete"


def test_explain_ai_resolution_reconciles_progress(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    prompt_key = _complete_module_except_first_explain(db, student)
    submitted = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt_key}/submit",
        json={"answer": "This alternate wording deliberately requires the automated review path to decide."},
        headers=auth_headers(student),
    ).json()["data"]
    job = db.query(PendingGrade).filter_by(submission_ref=f"v2-explain:{submitted['submission_id']}").one()

    class PassingProvider:
        def grade(self, _request):
            parsed = AIGradeResponse(
                schema_version=GRADING_SCHEMA_VERSION, score=1.0, passed=True,
                confidence=0.99, matched_concepts=["supported"], missing_concepts=[],
                feedback="Meets the rubric.", review_recommended=False,
            )
            return ProviderResult(outcome=OUTCOME_OK, provider="test", parsed=parsed)

    process_pending_grade(db, job, provider=PassingProvider())
    activity = db.query(V2ModuleActivity).filter_by(
        student_id=student.id, activity_type="explain", ref_key=prompt_key
    ).one()
    assert (activity.status, activity.score, activity.passed) == ("passed", 100, True)
    completed = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student),
    ).json()["data"]
    assert completed["progress"]["module_complete"] is True
    assert completed["continue"]["kind"] == "complete"


def test_failed_explain_resolution_updates_progress_without_completing(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    prompt_key = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student)
    ).json()["data"]["explain_prompts"][0]["key"]
    submitted = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt_key}/submit",
        json={"answer": "This alternate wording deliberately requires a mentor to decide the final result."},
        headers=auth_headers(student),
    ).json()["data"]
    job = db.query(PendingGrade).filter_by(submission_ref=f"v2-explain:{submitted['submission_id']}").one()
    apply_mentor_override(db, job, reason="Does not meet the rubric", override_score=0.0, override_passed=False)
    activity = db.query(V2ModuleActivity).filter_by(
        student_id=student.id, activity_type="explain", ref_key=prompt_key
    ).one()
    assert (activity.status, activity.passed) == ("failed", False)


def test_generic_student_progress_mutation_endpoint_is_removed(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    response = client.post(
        "/api/v2/progress/activity",
        json={"module_key": MODULE, "activity_type": "module_quiz", "ref_key": "forged", "status": "passed", "passed": True},
        headers=auth_headers(student),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("activity_type", ["module_quiz", "practical", "service_desk"])
def test_passed_rollup_is_monotonic_after_failed_retry(db, monkeypatch, activity_type):
    student, _ = _ready(db, monkeypatch)
    key = _quiz_key(db)
    ref_key = f"{key}:{activity_type}"
    record_activity(db, student_id=student.id, module_key=MODULE, activity_type=activity_type, ref_key=ref_key, status="passed", score=100, passed=True, commit=True)
    record_activity(db, student_id=student.id, module_key=MODULE, activity_type=activity_type, ref_key=ref_key, status="failed", score=0, passed=False, commit=True)
    row = db.query(V2ModuleActivity).filter_by(student_id=student.id, ref_key=ref_key).one()
    assert (row.status, row.score, row.passed) == ("passed", 100, True)
    assert row.detail["latest_result"] == {"status": "failed", "score": 0, "passed": False}


def test_stale_processing_grade_is_reclaimed(db):
    student = make_student(db, username="lease_student")
    stale = PendingGrade(
        student_id=student.id, source_type="free_response", submission_ref="lease:1",
        submitted_answer="answer", status=GRADE_JOB_PROCESSING,
        claimed_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        claim_token="abandoned", retry_count=0, max_retries=3,
    )
    db.add(stale)
    db.commit()
    claimed = claim_due_jobs(db, now=datetime.now(timezone.utc), lease_seconds=300)
    assert [job.id for job in claimed] == [stale.id]
    assert claimed[0].claim_token != "abandoned"


def test_superseded_grading_worker_cannot_append_duplicate_ai_grade(db):
    student = make_student(db, username="lease_race_student")
    job = PendingGrade(
        student_id=student.id, source_type="free_response", submission_ref="lease:race",
        submitted_answer="answer", question_text="question", status=GRADE_JOB_PROCESSING,
        claimed_at=datetime.now(timezone.utc), claim_token="first-worker",
        retry_count=0, max_retries=3,
    )
    db.add(job)
    db.commit()

    class PassingProvider:
        def grade(self, _request):
            parsed = AIGradeResponse(
                schema_version=GRADING_SCHEMA_VERSION, score=1.0, passed=True,
                confidence=0.99, matched_concepts=["supported"], missing_concepts=[],
                feedback="Meets the rubric.", review_recommended=False,
            )
            return ProviderResult(outcome=OUTCOME_OK, provider="test", parsed=parsed)

    job.claim_token = "replacement-worker"
    db.commit()
    stale_result = process_pending_grade(
        db, job, provider=PassingProvider(), expected_claim_token="first-worker",
    )
    assert stale_result is None
    assert len(job.ai_grades) == 0

    accepted = process_pending_grade(
        db, job, provider=PassingProvider(), expected_claim_token="replacement-worker",
    )
    assert accepted is not None
    assert len(job.ai_grades) == 1


def test_draft_lessons_and_unapproved_banks_are_not_student_visible(db, monkeypatch):
    student, client = _ready(db, monkeypatch)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    lesson = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).first()
    lesson.status = "draft"
    quiz_assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="module_quiz"
    ).one()
    quiz = db.get(Quiz, quiz_assessment.quiz_id)
    quiz.answer_keys_validated = False
    db.commit()
    module_data = client.get(f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student)).json()["data"]
    assert lesson.lesson_key not in {row["key"] for row in module_data["lessons"]}
    blocked = client.get(
        f"/api/v2/curriculum/modules/{MODULE}/assessments/{quiz_assessment.assessment_key}",
        headers=auth_headers(student),
    )
    assert blocked.status_code == 404


def test_v2_practical_bypasses_week_gate_only_with_valid_relationship(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="practical"
    ).one()
    lab = db.get(LabTemplate, assessment.lab_template_id)
    lab.week_number = 24
    db.commit()
    def blocked_legacy_gate(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="legacy week gate")

    monkeypatch.setattr("app.routers.labs.require_week_reached", blocked_legacy_gate)
    client = make_client(labs_router)
    legacy = client.post(f"/api/labs/{assessment.lab_template_id}/start", headers=auth_headers(student))
    assert legacy.status_code == 404
    valid = client.post(
        f"/api/labs/{assessment.lab_template_id}/start",
        params={"v2_module_key": MODULE, "v2_assessment_key": assessment.assessment_key},
        headers=auth_headers(student),
    )
    assert valid.status_code in {200, 202}
    params = {"v2_module_key": MODULE, "v2_assessment_key": assessment.assessment_key}
    blank = client.post(
        f"/api/labs/{assessment.lab_template_id}/submit", params=params,
        headers=auth_headers(student), json={"notes": "", "answers": {}},
    )
    assert blank.status_code == 400
    submitted = client.post(
        f"/api/labs/{assessment.lab_template_id}/submit", params=params,
        headers=auth_headers(student),
        json={"notes": "Collected command output and documented verification.", "answers": {}},
    )
    assert submitted.status_code == 200
    activity = db.query(V2ModuleActivity).filter_by(
        student_id=student.id, activity_type="practical",
        ref_key=assessment.assessment_key,
    ).one()
    assert activity.status == "needs_review"
    assert activity.passed is None
    assert activity.detail["evidence_review_required"] is True
    invalid = client.post(
        f"/api/labs/{assessment.lab_template_id}/start",
        params={"v2_module_key": MODULE, "v2_assessment_key": "not-related"},
        headers=auth_headers(student),
    )
    assert invalid.status_code == 404


def test_v2_practical_is_absent_from_legacy_list_and_revocation_is_immediate(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="practical"
    ).one()
    client = make_client(labs_router)
    headers = auth_headers(student)

    listed = client.get("/api/labs", headers=headers)
    assert assessment.lab_template_id not in {row["id"] for row in listed.json()["data"]}
    params = {"v2_module_key": MODULE, "v2_assessment_key": assessment.assessment_key}
    assert client.get(
        f"/api/labs/{assessment.lab_template_id}", params=params, headers=headers
    ).status_code == 200

    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "")
    assert client.post(
        f"/api/labs/{assessment.lab_template_id}/start", params=params, headers=headers
    ).status_code == 404


def test_revoked_v2_practical_run_cannot_use_vm_or_upload_evidence(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="practical"
    ).one()
    client = make_client(labs_router)
    headers = auth_headers(student)
    params = {"v2_module_key": MODULE, "v2_assessment_key": assessment.assessment_key}
    started = client.post(
        f"/api/labs/{assessment.lab_template_id}/start", params=params, headers=headers
    )
    assert started.status_code in {200, 202}
    run = db.get(LabRun, started.json()["data"]["run_id"])
    db.add(VmAssignment(
        student_id=student.id, lab_run_id=run.id, vmid=99991,
        status="running", guac_conn_id="revoked-v2",
    ))
    db.commit()

    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "")
    assert client.get(
        f"/api/labs/{assessment.lab_template_id}/vm-status", headers=headers
    ).status_code == 404
    assert client.post(
        f"/api/labs/{assessment.lab_template_id}/vm-access", headers=headers
    ).status_code == 404
    assert client.post(
        f"/api/labs/{run.id}/evidence",
        files={"file": ("proof.png", b"image", "image/png")},
        headers=headers,
    ).status_code == 404


def test_inactive_module_cannot_be_forged_as_v2_practical_context(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="practical"
    ).one()
    module.active = False
    db.commit()
    response = make_client(labs_router).post(
        f"/api/labs/{assessment.lab_template_id}/start",
        params={"v2_module_key": MODULE, "v2_assessment_key": assessment.assessment_key},
        headers=auth_headers(student),
    )
    assert response.status_code == 404


def test_service_desk_reconciliation_uses_exact_v2_activity_with_both_modes(db, monkeypatch):
    student, curriculum_client = _ready(db, monkeypatch)
    module_key = "module.aplus.core1.ip_configuration"
    assessment_key = "assess.aplus.ipcfg.service_desk"
    scenario, version = _seeded_inc2503(db)
    learning_assignment = ServiceDeskAssignment(
        student_id=student.id, scenario_id=scenario.id, mode="learning",
        is_required=False, maximum_attempts=1, assigned_by="admin",
    )
    simulation_assignment = ServiceDeskAssignment(
        student_id=student.id, scenario_id=scenario.id, mode="simulation",
        is_required=False, maximum_attempts=3, assigned_by="seed",
    )
    db.add_all([learning_assignment, simulation_assignment])
    db.flush()
    db.add(ServiceDeskAttempt(
        student_id=student.id,
        scenario_version_id=version.id,
        mode="learning",
        experience_mode="guided",
        status="completed",
        current_state={},
        current_state_hash="legacy-guided".ljust(64, "0"),
        state_version=1,
        attempt_number=1,
        score=100,
        passed=True,
    ))
    db.commit()
    launched = curriculum_client.post(
        f"/api/v2/curriculum/modules/{module_key}/service-desk/{assessment_key}/launch",
        headers=auth_headers(student),
    )
    assert launched.status_code == 200
    service_client = make_client(service_desk_router)
    listed = service_client.get(
        "/api/service-desk/assignments",
        params={"v2_module_key": module_key, "v2_assessment_key": assessment_key},
        headers=auth_headers(student),
    )
    target_rows = [row for row in listed.json() if row["scenario_id"] == scenario.id]
    assert {row["mode"] for row in target_rows} == {"learning", "simulation"}
    assert all(row["guided_completed"] is False for row in target_rows)
    optional_started = service_client.post(
        f"/api/service-desk/assignments/{simulation_assignment.id}/attempts",
        params={
            "v2_module_key": module_key,
            "v2_assessment_key": assessment_key,
        },
        headers=auth_headers(student),
    )
    assert optional_started.status_code == 201
    assert reconcile_v2_service_desk_attempt(
        db, student_id=student.id, scenario_id=scenario.id,
        attempt_id=optional_started.json()["id"], score=100, passed=True,
    ) is None
    optional_attempt = db.get(ServiceDeskAttempt, optional_started.json()["id"])
    optional_attempt.status = "failed"
    optional_attempt.passed = False
    db.commit()
    legacy_progress = build_service_desk_progression(db, student)
    assert scenario.stable_key not in legacy_progress["passed_keys"]
    assert scenario.stable_key not in legacy_progress["failed_history_keys"]
    optional_attempt.status = "completed"
    optional_attempt.passed = True
    db.commit()
    started = service_client.post(
        f"/api/service-desk/assignments/{learning_assignment.id}/attempts",
        params={
            "v2_module_key": module_key,
            "v2_assessment_key": assessment_key,
        },
        headers=auth_headers(student),
    )
    assert started.status_code == 201
    attempt_id = started.json()["id"]
    reconciled = reconcile_v2_service_desk_attempt(
        db, student_id=student.id, scenario_id=scenario.id,
        attempt_id=attempt_id, score=82, passed=True,
    )
    db.commit()
    assert reconciled is not None
    assert reconciled.ref_key == assessment_key
    assert reconciled.status == "passed"

    # Re-entering for the assessment/practice assignment is optional after
    # the required guided case passes and cannot revoke module credit.
    relaunched = curriculum_client.post(
        f"/api/v2/curriculum/modules/{module_key}/service-desk/{assessment_key}/launch",
        headers=auth_headers(student),
    )
    assert relaunched.status_code == 200
    assert relaunched.json()["data"]["experience_mode"] == "assessment"
    db.refresh(reconciled)
    assert reconciled.status == "passed"
    still_passed = reconcile_v2_service_desk_attempt(
        db, student_id=student.id, scenario_id=scenario.id,
        attempt_id=attempt_id, score=20, passed=False,
    )
    assert still_passed is not None
    assert still_passed.status == "passed"


def test_v2_service_desk_assignment_bypasses_legacy_ladder_only_for_exact_case(db, monkeypatch):
    student, curriculum_client = _ready(db, monkeypatch)
    module_key = "module.aplus.core1.ip_configuration"
    assessment_key = "assess.aplus.ipcfg.service_desk"
    scenario, _ = _seeded_inc2503(db)
    launched = curriculum_client.post(
        f"/api/v2/curriculum/modules/{module_key}/service-desk/{assessment_key}/launch",
        headers=auth_headers(student),
    )
    assert launched.status_code == 200
    assignment = db.query(ServiceDeskAssignment).filter_by(student_id=student.id).one()
    service_client = make_client(service_desk_router)
    started = service_client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts",
        headers=auth_headers(student),
    )
    assert started.status_code == 201
    marked_attempt = db.get(ServiceDeskAttempt, started.json()["id"])
    marked_attempt.status = "completed"
    marked_attempt.passed = True
    db.commit()
    assert scenario.stable_key not in build_service_desk_progression(
        db, student
    )["guided_completed_keys"]

    other = make_student(db, username="legacy_only_student")
    assert service_client.get(
        f"/api/service-desk/attempts/{started.json()['id']}",
        headers=auth_headers(other),
    ).status_code in {403, 404}

    legacy_assignment = ServiceDeskAssignment(
        student_id=other.id, scenario_id=assignment.scenario_id, mode=assignment.mode,
        is_required=True, maximum_attempts=3, assigned_by="seed",
    )
    db.add(legacy_assignment)
    db.commit()
    blocked = service_client.post(
        f"/api/service-desk/assignments/{legacy_assignment.id}/attempts",
        headers=auth_headers(other),
    )
    assert blocked.status_code == 403


def test_revoked_student_cannot_continue_v2_service_desk_attempt(db, monkeypatch):
    student, curriculum_client = _ready(db, monkeypatch)
    module_key = "module.aplus.core1.ip_configuration"
    assessment_key = "assess.aplus.ipcfg.service_desk"
    scenario, _ = _seeded_inc2503(db)
    legacy_assignment = ServiceDeskAssignment(
        student_id=student.id, scenario_id=scenario.id, mode="learning",
        is_required=False, maximum_attempts=None, assigned_by="admin",
    )
    db.add(legacy_assignment)
    db.commit()
    service_client = make_client(service_desk_router)
    legacy_attempt = service_client.post(
        f"/api/service-desk/assignments/{legacy_assignment.id}/attempts",
        headers=auth_headers(student),
    )
    assert legacy_attempt.status_code == 201
    assert curriculum_client.post(
        f"/api/v2/curriculum/modules/{module_key}/service-desk/{assessment_key}/launch",
        headers=auth_headers(student),
    ).status_code == 200
    assignment = db.query(ServiceDeskAssignment).filter_by(
        student_id=student.id, scenario_id=scenario.id, mode="learning"
    ).one()
    listed_for_v2 = service_client.get(
        "/api/service-desk/assignments",
        params={
            "v2_module_key": module_key,
            "v2_assessment_key": assessment_key,
        },
        headers=auth_headers(student),
    )
    assert listed_for_v2.status_code == 200
    v2_row = next(row for row in listed_for_v2.json() if row["id"] == assignment.id)
    assert v2_row["most_recent_attempt"] is None
    started = service_client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts",
        params={
            "v2_module_key": module_key,
            "v2_assessment_key": assessment_key,
        },
        headers=auth_headers(student),
    )
    assert started.status_code == 201

    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "")
    listed = service_client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    )
    assert listed.status_code == 200
    assert {row["id"] for row in listed.json()} == {legacy_assignment.id}
    assert service_client.get(
        f"/api/service-desk/attempts/{legacy_attempt.json()['id']}",
        headers=auth_headers(student),
    ).status_code == 200
    assert service_client.get(
        f"/api/service-desk/attempts/{started.json()['id']}",
        headers=auth_headers(student),
    ).status_code == 404
    attempt_rows = service_client.get(
        "/api/service-desk/attempts", headers=auth_headers(student)
    ).json()
    assert {row["id"] for row in attempt_rows} == {legacy_attempt.json()["id"]}
    assert service_client.post(
        f"/api/service-desk/attempts/{started.json()['id']}/hints",
        headers=auth_headers(student),
        json={"idempotency_key": "revoked", "tool": "ticket", "payload": {}},
    ).status_code == 404

    activity = db.query(V2ModuleActivity).filter_by(
        student_id=student.id,
        module_key=module_key,
        activity_type="service_desk",
        ref_key=assessment_key,
    ).one()
    before = (activity.status, activity.score, activity.passed)
    assert reconcile_v2_service_desk_attempt(
        db,
        student_id=student.id,
        scenario_id=scenario.id,
        attempt_id=legacy_attempt.json()["id"],
        score=100,
        passed=True,
    ) is None
    db.refresh(activity)
    assert (activity.status, activity.score, activity.passed) == before


def test_student_ownership_and_privileged_endpoint_matrix(db, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "runtime-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "runtime-admin-password")
    monkeypatch.setenv("ADMIN_API_KEY", "runtime-admin-api-key")
    student_a, _ = _ready(db, monkeypatch)
    student_b = make_student(db, username="runtime_student_b")
    # Both are enrolled: this proves per-student ownership inside the pilot,
    # not that a non-enrolled student is turned away (covered separately).
    enroll_v2(monkeypatch, student_a, student_b)
    client = make_client(
        curriculum_router, progress_router, grading_router,
        admin_grading_router, admin_v2_router, admin_curriculum_router,
    )
    key = _quiz_key(db)
    url = f"/api/v2/curriculum/modules/{MODULE}/assessments/{key}"
    attempt = client.get(url, headers=auth_headers(student_a)).json()["data"]
    cross_submit = client.post(
        f"{url}/submit",
        json={"attempt_id": attempt["attempt"]["id"], "answers": {}},
        headers=auth_headers(student_b),
    )
    assert cross_submit.status_code == 404

    prompt_key = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student_a)
    ).json()["data"]["explain_prompts"][0]["key"]
    submission = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt_key}/submit",
        json={"answer": "A detailed alternate explanation that needs review before it can be accepted."},
        headers=auth_headers(student_a),
    ).json()["data"]
    ref = f"v2-explain:{submission['submission_id']}"
    assert client.get(
        f"/api/grading/status?source_type=interview_explain&submission_ref={ref}",
        headers=auth_headers(student_b),
    ).status_code == 404
    assert client.get(
        f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt_key}",
        headers=auth_headers(student_b),
    ).json()["data"]["submissions"] == []

    for method, path in (
        ("get", "/api/admin/grading/queue"),
        ("get", f"/api/admin/v2/mentor/cohort/{MODULE}"),
        ("get", "/api/admin/curriculum/videos"),
    ):
        assert getattr(client, method)(path, headers=auth_headers(student_a)).status_code in {401, 403}
