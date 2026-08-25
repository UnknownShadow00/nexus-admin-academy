"""Phase 4C.3 — Final Support Shift: migration, grading, and router tests."""

import os
import subprocess
import sys
from pathlib import Path

from conftest import auth_headers, make_client, make_student
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.lab import LabRun, LabTemplate
from app.models.progression import PromotionGate, Role, StudentRole
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.routers.final_shift import router
from app.routers.labs import router as labs_router
from app.services.final_shift_grading import compute_final_shift_grade
from app.services.integrated_support_final_shift import WEEK_24_CASE
from app.services.progression_service import check_promotion_eligibility

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION_0060 = "0060_network_linux_cloud_practical_upgrade"
REVISION_0061 = "0061_integrated_support_prove"

client = make_client(router)
labs_client = make_client(labs_router)


def _run(command: list[str], database_url: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "JWT_SECRET_KEY": "phase4c3-migration-test-secret-at-least-32-bytes",
            "COOKIE_SECURE": "false",
        }
    )
    subprocess.run(command, cwd=BACKEND_ROOT, env=environment, capture_output=True, check=True, text=True)


def _seed(database_url: str) -> None:
    _run([sys.executable, "seed.py"], database_url)
    _run([sys.executable, "seed_curriculum.py"], database_url)


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def test_migration_upgrade_converts_week_23_24_and_adds_gate(tmp_path):
    database_path = tmp_path / "fresh.db"
    database_url = f"sqlite:///{database_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], database_url)
    _seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as db:
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == REVISION_0061
        lab21 = db.get(LabTemplate, 21)
        lab22 = db.get(LabTemplate, 22)
        assert lab21.lab_type == lab22.lab_type == "structured_final_shift"
        assert len(lab21.success_criteria["final_shift"]["incidents"]) == 3
        assert len(lab22.success_criteria["final_shift"]["incidents"]) == 3

        week23 = db.query(TrainingWeek).filter_by(week_number=23).one()
        week24 = db.query(TrainingWeek).filter_by(week_number=24).one()
        activity23 = db.query(TrainingWeekActivity).filter_by(
            training_week_id=week23.id, activity_type="guided_lab", content_ref="21"
        ).one()
        activity24 = db.query(TrainingWeekActivity).filter_by(
            training_week_id=week24.id, activity_type="guided_lab", content_ref="22"
        ).one()
        assert activity23.metadata_json.get("learning_role") == "troubleshoot"
        assert activity24.metadata_json.get("learning_role") == "prove"
        assert activity23.is_required is True
        assert activity24.is_required is True

        final_role = db.query(Role).filter_by(name="Junior Infrastructure Administrator").one()
        gate = db.query(PromotionGate).filter_by(role_id=final_role.id, requirement_type="required_lab_pass").one()
        assert gate.requirement_config == {"lab_id": 22, "min_score_pct": 80}

    assert _active_totals(database_path) == (35, 320, 141, 179)
    assert _role_counts(database_path) == {
        "learn": 216,
        "check": 38,
        "practice": 21,
        "troubleshoot": 37,
        "prove": 8,
    }


def _role_counts(database_path):
    from app.services.curriculum_structure import learning_role_for

    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        counts = {"learn": 0, "check": 0, "practice": 0, "troubleshoot": 0, "prove": 0}
        for activity_type, metadata_json in db.execute(
            text("SELECT activity_type, metadata_json FROM training_week_activities")
        ):
            import json as _json

            metadata = _json.loads(metadata_json) if metadata_json else None
            counts[learning_role_for(activity_type, metadata)] += 1
        return counts


def _active_totals(database_path):
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        activities = (
            db.query(TrainingWeekActivity)
            .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
            .filter(TrainingWeek.is_active.is_(True))
            .all()
        )
        required = sum(activity.is_required for activity in activities)
        return (
            db.query(TrainingWeek).filter_by(is_active=True).count(),
            len(activities),
            required,
            len(activities) - required,
        )


def test_migration_downgrade_restores_prior_content_and_removes_gate(tmp_path):
    database_path = tmp_path / "cycle.db"
    database_url = f"sqlite:///{database_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], database_url)
    _seed(database_url)

    _run([sys.executable, "-m", "alembic", "downgrade", REVISION_0060], database_url)
    engine = create_engine(database_url)
    with Session(engine) as db:
        assert db.get(LabTemplate, 21).lab_type == "structured_operations"
        assert db.get(LabTemplate, 22).lab_type == "structured_capstone"
        final_role = db.query(Role).filter_by(name="Junior Infrastructure Administrator").one()
        assert (
            db.query(PromotionGate).filter_by(role_id=final_role.id, requirement_type="required_lab_pass").first()
            is None
        )

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0061], database_url)
    with Session(engine) as db:
        assert db.get(LabTemplate, 21).lab_type == "structured_final_shift"
    assert _active_totals(database_path) == (35, 320, 141, 179)


