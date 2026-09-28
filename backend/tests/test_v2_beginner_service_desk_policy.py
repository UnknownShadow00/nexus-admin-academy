"""A hidden V2 assignment cannot create work; its trusted attempt can finish."""

import pytest

from conftest import auth_headers, enroll_v2, make_client, make_student
from seed import seed_service_desk_scenarios

from app.models.certification import CertificationModule, ModuleAssessment
from app.models.service_desk import (
    ServiceDeskAssignment, ServiceDeskAttempt, ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.routers.service_desk import router as service_desk_router
from app.routers.v2_curriculum import router as curriculum_router
from app.services.service_desk_realism import fixture_catalog
from app.services.v2_beginner_path import STAGE_KEYS
from app.services.v2_content_loader import load_module
from app.services.v2_progress_service import record_activity
from test_service_desk_attempts import setup_assignment

OLD_MODULE = "module.aplus.core1.ip_configuration"
OLD_ASSESSMENT = "assess.aplus.ipcfg.service_desk"


def _loaded(db):
    seed_service_desk_scenarios(db, ticket_ids=set(fixture_catalog()) | {"INC2403"})
    load_module(db, commit=True)
    return db.query(ServiceDeskScenario).filter_by(stable_key="inc2503").one()


def _old_launch(db, monkeypatch, *, username="sd_beginner_old"):
    scenario = _loaded(db)
    student = make_student(db, username=username)
    enroll_v2(monkeypatch, student)
    client = make_client(curriculum_router, service_desk_router)
    launched = client.post(
        f"/api/v2/curriculum/modules/{OLD_MODULE}/service-desk/{OLD_ASSESSMENT}/launch",
        headers=auth_headers(student),
    )
    assert launched.status_code == 200, launched.text
    assignment = db.query(ServiceDeskAssignment).filter_by(
        student_id=student.id, scenario_id=scenario.id, mode="learning",
    ).one()
    return student, client, assignment


def _start(client, student, assignment, **params):
    return client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts",
        params=params, headers=auth_headers(student),
    )


@pytest.mark.parametrize("completed_history", [False, True])
def test_old_assignment_cannot_create_attempt_after_switch(db, monkeypatch, completed_history):
    student, client, assignment = _old_launch(db, monkeypatch)
    historical_id = None
    if completed_history:
        started = _start(client, student, assignment)
        assert started.status_code == 201
        historical_id = started.json()["id"]
        attempt = db.get(ServiceDeskAttempt, historical_id)
        attempt.status = "completed"
        attempt.passed = True
        db.commit()

    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    headers = auth_headers(student)
    assert client.get("/api/service-desk/assignments", headers=headers).status_code == 200
    assert assignment.id not in {
        row["id"] for row in client.get("/api/service-desk/assignments", headers=headers).json()
    }
    explicit = client.get(
        "/api/service-desk/assignments",
        params={"v2_module_key": OLD_MODULE, "v2_assessment_key": OLD_ASSESSMENT},
        headers=headers,
    )
    assert explicit.status_code == 404
    assert _start(client, student, assignment).status_code == 404
    assert _start(
        client, student, assignment,
        v2_module_key=OLD_MODULE, v2_assessment_key=OLD_ASSESSMENT,
    ).status_code == 404
    assert db.query(ServiceDeskAttempt).filter_by(student_id=student.id).count() == int(completed_history)
    if historical_id:
        assert client.get(f"/api/service-desk/attempts/{historical_id}", headers=headers).status_code == 200
        assert historical_id in {row["id"] for row in client.get("/api/service-desk/attempts", headers=headers).json()}


def test_unmarked_in_progress_attempt_cannot_grandfather_old_assignment(db, monkeypatch):
    student, client, assignment = _old_launch(db, monkeypatch)
    version = db.query(ServiceDeskScenarioVersion).filter_by(
        scenario_id=assignment.scenario_id, status="published",
    ).first()
    db.add(ServiceDeskAttempt(
        student_id=student.id, scenario_version_id=version.id,
        mode=assignment.mode, experience_mode="guided", status="in_progress",
        current_state={}, current_state_hash="0" * 64, state_version=0,
        attempt_number=1,
    ))
    db.commit()
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    assert assignment.id not in {
        item["id"] for item in client.get(
            "/api/service-desk/assignments", headers=auth_headers(student),
        ).json()
    }
    assert _start(client, student, assignment).status_code == 404


