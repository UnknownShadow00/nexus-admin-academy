"""First-class escalation grading for the Service Desk redesign (Group 3).

Covers the taxonomy, the trusted ``ticket.escalate`` transition, the priority
scenarios ``inc2506`` (pure escalation) and ``inc2508`` (contain then escalate),
verification treated as N/A rather than fake completion, normalized process
scoring, and the guarantee that ordinary-scenario grading is unchanged.
"""

from app.routers import service_desk
from conftest import auth_headers, make_student
from test_service_desk_attempts import (
    close,
    complete_process_workflow,
    make_client,
    setup_assignment,
    start,
)

STEP = "remote_desktop.perform_scenario_step"


def _client():
    return make_client(service_desk.router)


def _assign(client, student, attempt_id, ticket_id):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": "assign",
            "event_type": "ticket.assign",
            "tool": "ticket",
            "payload": {"ticketId": ticket_id},
        },
    )


def _step(client, student, attempt_id, ticket_id, asset_tag, step_id, *, key=None):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": key or step_id,
            "event_type": STEP,
            "tool": "remote_desktop",
            "payload": {
                "ticketId": ticket_id,
                "assetTag": asset_tag,
                "stepId": step_id,
            },
        },
    )


def _internal_note(client, student, attempt_id, ticket_id, asset_tag):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": "note",
            "event_type": "remote_desktop.add_internal_note",
            "tool": "remote_desktop",
            "payload": {
                "ticketId": ticket_id,
                "assetTag": asset_tag,
                "body": "Evidence gathered; access request is outside my authority.",
            },
        },
    )


def _escalate(client, student, attempt_id, ticket_id, reason, route, *, key="escalate"):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": key,
            "event_type": "ticket.escalate",
            "tool": "ticket",
            "payload": {"ticketId": ticket_id, "reason": reason, "routeTeam": route},
        },
    )


def _complete(client, student, attempt_id, key="complete"):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": key},
    )


def _investigate_and_diagnose(client, student, attempt_id, ticket_id, asset_tag):
    assert _assign(client, student, attempt_id, ticket_id).status_code == 201
    assert (
        _step(
            client, student, attempt_id, ticket_id, asset_tag, "scenario.inspect-symptom"
        ).status_code
        == 201
    )
    assert (
        _step(
            client,
            student,
            attempt_id,
            ticket_id,
            asset_tag,
            "scenario.isolate-root-cause",
        ).status_code
        == 201
    )


# --------------------------------------------------------------------------- #
# Taxonomy / transition validation
# --------------------------------------------------------------------------- #


def test_unknown_escalation_reason_is_rejected(db):
    student = make_student(db, username="esc-bad-reason")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2506", "NX-2506")
    response = _escalate(
        client, student, attempt_id, "INC2506", "made-up-reason", "Identity & Access"
    )
    assert response.status_code == 422


def test_escalation_to_wrong_route_is_not_trusted(db):
    student = make_student(db, username="esc-wrong-route")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2506", "NX-2506")
    response = _escalate(
        client, student, attempt_id, "INC2506", "policy-authorization", "Service Desk"
    )
    assert response.status_code == 409


def test_escalation_before_investigation_is_blocked(db):
    student = make_student(db, username="esc-premature")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    assert _assign(client, student, attempt_id, "INC2506").status_code == 201
    response = _escalate(
        client,
        student,
        attempt_id,
        "INC2506",
        "policy-authorization",
        "Identity & Access",
    )
    assert response.status_code == 409
    assert "investigation" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# INC2506 - restricted access, pure escalation, verification N/A
# --------------------------------------------------------------------------- #


def test_inc2506_correct_escalation_passes_with_normalized_full_score(db):
    student = make_student(db, username="esc-2506-ok")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2506", "NX-2506")
    assert (
        _internal_note(client, student, attempt_id, "INC2506", "NX-2506").status_code
        == 201
    )
    assert (
        _escalate(
            client,
            student,
            attempt_id,
            "INC2506",
            "policy-authorization",
            "Identity & Access",
        ).status_code
        == 201
    )
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is True
    assert body["critical_failure"] is False
    # All applicable process categories earned -> normalized 100%.
    assert body["overall_score"] == 100
    details = body["details"]
    assert details["escalation_expected"] is True
    assert details["escalated"] is True
    assert details["escalation_route"] == "Identity & Access"
    assert details["escalation_reason"] == "policy-authorization"
    assert details["prohibited_hit"] is False
    # Verification is N/A for a pure escalation - never reported as earned work.
    assert details["verification_applicable"] is False
    assert details["containment_met"] is None
    assert details["process_points"] == 100