def test_historical_week_24_completion_preserved_but_does_not_satisfy_new_gate(tmp_path):
    """A student who passed the OLD, weaker Week 24 lab before this migration
    keeps that history, but it must not silently count toward the new,
    stronger graduation requirement (spec: historical completion policy)."""
    database_path = tmp_path / "historical.db"
    database_url = f"sqlite:///{database_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], database_url)
    _seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as db:
        from app.models.student import Student

        student = Student(
            name="Old Completion Student",
            email="old-completion@example.test",
            username="old-completion",
            password_hash="not-a-real-hash",
        )
        db.add(student)
        db.flush()
        old_run = LabRun(
            lab_template_id=22,
            student_id=student.id,
            status="submitted",
            final_score=100,
            structured_feedback={"score_pct": 100, "questions": []},
        )
        db.add(old_run)
        db.commit()
        student_id, old_run_id = student.id, old_run.id

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0061], database_url)
    with Session(engine) as db:
        preserved = db.get(LabRun, old_run_id)
        assert preserved is not None
        assert preserved.status == "submitted" and preserved.final_score == 100

        final_role = db.query(Role).filter_by(name="Junior Infrastructure Administrator").one()
        eligibility = check_promotion_eligibility(student_id, final_role.id, db)
        gate_result = next(
            r for r in eligibility["requirements_met"] + eligibility["requirements_missing"]
            if r["type"] == "required_lab_pass"
        )
        assert gate_result["met"] is False


def test_already_awarded_role_is_never_revoked_by_gate_evaluation(tmp_path):
    database_path = tmp_path / "graduated.db"
    database_url = f"sqlite:///{database_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], database_url)
    _seed(database_url)

    engine = create_engine(database_url)
    with Session(engine) as db:
        from app.models.student import Student

        final_role = db.query(Role).filter_by(name="Junior Infrastructure Administrator").one()
        student = Student(
            name="Already Graduated",
            email="already-graduated@example.test",
            username="already-graduated",
            password_hash="not-a-real-hash",
            current_role_id=final_role.id,
        )
        db.add(student)
        db.flush()
        award = StudentRole(student_id=student.id, role_id=final_role.id, promotion_notes="Graduated pre-4C.3")
        db.add(award)
        db.commit()
        student_id, award_id, role_id = student.id, award.id, final_role.id

    # Re-running eligibility (which now returns not-met for this student,
    # since they have no passing 4C.3-rubric LabRun) must never touch the
    # already-persisted award or the student's current role.
    with Session(engine) as db:
        eligibility = check_promotion_eligibility(student_id, role_id, db)
        assert eligibility["eligible"] is False
        from app.models.student import Student

        student = db.get(Student, student_id)
        assert student.current_role_id == role_id
        assert db.get(StudentRole, award_id).role_id == role_id


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def _passing_feedback():
    incidents = {}
    for incident in WEEK_24_CASE["final_shift"]["incidents"]:
        doc = {"issue": "x", "evidence": "x", "action": "x", "verification": "x"}
        if incident["requires_user_update"]:
            doc["user_update"] = "Told the user"
        if incident["requires_escalation"]:
            doc["escalation"] = "Filed escalation"
        incidents[incident["key"]] = {
            "inspected_panel_ids": incident["required_inspections"],
            "diagnosis_answer": incident["diagnosis"]["correct"],
            "action_choice": incident["correct_action_id"],
            "unsafe_action_attempted": False,
            "documentation": doc,
            "status": "escalated" if incident["requires_escalation"] else "resolved",
        }
    return {
        "queue_order": ["incident_c", "incident_a", "incident_b"],
        "incidents": incidents,
        "handoff": {"resolved": "a, b", "escalated": "c", "watch_items": "none"},
    }


def test_grading_full_correct_run_passes_at_100():
    grade = compute_final_shift_grade(WEEK_24_CASE, _passing_feedback())
    assert grade["passed"] is True
    assert grade["overall_score"] == 100
    assert grade["safety_gate_ok"] is True
    assert grade["all_resolved_or_escalated"] is True