def test_trusted_old_attempt_resumes_writes_and_completes_without_new_launch(db, monkeypatch):
    student, client, assignment = _old_launch(db, monkeypatch)
    other = make_student(db, username="sd_beginner_other")
    enroll_v2(monkeypatch, student, other)
    started = _start(client, student, assignment)
    assert started.status_code == 201
    attempt_id = started.json()["id"]
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    headers = auth_headers(student)
    listed = client.get("/api/service-desk/assignments", headers=headers)
    row = next(item for item in listed.json() if item["id"] == assignment.id)
    assert row["resumable_only"] is True
    assert row["most_recent_attempt"]["id"] == attempt_id
    assert row["most_recent_attempt"]["status"] == "in_progress"
    explicit = client.get(
        "/api/service-desk/assignments",
        params={"v2_module_key": OLD_MODULE, "v2_assessment_key": OLD_ASSESSMENT},
        headers=headers,
    )
    assert explicit.status_code == 200
    assert next(item for item in explicit.json() if item["id"] == assignment.id)["resumable_only"] is True
    resumed = _start(client, student, assignment)
    assert resumed.status_code == 200 and resumed.json()["id"] == attempt_id
    assert db.query(ServiceDeskAttempt).filter_by(student_id=student.id).count() == 1
    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=headers).status_code == 200

    # Ownership and the V2 pilot allowlist still protect the grandfathered ID.
    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(other)).status_code in {403, 404}
    assert _start(client, other, assignment).status_code == 404
    assert _start(
        client, student, assignment,
        v2_module_key=STAGE_KEYS[0], v2_assessment_key=OLD_ASSESSMENT,
    ).status_code == 404
    assert client.post(
        f"/api/service-desk/attempts/{attempt_id}/hints", headers=auth_headers(other),
        json={"idempotency_key": "other-hint", "tool": "ticket", "payload": {}},
    ).status_code in {403, 404}
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "")
    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=headers).status_code == 404
    assert _start(client, student, assignment).status_code == 404
    assert assignment.id not in {
        item["id"] for item in client.get("/api/service-desk/assignments", headers=headers).json()
    }
    enroll_v2(monkeypatch, student, other)

    # A stale/corrupt assignment label cannot borrow the attempt marker.
    original_source = assignment.assigned_by
    assignment.assigned_by = f"v2_curriculum:{STAGE_KEYS[0]}:forged-assessment"
    db.commit()
    assert assignment.id not in {item["id"] for item in client.get("/api/service-desk/assignments", headers=headers).json()}
    assert _start(client, student, assignment).status_code == 404
    assignment.assigned_by = "manual"
    db.commit()
    assert _start(
        client, student, assignment,
        v2_module_key=OLD_MODULE, v2_assessment_key=OLD_ASSESSMENT,
    ).status_code == 404
    explicit = client.get(
        "/api/service-desk/assignments",
        params={"v2_module_key": OLD_MODULE, "v2_assessment_key": OLD_ASSESSMENT},
        headers=headers,
    )
    assert explicit.status_code == 404
    assignment.assigned_by = original_source
    db.commit()

    event = client.post(
        f"/api/service-desk/attempts/{attempt_id}/events", headers=headers,
        json={
            "idempotency_key": "old-run-note", "event_type": "ticket.add_note", "tool": "ticket",
            "payload": {"body": "I checked the original evidence before continuing."},
            "resulting_state": {}, "success": True,
        },
    )
    assert event.status_code == 201, event.text
    action = client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions", headers=headers,
        json={
            "idempotency_key": "old-run-action", "event_type": "ticket.add_note",
            "tool": "ticket", "payload": {"ticketId": "INC2503", "body": "I checked the current device and kept the evidence."},
        },
    )
    assert action.status_code in {200, 201}, action.text
    snapshot = client.post(
        f"/api/service-desk/attempts/{attempt_id}/snapshot", headers=headers,
        json={"idempotency_key": "old-run-snapshot", "snapshot": {"schema_version": 1, "nexus_service_desk_attempt": {}}},
    )
    assert snapshot.status_code == 201, snapshot.text
    hint = client.post(
        f"/api/service-desk/attempts/{attempt_id}/hints", headers=headers,
        json={"idempotency_key": "old-run-hint", "tool": "ticket", "payload": {"ticketId": "INC2503"}},
    )
    assert hint.status_code == 201, hint.text
    closed = client.post(
        f"/api/service-desk/attempts/{attempt_id}/events", headers=headers,
        json={
            "idempotency_key": "old-run-close", "event_type": "ticket.close", "tool": "ticket",
            "payload": {"verifiedResolved": True, "resolutionNote": "Checked with the user"},
            "resulting_state": {}, "success": True,
        },
    )
    assert closed.status_code == 201, closed.text
    completed = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete", headers=headers,
        json={"idempotency_key": "old-run-complete"},
    )
    assert completed.status_code == 201, completed.text
    assert db.get(ServiceDeskAttempt, attempt_id).status in {"completed", "failed"}
    assert _start(client, student, assignment).status_code == 404
    assert assignment.id not in {item["id"] for item in client.get("/api/service-desk/assignments", headers=headers).json()}
    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=headers).status_code == 200


