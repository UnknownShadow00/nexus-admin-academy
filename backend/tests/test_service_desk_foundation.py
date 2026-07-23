import copy

import pytest
from sqlalchemy import update

from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskAuditLog,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
    ServiceDeskBetaEnrollment,
)
from app.routers import admin_service_desk, service_desk
from app.services.admin_auth import verify_admin
from app.services.service_desk_definitions import (
    ScenarioDefinitionError,
    canonical_definition,
    load_definition_file,
    publish_definition,
    seed_service_desk_scenarios,
)
from app.services.service_desk_engine import replay_attempt
from app.services.service_desk_health import run_published_scenario_health

from conftest import auth_headers, make_client, make_student


def student_client():
    return make_client(service_desk.router)


def admin_client():
    client = make_client(admin_service_desk.router)
    client.app.dependency_overrides[verify_admin] = lambda: True
    return client


def seed_scenario(db):
    result = seed_service_desk_scenarios(db)
    db.commit()
    return result


def test_scenario_canonicalization_sorts_unordered_supported_modes():
    definition = load_definition_file("locked_user_account")

    canonical = canonical_definition(definition)

    assert canonical["supported_modes"] == ["learning", "simulation"]


def test_seed_accepts_legacy_order_dependent_hash_for_identical_definition(db):
    seeded = seed_scenario(db)
    db.execute(
        update(ServiceDeskScenarioVersion)
        .where(ServiceDeskScenarioVersion.id == seeded["version_id"])
        .values(definition_hash="legacy-order-dependent-hash")
    )
    db.commit()

    repeated = seed_service_desk_scenarios(db)

    assert repeated["version_id"] == seeded["version_id"]


def enroll_beta(db, student):
    db.add(ServiceDeskBetaEnrollment(student_id=student.id, enabled=True, enrolled_by="test"))
    db.commit()