def test_grading_unsafe_final_action_fails_regardless_of_score():
    feedback = _passing_feedback()
    unsafe_action = next(a["id"] for a in WEEK_24_CASE["final_shift"]["incidents"][0]["actions"] if not a["safe"])
    feedback["incidents"]["incident_a"]["action_choice"] = unsafe_action
    feedback["incidents"]["incident_a"]["status"] = "investigating"
    grade = compute_final_shift_grade(WEEK_24_CASE, feedback)
    assert grade["safety_gate_ok"] is False
    assert grade["passed"] is False


def test_grading_unresolved_incident_fails_even_with_high_score_elsewhere():
    feedback = _passing_feedback()
    feedback["incidents"]["incident_b"] = {
        "inspected_panel_ids": [],
        "diagnosis_answer": None,
        "action_choice": None,
        "unsafe_action_attempted": False,
        "documentation": {},
        "status": "investigating",
    }
    grade = compute_final_shift_grade(WEEK_24_CASE, feedback)
    assert grade["all_resolved_or_escalated"] is False
    assert grade["passed"] is False


def test_grading_prioritization_scores_partial_credit_for_wrong_order():
    feedback = _passing_feedback()
    feedback["queue_order"] = ["incident_b", "incident_a", "incident_c"]  # fully reversed vs expected
    grade = compute_final_shift_grade(WEEK_24_CASE, feedback)
    assert grade["dimension_scores"]["prioritization"] == 0.0
    assert grade["overall_score"] < 100


def test_grading_one_incident_verification_never_satisfies_another():
    feedback = _passing_feedback()
    # incident_c's evidence answers copied onto incident_a's diagnosis field
    feedback["incidents"]["incident_a"]["diagnosis_answer"] = WEEK_24_CASE["final_shift"]["incidents"][2]["diagnosis"]["correct"]
    grade = compute_final_shift_grade(WEEK_24_CASE, feedback)
    assert grade["per_incident"]["incident_a"]["diagnosis"] == 0.0


# ---------------------------------------------------------------------------
# Router: happy path, safety, isolation
# ---------------------------------------------------------------------------


