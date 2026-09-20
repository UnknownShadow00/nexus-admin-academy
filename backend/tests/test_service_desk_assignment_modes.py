"""Assignment-mode boundaries for retries, debriefs, and ownership."""

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
)
from app.routers import admin_service_desk, service_desk
from conftest import auth_headers, make_client, make_student
from test_service_desk_attempts import close, setup_assignment, start


def _complete_failure(client, student, attempt_id):
    close(client, student, attempt_id)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": f"complete-{attempt_id}"},
    )
    assert response.status_code == 201
    assert response.json()["passed"] is False
    return response.json()


def test_learning_and_simulation_retry_ceilings_are_independent(db):
    student = make_student(db, username="assignment-modes")
    learning = setup_assignment(
        db, student, stable_key="inc2506", process_profile=True,
        mode="learning", maximum_attempts=2,
    )
    simulation = ServiceDeskAssignment(
        student_id=student.id,
        scenario_id=learning.scenario_id,
        mode="simulation",
        assigned_by="admin",
        maximum_attempts=1,
    )
    db.add(simulation)
    db.commit()
    client = make_client(service_desk.router)

    first_learning = start(client, student, learning)
    assert first_learning.status_code == 201
    learning_grade = _complete_failure(client, student, first_learning.json()["id"])
    assert learning_grade["debrief"]["coaching_tier"] == "limited"
    assert learning_grade["debrief"]["result"]["attempts_remaining"] == 1

    first_simulation = start(client, student, simulation)
    assert first_simulation.status_code == 201
    assert first_simulation.json()["attempt_number"] == 2
    simulation_grade = _complete_failure(client, student, first_simulation.json()["id"])
    assert simulation_grade["debrief"]["coaching_tier"] == "full"
    assert simulation_grade["debrief"]["result"]["attempts_remaining"] == 0
    assert start(client, student, simulation).status_code == 403

    second_learning = start(client, student, learning)
    assert second_learning.status_code == 201
    assert second_learning.json()["attempt_number"] == 3


def test_unlimited_assignment_keeps_failed_debrief_limited(db):
    student = make_student(db, username="assignment-unlimited")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", process_profile=True,
        mode="learning", maximum_attempts=None,
    )
    client = make_client(service_desk.router)
    attempt = start(client, student, assignment)
    grade = _complete_failure(client, student, attempt.json()["id"])

    assert grade["debrief"]["coaching_tier"] == "limited"
    assert grade["debrief"]["stronger_path"] == []
    assert grade["debrief"]["result"]["attempts_remaining"] is None
    assert start(client, student, assignment).status_code == 201


def test_practice_experience_uses_simulation_assignment_retry_ceiling(db):
    student = make_student(db, username="assignment-practice")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", process_profile=True,
        mode="simulation", maximum_attempts=2,
    )
    client = make_client(service_desk.router)

    assessment = start(client, student, assignment)
    assert assessment.status_code == 201
    first = db.get(ServiceDeskAttempt, assessment.json()["id"])
    assert first.experience_mode == "assessment"
    first.status = "completed"
    first.passed = True
    first.score = 100
    db.commit()

    listed = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    listed_assignment = next(row for row in listed if row["id"] == assignment.id)
    assert listed_assignment["experience_mode"] == "practice"
    assert listed_assignment["most_recent_attempt"] == {
        "id": first.id,
        "status": "completed",
        "attempt_number": first.attempt_number,
        "experience_mode": "assessment",
    }

    practice = start(client, student, assignment)
    assert practice.status_code == 201
    assert practice.json()["experience_mode"] == "practice"
    grade = _complete_failure(client, student, practice.json()["id"])
    assert grade["debrief"]["result"]["attempts_remaining"] == 0
    assert grade["debrief"]["coaching_tier"] == "full"
    assert start(client, student, assignment).status_code == 403