def test_current_beginner_context_and_legacy_service_desk_keep_their_routes(db, monkeypatch):
    scenario = _loaded(db)
    student = make_student(db, username="sd_current_beginner")
    enroll_v2(monkeypatch, student)
    module = db.query(CertificationModule).filter_by(module_key=STAGE_KEYS[0]).one()
    assessment = ModuleAssessment(
        assessment_key="test.beginner.stage1.service_desk",
        certification_module_id=module.id, assessment_role="service_desk",
        service_desk_scenario_id=scenario.id, active=True,
    )
    db.add(assessment)
    db.flush()
    record_activity(
        db, student_id=student.id, module_key=module.module_key,
        activity_type="service_desk", ref_key=assessment.assessment_key,
        status="in_progress", detail={"scenario_id": scenario.id}, commit=True,
    )
    assignment = ServiceDeskAssignment(
        student_id=student.id, scenario_id=scenario.id, mode="learning",
        assigned_by=f"v2_curriculum:{module.module_key}:{assessment.assessment_key}",
    )
    db.add(assignment)
    db.commit()
    client = make_client(service_desk_router)
    headers = auth_headers(student)
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    listed = client.get("/api/service-desk/assignments", headers=headers)
    assert listed.status_code == 200
    assert next(item for item in listed.json() if item["id"] == assignment.id)["resumable_only"] is False
    current = _start(client, student, assignment)
    assert current.status_code == 201, current.text
    assert client.get(f"/api/service-desk/attempts/{current.json()['id']}", headers=headers).status_code == 200

    locked_student = make_student(db, username="sd_locked_beginner_stage")
    enroll_v2(monkeypatch, student, locked_student)
    locked_module = db.query(CertificationModule).filter_by(module_key=STAGE_KEYS[1]).one()
    locked_assessment = ModuleAssessment(
        assessment_key="test.beginner.stage2.service_desk",
        certification_module_id=locked_module.id, assessment_role="service_desk",
        service_desk_scenario_id=scenario.id, active=True,
    )
    db.add(locked_assessment)
    db.flush()
    record_activity(
        db, student_id=locked_student.id, module_key=locked_module.module_key,
        activity_type="service_desk", ref_key=locked_assessment.assessment_key,
        status="in_progress", detail={"scenario_id": scenario.id}, commit=True,
    )
    locked_assignment = ServiceDeskAssignment(
        student_id=locked_student.id, scenario_id=scenario.id, mode="learning",
        assigned_by=f"v2_curriculum:{locked_module.module_key}:{locked_assessment.assessment_key}",
    )
    db.add(locked_assignment)
    db.commit()
    locked = _start(client, locked_student, locked_assignment)
    assert locked.status_code == 403
    assert "Finish Stage 1" in locked.json()["detail"]

    legacy_student = make_student(db, username="sd_legacy_beginner_flag")
    legacy_assignment = setup_assignment(db, legacy_student, stable_key="legacy-path-switch", mode="learning")
    legacy_headers = auth_headers(legacy_student)
    legacy = _start(client, legacy_student, legacy_assignment)
    assert legacy.status_code == 201, legacy.text
    assert client.get(f"/api/service-desk/attempts/{legacy.json()['id']}", headers=legacy_headers).status_code == 200
    legacy_rows = client.get("/api/service-desk/assignments", headers=legacy_headers).json()
    assert next(item for item in legacy_rows if item["id"] == legacy_assignment.id)["resumable_only"] is False


def test_old_v2_launch_remains_available_when_beginner_flag_off(db, monkeypatch):
    student, client, assignment = _old_launch(db, monkeypatch)
    first = _start(client, student, assignment)
    assert first.status_code == 201, first.text
    first_attempt = db.get(ServiceDeskAttempt, first.json()["id"])
    first_attempt.status = "failed"
    db.commit()
    second = _start(client, student, assignment)
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first.json()["id"]
    assert assignment.id in {row["id"] for row in client.get("/api/service-desk/assignments", headers=auth_headers(student)).json()}