def _seed_final_shift_lab(db, lab_id=22, week_number=24):
    lab = LabTemplate(
        id=lab_id,
        title="Final Support Shift",
        lab_type="structured_final_shift",
        difficulty=3,
        week_number=week_number,
        estimated_minutes=45,
        environment_requirements={},
        setup_instructions="Work the queue.",
        success_criteria={"final_shift": WEEK_24_CASE["final_shift"]},
        required_evidence={},
        hints={},
        is_published=True,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


def _mentor_student(db, username):
    student = make_student(db, username=username)
    student.is_mentor = True
    db.commit()
    db.refresh(student)
    return student


def test_generic_lab_endpoint_never_leaks_final_shift_answer_key(db):
    """LabPage.jsx calls GET /api/labs/{id} before it knows the lab_type, so
    the generic labs router must never forward success_criteria.final_shift
    (which carries diagnosis.correct, actions[].safe, and verification) —
    only /api/final-shift/{id} may serve the redacted case content."""
    student = _mentor_student(db, "fs-leak-check")
    lab = _seed_final_shift_lab(db)

    res = labs_client.get(f"/api/labs/{lab.id}", headers=auth_headers(student))
    assert res.status_code == 200
    assert "final_shift" not in res.json()["data"]["success_criteria"]


def test_get_before_start_shows_not_started_and_hides_answers(db):
    student = _mentor_student(db, "fs-view")
    lab = _seed_final_shift_lab(db)

    res = client.get(f"/api/final-shift/{lab.id}", headers=auth_headers(student))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "not_started"
    incident = data["incidents"][0]
    assert "correct" not in incident["diagnosis_options"][0]
    assert all("safe" not in action for action in incident["actions"])
    assert incident["state"]["verification"] is None


def test_full_happy_path_start_open_attempt_handoff(db):
    student = _mentor_student(db, "fs-happy")
    lab = _seed_final_shift_lab(db)

    start = client.post(f"/api/final-shift/{lab.id}/start", headers=auth_headers(student))
    assert start.status_code == 200

    incidents_in_priority_order = sorted(
        WEEK_24_CASE["final_shift"]["incidents"], key=lambda incident: incident["expected_priority_rank"]
    )
    for incident in incidents_in_priority_order:
        open_res = client.post(
            f"/api/final-shift/{lab.id}/incidents/{incident['key']}/open", headers=auth_headers(student)
        )
        assert open_res.status_code == 200
        doc = {"issue": "x", "evidence": "x", "action": "x", "verification": "x"}
        if incident["requires_user_update"]:
            doc["user_update"] = "told them"
        if incident["requires_escalation"]:
            doc["escalation"] = "escalated"
        attempt = client.post(
            f"/api/final-shift/{lab.id}/incidents/{incident['key']}/attempt",
            headers=auth_headers(student),
            json={
                "inspected_panel_ids": incident["required_inspections"],
                "diagnosis_answer": incident["diagnosis"]["correct"],
                "action_choice": incident["correct_action_id"],
                "documentation": doc,
            },
        )
        assert attempt.status_code == 200
        body = attempt.json()["data"]
        assert body["ready"] is True
        assert body["verification"] is not None

    handoff = client.post(
        f"/api/final-shift/{lab.id}/handoff",
        headers=auth_headers(student),
        json={"resolved": "a, b", "escalated": "c", "watch_items": "none"},
    )
    assert handoff.status_code == 200
    grading = handoff.json()["data"]["grading"]
    assert grading["passed"] is True
    assert grading["overall_score"] == 100


def test_unsafe_action_is_rejected_and_never_reveals_verification(db):
    student = _mentor_student(db, "fs-unsafe")
    lab = _seed_final_shift_lab(db)
    incident = WEEK_24_CASE["final_shift"]["incidents"][0]
    unsafe_action = next(a["id"] for a in incident["actions"] if not a["safe"])

    client.post(f"/api/final-shift/{lab.id}/start", headers=auth_headers(student))
    client.post(f"/api/final-shift/{lab.id}/incidents/{incident['key']}/open", headers=auth_headers(student))
    res = client.post(
        f"/api/final-shift/{lab.id}/incidents/{incident['key']}/attempt",
        headers=auth_headers(student),
        json={
            "inspected_panel_ids": incident["required_inspections"],
            "diagnosis_answer": incident["diagnosis"]["correct"],
            "action_choice": unsafe_action,
            "documentation": {},
        },
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["ready"] is False
    assert body["verification"] is None


def test_handoff_blocked_until_all_incidents_resolved(db):
    student = _mentor_student(db, "fs-incomplete")
    lab = _seed_final_shift_lab(db)
    client.post(f"/api/final-shift/{lab.id}/start", headers=auth_headers(student))

    res = client.post(
        f"/api/final-shift/{lab.id}/handoff",
        headers=auth_headers(student),
        json={"resolved": "a", "escalated": "", "watch_items": ""},
    )
    assert res.status_code == 409


def test_student_cannot_act_on_another_students_run(db):
    student_a = _mentor_student(db, "fs-a")
    student_b = _mentor_student(db, "fs-b")
    lab = _seed_final_shift_lab(db)

    client.post(f"/api/final-shift/{lab.id}/start", headers=auth_headers(student_a))
    incident_key = WEEK_24_CASE["final_shift"]["incidents"][0]["key"]
    client.post(f"/api/final-shift/{lab.id}/incidents/{incident_key}/open", headers=auth_headers(student_a))

    # Student B has no active run yet; acting on the same lab/incident must
    # 400 (must start their own run) rather than touching A's progress.
    res = client.post(
        f"/api/final-shift/{lab.id}/incidents/{incident_key}/attempt",
        headers=auth_headers(student_b),
        json={"inspected_panel_ids": [], "diagnosis_answer": None, "action_choice": None, "documentation": {}},
    )
    assert res.status_code == 400

    a_state = client.get(f"/api/final-shift/{lab.id}", headers=auth_headers(student_a)).json()["data"]
    assert incident_key in a_state["queue_order"]
    b_state = client.get(f"/api/final-shift/{lab.id}", headers=auth_headers(student_b)).json()["data"]
    assert b_state["queue_order"] == []


def test_retry_after_submission_starts_a_fresh_run_and_preserves_history(db):
    student = _mentor_student(db, "fs-retry")
    lab = _seed_final_shift_lab(db)
    client.post(f"/api/final-shift/{lab.id}/start", headers=auth_headers(student))

    # Directly mark the run as submitted (short-circuit a full failing pass)
    # to test the retry path in isolation. `db` shares the same StaticPool
    # engine as the TestClient's overridden session, so this is visible to it.
    run = db.query(LabRun).filter_by(lab_template_id=lab.id, student_id=student.id).one()
    run.status = "submitted"
    run.final_score = 10
    first_run_id = run.id
    db.commit()

    restart = client.post(f"/api/final-shift/{lab.id}/start", headers=auth_headers(student))
    assert restart.status_code == 200
    new_run_id = restart.json()["data"]["run_id"]
    assert new_run_id != first_run_id

    old_run = db.get(LabRun, first_run_id)
    assert old_run is not None and old_run.status == "submitted"