def test_inc2506_self_service_remediation_is_a_critical_failure(db):
    student = make_student(db, username="esc-2506-selfserve")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2506", "NX-2506")
    assert (
        _step(
            client,
            student,
            attempt_id,
            "INC2506",
            "NX-2506",
            "scenario.apply-safe-remediation",
        ).status_code
        == 201
    )
    assert (
        _step(
            client,
            student,
            attempt_id,
            "INC2506",
            "NX-2506",
            "scenario.verify-original-symptom",
        ).status_code
        == 201
    )
    assert (
        _internal_note(client, student, attempt_id, "INC2506", "NX-2506").status_code
        == 201
    )
    close(client, student, attempt_id)
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is False
    assert body["critical_failure"] is True
    assert body["details"]["prohibited_hit"] is True


def test_inc2506_close_without_escalation_does_not_pass(db):
    student = make_student(db, username="esc-2506-noescalate")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2506", "NX-2506")
    assert (
        _internal_note(client, student, attempt_id, "INC2506", "NX-2506").status_code
        == 201
    )
    close(client, student, attempt_id)
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is False
    assert body["critical_failure"] is False


# --------------------------------------------------------------------------- #
# INC2508 - phishing: contain THEN escalate
# --------------------------------------------------------------------------- #


def test_inc2508_containment_without_escalation_is_incomplete(db):
    student = make_student(db, username="esc-2508-containonly")
    assignment = setup_assignment(
        db, student, stable_key="inc2508", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2508", "NX-2508")
    assert (
        _step(
            client,
            student,
            attempt_id,
            "INC2508",
            "NX-2508",
            "scenario.apply-safe-remediation",
        ).status_code
        == 201
    )
    assert (
        _internal_note(client, student, attempt_id, "INC2508", "NX-2508").status_code
        == 201
    )
    close(client, student, attempt_id)
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    assert grade.json()["passed"] is False


def test_inc2508_escalation_without_containment_is_incomplete(db):
    student = make_student(db, username="esc-2508-noconatin")
    assignment = setup_assignment(
        db, student, stable_key="inc2508", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2508", "NX-2508")
    assert (
        _internal_note(client, student, attempt_id, "INC2508", "NX-2508").status_code
        == 201
    )
    assert (
        _escalate(
            client,
            student,
            attempt_id,
            "INC2508",
            "security-incident",
            "Information Security",
        ).status_code
        == 201
    )
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is False
    assert body["details"]["containment_met"] is False
    assert body["details"]["verification_applicable"] is True


def test_inc2508_contain_then_escalate_passes(db):
    student = make_student(db, username="esc-2508-ok")
    assignment = setup_assignment(
        db, student, stable_key="inc2508", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2508", "NX-2508")
    assert (
        _step(
            client,
            student,
            attempt_id,
            "INC2508",
            "NX-2508",
            "scenario.apply-safe-remediation",
        ).status_code
        == 201
    )
    assert (
        _internal_note(client, student, attempt_id, "INC2508", "NX-2508").status_code
        == 201
    )
    assert (
        _escalate(
            client,
            student,
            attempt_id,
            "INC2508",
            "security-incident",
            "Information Security",
        ).status_code
        == 201
    )
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is True
    assert body["critical_failure"] is False
    assert body["overall_score"] == 100
    details = body["details"]
    assert details["verification_applicable"] is True
    assert details["containment_met"] is True
    assert details["escalation_route"] == "Information Security"


# --------------------------------------------------------------------------- #
# Ordinary scenarios are untouched
# --------------------------------------------------------------------------- #


def test_ordinary_scenario_escalation_does_not_resolve(db):
    student = make_student(db, username="esc-ordinary")
    assignment = setup_assignment(
        db, student, stable_key="inc2507", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    _investigate_and_diagnose(client, student, attempt_id, "INC2507", "NX-2507")
    response = _escalate(
        client, student, attempt_id, "INC2507", "security-incident", "Information Security"
    )
    # Recorded, but never trusted for an ordinary scenario.
    assert response.status_code == 201
    close(client, student, attempt_id)
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is False
    assert body["critical_failure"] is False
    assert body["details"].get("escalation_expected") is False
    assert body["details"].get("escalation_attempted") is True


def test_ordinary_scenario_grading_unchanged(db):
    student = make_student(db, username="ordinary-unchanged")
    assignment = setup_assignment(
        db, student, stable_key="inc2507", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    complete_process_workflow(client, student, attempt_id, "inc2507")
    close(client, student, attempt_id)
    grade = _complete(client, student, attempt_id)
    assert grade.status_code == 201, grade.text
    body = grade.json()
    assert body["passed"] is True
    assert body["overall_score"] == 100
    assert body["critical_failure"] is False
    assert "escalation_expected" not in body["details"]