def start_learning(client, student, scenario_id):
    response = client.post(
        f"/api/service-desk/scenarios/{scenario_id}/attempts",
        json={"mode": "learning"},
        headers=auth_headers(student),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def action(client, student, attempt, name, payload=None, key=None):
    response = client.post(
        f"/api/service-desk/attempts/{attempt['id']}/actions",
        json={
            "action": name,
            "payload": payload or {},
            "idempotency_key": key or f"{name}-{attempt['state_version']}-key",
            "expected_state_version": attempt["state_version"],
        },
        headers=auth_headers(student),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_student_feature_is_disabled_by_default(db, monkeypatch):
    seeded = seed_scenario(db)
    student = make_student(db, "service-disabled")
    monkeypatch.delenv("SERVICE_DESK_LAB_ENABLED", raising=False)
    monkeypatch.delenv("SERVICE_DESK_LAB_ADMIN_ENABLED", raising=False)

    response = student_client().get("/api/service-desk/scenarios", headers=auth_headers(student))

    assert seeded["published"] == 5
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERVICE_DESK_UNAVAILABLE"
    assert response.json()["detail"]["message"] == "Service Desk Lab is unavailable."


def test_admin_feature_is_disabled_by_default(db, monkeypatch):
    seed_scenario(db)
    monkeypatch.delenv("SERVICE_DESK_LAB_ADMIN_ENABLED", raising=False)

    response = admin_client().get("/api/admin/service-desk/scenarios")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SERVICE_DESK_ADMIN_UNAVAILABLE"


def test_enabled_feature_still_requires_explicit_beta_enrollment(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-non-beta")

    denied = student_client().get("/api/service-desk/scenarios", headers=auth_headers(student))
    assert denied.status_code == 404
    enroll_beta(db, student)
    allowed = student_client().get("/api/service-desk/scenarios", headers=auth_headers(student))
    assert allowed.status_code == 200
    assert len(allowed.json()["data"]) == seeded["published"]


def test_locked_user_account_health_path_persists_ordered_events_and_safe_projection(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-health")
    enroll_beta(db, student)
    client = student_client()
    attempt = start_learning(client, student, seeded["scenario_id"])

    assert "root_cause" not in str(attempt)
    assert "hidden_facts" not in str(attempt)
    assert "critical_failure" not in str(attempt["visible_state"])

    for index, step in enumerate(load_definition_file("locked_user_account").health_path, start=1):
        result = action(
            client,
            student,
            attempt,
            step.action.value,
            step.payload,
            key=f"valid-health-{index}",
        )
        attempt = result["attempt"]
        assert result["action_success"] is True

    assert attempt["status"] == "completed"
    assert attempt["result"] == {
        "technical_complete": True,
        "overall_score": 100,
        "passed": True,
        "feedback_summary": "You verified the requester, restored the correct account safely, documented the work, and resolved the ticket.",
    }
    assert "root_cause" not in str(attempt)
    assert "correct_account_id" not in str(attempt)
    assert "instructor_notes" not in str(attempt)

    stored = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.id == attempt["id"]).one()
    events = (
        db.query(ServiceDeskAttemptEvent)
        .filter(ServiceDeskAttemptEvent.attempt_id == stored.id)
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )
    assert [event.sequence_number for event in events] == list(range(1, 10))
    assert events[-1].payload_json["action"] == "resolve_ticket"
    assert "note" not in events[-2].payload_json
    assert events[-2].payload_json["note_recorded"] is True
    assert replay_attempt(db, stored)["state_hash"] == stored.current_state_hash


def test_recoverable_wrong_search_can_be_corrected(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-recoverable")
    enroll_beta(db, student)
    client = student_client()
    attempt = start_learning(client, student, seeded["scenario_id"])
    for name, payload in [
        ("open_ticket", {}),
        ("inspect_requester", {}),
        ("verify_identity", {"verification_method": "employee_id_last4"}),
    ]:
        attempt = action(client, student, attempt, name, payload)["attempt"]

    wrong = action(client, student, attempt, "search_account", {"query": "wrong.user"})
    attempt = wrong["attempt"]
    assert wrong["action_success"] is True
    assert attempt["visible_state"]["account_found"] is False
    assert attempt["status"] == "in_progress"

    corrected = action(client, student, attempt, "search_account", {"query": "tnguyen"})
    assert corrected["attempt"]["visible_state"]["account_found"] is True


def test_critical_unlock_before_identity_fails_and_cannot_pass(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-critical")
    enroll_beta(db, student)
    client = student_client()
    attempt = start_learning(client, student, seeded["scenario_id"])

    result = action(client, student, attempt, "unlock_account", {"account_id": "tnguyen"}, key="critical-unlock-001")
    failed = result["attempt"]

    assert result["action_success"] is False
    assert failed["status"] == "failed"
    assert failed["result"]["technical_complete"] is False
    assert failed["result"]["overall_score"] == 0
    assert failed["result"]["passed"] is False
    assert "critical_failure" not in str(failed["visible_state"])


@pytest.mark.parametrize(("definition_key", "critical_action", "wrong_payload"), [
    ("locked_user_account", "unlock_account", {"account_id": "wrong-account"}),
    ("password_reset", "reset_password", {"account_id": "wrong-account"}),
    ("mfa_reset", "reset_mfa", {"account_id": "wrong-account"}),
    ("bitlocker_recovery", "lookup_recovery_key", {"device_id": "WRONG-DEVICE"}),
    ("new_employee_onboarding", "create_account", {"account_id": "wrong-account"}),
])
def test_wrong_account_or_device_is_critical_for_every_scenario(
    db, monkeypatch, definition_key, critical_action, wrong_payload
):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seed_scenario(db)
    definition = load_definition_file(definition_key)
    scenario = db.query(ServiceDeskScenario).filter_by(stable_key=definition.stable_key).one()
    student = make_student(db, f"critical-{definition_key}")
    enroll_beta(db, student)
    attempt = start_learning(student_client(), student, scenario.id)

    for index, step in enumerate(definition.health_path, start=1):
        if step.action.value == critical_action:
            rejected = action(
                student_client(), student, attempt, critical_action, wrong_payload,
                key=f"wrong-target-{definition_key}",
            )
            assert rejected["action_success"] is False
            attempt = rejected["attempt"]
            break
        attempt = action(
            student_client(), student, attempt, step.action.value, step.payload,
            key=f"correct-{definition_key}-{index}",
        )["attempt"]

    assert attempt["status"] == "failed"
    assert attempt["result"]["passed"] is False
    assert "critical_failure" not in str(attempt["visible_state"])

    retry = start_learning(student_client(), student, scenario.id)
    for index, step in enumerate(definition.health_path, start=1):
        retry = action(
            student_client(), student, retry, step.action.value, step.payload,
            key=f"retry-{definition_key}-{index}",
        )["attempt"]
    assert retry["status"] == "completed"
    assert retry["result"]["passed"] is True


def test_attempt_isolated_and_client_cannot_inject_state_score_or_unknown_action(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student_a = make_student(db, "service-owner")
    enroll_beta(db, student_a)
    student_b = make_student(db, "service-other")
    client = student_client()
    attempt = start_learning(client, student_a, seeded["scenario_id"])

    foreign = client.get(f"/api/service-desk/attempts/{attempt['id']}", headers=auth_headers(student_b))
    injected_score = client.post(
        f"/api/service-desk/attempts/{attempt['id']}/actions",
        json={"action": "open_ticket", "idempotency_key": "inject-score-001", "expected_state_version": 0, "score": 100},
        headers=auth_headers(student_a),
    )
    injected_state = client.post(
        f"/api/service-desk/attempts/{attempt['id']}/actions",
        json={"action": "open_ticket", "idempotency_key": "inject-state-001", "expected_state_version": 0, "current_state": {"ticket_resolved": True}},
        headers=auth_headers(student_a),
    )
    unknown = client.post(
        f"/api/service-desk/attempts/{attempt['id']}/actions",
        json={"action": "delete_account", "idempotency_key": "unknown-action-1", "expected_state_version": 0},
        headers=auth_headers(student_a),
    )

    assert foreign.status_code == 404
    assert injected_score.status_code == 422
    assert injected_state.status_code == 422
    assert unknown.status_code == 422


def test_idempotency_and_stale_actions_preserve_event_order(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-idempotent")
    enroll_beta(db, student)
    client = student_client()
    attempt = start_learning(client, student, seeded["scenario_id"])
    payload = {"action": "open_ticket", "idempotency_key": "open-ticket-once", "expected_state_version": 0, "payload": {}}

    first = client.post(f"/api/service-desk/attempts/{attempt['id']}/actions", json=payload, headers=auth_headers(student))
    repeated = client.post(f"/api/service-desk/attempts/{attempt['id']}/actions", json=payload, headers=auth_headers(student))
    stale = client.post(
        f"/api/service-desk/attempts/{attempt['id']}/actions",
        json={"action": "inspect_requester", "idempotency_key": "stale-request-001", "expected_state_version": 0, "payload": {}},
        headers=auth_headers(student),
    )

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json()["data"]["idempotent"] is True
    assert stale.status_code == 409
    events = db.query(ServiceDeskAttemptEvent).filter(ServiceDeskAttemptEvent.attempt_id == attempt["id"]).order_by(ServiceDeskAttemptEvent.sequence_number).all()
    assert [event.sequence_number for event in events] == [1, 2]
    events[-1].success = False
    with pytest.raises(ValueError, match="append-only"):
        db.commit()
    db.rollback()


def test_simulation_is_limited_to_three_scored_attempts(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-simulation-limit")
    enroll_beta(db, student)
    client = student_client()
    for index in range(3):
        started = client.post(
            f"/api/service-desk/scenarios/{seeded['scenario_id']}/attempts",
            json={"mode": "simulation"}, headers=auth_headers(student),
        )
        assert started.status_code == 201
        attempt = started.json()["data"]
        failed = action(client, student, attempt, "unlock_account", {"account_id": "tnguyen"}, key=f"critical-sim-{index}")
        assert failed["attempt"]["status"] == "failed"

    fourth = client.post(
        f"/api/service-desk/scenarios/{seeded['scenario_id']}/attempts",
        json={"mode": "simulation"}, headers=auth_headers(student),
    )
    assert fourth.status_code == 403
    assert fourth.json()["detail"]["code"] == "SIMULATION_ATTEMPT_LIMIT"

    # A protected administrator policy override releases one historical scored
    # attempt without deleting its evidence, then permits one more attempt.
    monkeypatch.setenv("SERVICE_DESK_LAB_ADMIN_ENABLED", "true")
    reset = admin_client().post(f"/api/admin/service-desk/attempts/{attempt['id']}/reset")
    assert reset.status_code == 200, reset.text
    assert reset.json()["data"]["attempt"]["admin_reset_at"] is not None
    assert reset.json()["data"]["events"][-1]["event_type"] == "admin_reset"
    assert db.query(ServiceDeskAuditLog).filter(
        ServiceDeskAuditLog.action == "attempt_reset",
        ServiceDeskAuditLog.target_id == str(attempt["id"]),
    ).count() == 1
    released = client.post(
        f"/api/service-desk/scenarios/{seeded['scenario_id']}/attempts",
        json={"mode": "simulation"}, headers=auth_headers(student),
    )
    assert released.status_code == 201


def test_learning_attempts_remain_unlimited(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-learning-unlimited")
    enroll_beta(db, student)
    client = student_client()
    for index in range(4):
        started = client.post(
            f"/api/service-desk/scenarios/{seeded['scenario_id']}/attempts",
            json={"mode": "learning"}, headers=auth_headers(student),
        )
        assert started.status_code == 201
        attempt = started.json()["data"]
        failed = action(client, student, attempt, "unlock_account", {"account_id": "tnguyen"}, key=f"critical-learn-{index}")
        assert failed["attempt"]["status"] == "failed"


def test_admin_validation_inspection_and_immutable_publication_are_protected(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ADMIN_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-admin-inspection")
    forbidden = student_client().get("/api/service-desk/scenarios", headers=auth_headers(student))
    monkeypatch.setenv("ADMIN_API_KEY", "service-desk-admin-test-key")
    direct_admin = make_client(admin_service_desk.router).get(
        "/api/admin/service-desk/scenarios", headers=auth_headers(student)
    )
    client = admin_client()
    listed = client.get("/api/admin/service-desk/scenarios")
    validated = client.post("/api/admin/service-desk/scenarios/validate", json={"definition": load_definition_file("locked_user_account").model_dump(mode="json")})
    versions = client.get(f"/api/admin/service-desk/scenarios/{seeded['scenario_id']}/versions")
    version = db.query(ServiceDeskScenarioVersion).filter(ServiceDeskScenarioVersion.id == seeded["version_id"]).one()
    changed = copy.deepcopy(version.definition_json)
    changed["title"] = "Changed historical title"

    assert forbidden.status_code == 404
    assert direct_admin.status_code == 403
    assert listed.status_code == 200
    assert validated.status_code == 200
    assert validated.json()["data"]["valid"] is True
    assert versions.status_code == 200
    assert versions.json()["data"][0]["health"]["valid"] is True
    with pytest.raises(ScenarioDefinitionError):
        publish_definition(db, changed, published_by="admin")
    version.definition_json = changed
    with pytest.raises(ValueError, match="immutable"):
        db.commit()
    db.rollback()


def test_published_scenario_health_count_is_five(db):
    seed_scenario(db)
    repeated = seed_service_desk_scenarios(db)
    db.commit()
    versions = db.query(ServiceDeskScenarioVersion).filter(ServiceDeskScenarioVersion.status == "published").all()
    assert len(versions) == 5
    assert repeated["published"] == 5
    assert all(run_published_scenario_health(version)["valid"] is True for version in versions)


def test_admin_scenario_list_includes_version_health(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ADMIN_ENABLED", "true")
    seed_scenario(db)

    response = admin_client().get("/api/admin/service-desk/scenarios")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 5
    assert all(item["versions"] == [{
        "version_number": 1,
        "status": "published",
        "validation_status": "valid",
        "health_valid": True,
    }] for item in response.json()["data"])


def test_student_action_metadata_exposes_fields_not_accepted_values(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-safe-tool-metadata")
    enroll_beta(db, student)

    attempt = start_learning(student_client(), student, seeded["scenario_id"])
    action_metadata = {item["key"]: item for item in attempt["allowed_actions"]}

    assert action_metadata["verify_identity"]["payload_fields"] == ["verification_method"]
    assert "employee_id_last4" not in str(attempt)
    assert "correct_account_id" not in str(attempt)


def test_admin_can_manage_beta_assignments_and_knowledge_with_audit(db, monkeypatch):
    monkeypatch.setenv("SERVICE_DESK_LAB_ADMIN_ENABLED", "true")
    seeded = seed_scenario(db)
    student = make_student(db, "service-admin-controls")
    client = admin_client()

    enrolled = client.post("/api/admin/service-desk/beta-enrollments", json={"student_id": student.id, "note": "local review"})
    listed_enrollments = client.get("/api/admin/service-desk/beta-enrollments")
    assignment = client.post("/api/admin/service-desk/assignments", json={"student_id": student.id, "scenario_id": seeded["scenario_id"], "mode": "learning", "is_required": True})
    listed_assignments = client.get("/api/admin/service-desk/assignments")
    knowledge = client.get("/api/admin/service-desk/knowledge")
    saved_article = client.post("/api/admin/service-desk/knowledge", json={
        "stable_id": "local-review-article", "title": "Local review article", "category": "Review",
        "content": "This temporary local article verifies administrator knowledge management.", "status": "draft", "skill_tags": ["review"],
    })
    removed_assignment = client.delete(f"/api/admin/service-desk/assignments/{assignment.json()['data']['id']}")
    removed_enrollment = client.delete(f"/api/admin/service-desk/beta-enrollments/{student.id}")

    assert enrolled.status_code == 201
    assert any(row["student_id"] == student.id for row in listed_enrollments.json()["data"])
    assert assignment.status_code == 201
    assert any(row["id"] == assignment.json()["data"]["id"] for row in listed_assignments.json()["data"])
    assert knowledge.status_code == 200
    assert len(knowledge.json()["data"]) == 7
    assert saved_article.status_code == 201
    assert removed_assignment.status_code == 200
    assert removed_enrollment.status_code == 200
    actions = {row.action for row in db.query(ServiceDeskAuditLog).all()}
    assert {"beta_enrolled", "beta_removed", "assignment_saved", "assignment_removed", "knowledge_saved"}.issubset(actions)