def test_attempt_ownership_is_enforced_in_every_assignment_mode(db):
    owner = make_student(db, username="mode-owner")
    other = make_student(db, username="mode-other")
    client = make_client(service_desk.router)
    for index, mode in enumerate(("learning", "simulation"), start=1):
        assignment = setup_assignment(
            db, owner, stable_key=f"scenario-mode-{index}", mode=mode,
            maximum_attempts=2,
        )
        assert client.post(
            f"/api/service-desk/assignments/{assignment.id}/attempts",
            headers=auth_headers(other),
        ).status_code == 404


def test_contract_endpoint_exposes_semantic_runtime_version(db):
    response = make_client(service_desk.router).get("/api/service-desk/contract")

    assert response.status_code == 200
    assert response.json() == {
        "contract_version": service_desk.SERVICE_DESK_CONTRACT_VERSION,
    }


def test_mutation_rejects_missing_or_mismatched_service_desk_contract(db):
    student = make_student(db, username="stale-service-desk-client")
    assignment = setup_assignment(db, student, stable_key="contract-guard")
    client = make_client(service_desk.router)
    headers = auth_headers(student)
    headers.pop("X-Nexus-Service-Desk-Contract")

    missing = client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts",
        headers=headers,
    )
    assert missing.status_code == 409
    headers["X-Nexus-Service-Desk-Contract"] = "1.0"
    mismatch = client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts",
        headers=headers,
    )
    assert mismatch.status_code == 409


def test_marked_v2_attempt_and_retry_grant_do_not_change_legacy_budget(db, monkeypatch):
    student = make_student(db, username="mode-context-isolation")
    assignment = setup_assignment(
        db,
        student,
        stable_key="context-isolation",
        mode="learning",
        maximum_attempts=1,
    )
    client = make_client(service_desk.router)
    marked = start(client, student, assignment)
    assert marked.status_code == 201
    attempt = db.get(ServiceDeskAttempt, marked.json()["id"])
    attempt.status = "failed"
    attempt.passed = False
    db.add(ServiceDeskAttemptEvent(
        attempt_id=attempt.id,
        sequence_number=1,
        idempotency_key="test-v2-context",
        event_type="v2.curriculum_launch",
        tool="system",
        payload_json={"module_key": "module.test", "assessment_key": "assessment.test"},
        previous_state_hash=attempt.current_state_hash,
        resulting_state_hash=attempt.current_state_hash,
        success=True,
        trusted=True,
    ))
    db.commit()

    legacy_retry = start(client, student, assignment)
    assert legacy_retry.status_code == 201
    legacy = db.get(ServiceDeskAttempt, legacy_retry.json()["id"])
    legacy.status = "failed"
    legacy.passed = False
    for number in (3, 4):
        extra = ServiceDeskAttempt(
            student_id=student.id,
            scenario_version_id=attempt.scenario_version_id,
            mode="learning",
            experience_mode="guided",
            status="failed",
            current_state={},
            current_state_hash=f"v2-context-{number}".ljust(64, "0"),
            state_version=0,
            attempt_number=number,
            passed=False,
        )
        db.add(extra)
        db.flush()
        db.add(ServiceDeskAttemptEvent(
            attempt_id=extra.id,
            sequence_number=1,
            idempotency_key=f"test-v2-context-{number}",
            event_type="v2.curriculum_launch",
            tool="system",
            payload_json={
                "module_key": "module.test",
                "assessment_key": "assessment.test",
            },
            previous_state_hash=extra.current_state_hash,
            resulting_state_hash=extra.current_state_hash,
            success=True,
            trusted=True,
        ))
    db.commit()
    assert start(client, student, assignment).status_code == 403

    monkeypatch.setenv("ADMIN_API_KEY", "context-retry-key")
    admin = make_client(admin_service_desk.router)
    granted = admin.post(
        f"/api/admin/service-desk/attempts/{attempt.id}/grant-retry",
        headers={"X-Admin-Key": "context-retry-key"},
    )
    assert granted.status_code == 200
    assert granted.json()["attempts_remaining"] == 1
    db.refresh(assignment)
    assert assignment.maximum_attempts == 1
    assert start(client, student, assignment).status_code == 403
