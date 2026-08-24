"""Phase 4B.2: real API-driven attempt/event/grading pipeline coverage for
the two live endpoint-management Service Desk scenarios (bitlocker-recovery,
offboarding-device-reassignment). Mirrors
test_phase4b1_microsoft_service_desk_scenarios.py's approach: both scenarios
use the same generic process-profile harness as the account-process
scenarios, since _device_process() produces the same 5-category shape.
"""
import pytest

from app.models.xp_ledger import XPLedger
from app.models.service_desk import ServiceDeskAttemptEvent
from app.routers import service_desk
from app.services.service_desk_objectives import SCENARIO_OBJECTIVES
from conftest import auth_headers, make_client, make_student
from test_service_desk_attempts import (
    _process_ticket_id,
    close,
    complete_process_workflow,
    setup_assignment,
    start,
)

ENDPOINT_STABLE_KEYS = ["bitlocker-recovery", "offboarding-device-reassignment"]

_REMEDIATION_EVENT = {
    "bitlocker-recovery": (
        "device.reveal_recovery_key",
        {"ticketId": "INC3001", "deviceId": "device-nex-lt-2214"},
    ),
    "offboarding-device-reassignment": (
        "device.reassign_device",
        {
            "ticketId": "INC3002",
            "deviceId": "device-nex-lt-3390",
            "action": "reset-and-reassign",
        },
    ),
}

_DECOY_REMEDIATION_EVENT = {
    "bitlocker-recovery": (
        "device.reveal_recovery_key",
        {"ticketId": "INC3001", "deviceId": "device-nex-lt-9999-decoy"},
    ),
    "offboarding-device-reassignment": (
        "device.reassign_device",
        {
            "ticketId": "INC3002",
            "deviceId": "device-nex-lt-9999-decoy",
            "action": "reset-and-reassign",
        },
    ),
}


def _reach_remediation(client, student, attempt_id, stable_key):
    definition = SCENARIO_OBJECTIVES[stable_key]
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    for category in definition.categories[:2]:
        for objective in category.objectives:
            rule = objective.any_of[0]
            response = client.post(
                path,
                headers=auth_headers(student),
                json={
                    "idempotency_key": f"prerequisite-{rule.event_type}",
                    "event_type": rule.event_type,
                    "tool": "chat" if rule.event_type.startswith("chat.") else "device",
                    "payload": rule.payload,
                },
            )
            assert response.status_code == 201, response.text


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_correct_flow_passes(db, stable_key):
    student = make_student(db, username=f"endpoint-correct-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    complete_process_workflow(client, student, attempt_id, stable_key)
    close(client, student, attempt_id)
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": f"complete-{stable_key}"},
    )
    assert grade.status_code == 201
    assert grade.json()["passed"] is True
    assert grade.json()["overall_score"] == 100


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_rejects_premature_action_before_investigation(db, stable_key):
    """Revealing a BitLocker key / reassigning a device before identity
    verification and diagnosis must be rejected by server-authoritative
    state, not merely graded low -- the critical-failure behavior the user
    explicitly required."""
    student = make_student(db, username=f"endpoint-premature-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    headers = auth_headers(student)
    path = f"/api/service-desk/attempts/{attempt_id}/actions"

    assert (
        client.post(
            path,
            headers=headers,
            json={
                "idempotency_key": "assign",
                "event_type": "ticket.assign",
                "tool": "ticket",
                "payload": {"ticketId": _process_ticket_id(stable_key)},
            },
        ).status_code
        == 201
    )

    event_type, payload = _REMEDIATION_EVENT[stable_key]
    response = client.post(
        path,
        headers=headers,
        json={"idempotency_key": "guessed-fix", "event_type": event_type, "tool": "device", "payload": payload},
    )
    assert response.status_code == 409
    assert "server-authoritative attempt state" in response.json()["detail"]


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_rejects_critical_action_against_decoy_device(db, stable_key):
    """Acting on a similar-looking decoy device must not silently pass --
    the exact-match-payload mechanism the account scenarios already use for
    wrong-user decoys, applied here to a wrong-device decoy."""
    student = make_student(db, username=f"endpoint-decoy-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    # Reach remediation legitimately, then prove that a similar-looking wrong
    # device is rejected as a safety violation rather than accepted as an
    # untrusted audit action.
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    _reach_remediation(client, student, attempt_id, stable_key)

    decoy_event_type, decoy_payload = _DECOY_REMEDIATION_EVENT[stable_key]
    decoy_response = client.post(
        path,
        headers=auth_headers(student),
        json={
            "idempotency_key": "decoy-attempt",
            "event_type": decoy_event_type,
            "tool": "device",
            "payload": decoy_payload,
        },
    )
    assert decoy_response.status_code == 409
    assert "server-authoritative attempt state" in decoy_response.json()["detail"]


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_rejects_wrong_requester_identity(db, stable_key):
    student = make_student(db, username=f"endpoint-wrong-requester-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    definition = SCENARIO_OBJECTIVES[stable_key]
    inspect_rule = definition.categories[0].objectives[0].any_of[0]
    identity_rule = definition.categories[0].objectives[1].any_of[0]
    path = f"/api/service-desk/attempts/{attempt_id}/actions"

    inspected = client.post(
        path,
        headers=auth_headers(student),
        json={
            "idempotency_key": "inspect-correct-device",
            "event_type": inspect_rule.event_type,
            "tool": "device",
            "payload": inspect_rule.payload,
        },
    )
    assert inspected.status_code == 201, inspected.text

    wrong_identity = client.post(
        path,
        headers=auth_headers(student),
        json={
            "idempotency_key": "verify-wrong-requester",
            "event_type": identity_rule.event_type,
            "tool": "chat",
            "payload": identity_rule.payload
            | {"contactId": "directory-user-wrong-requester"},
        },
    )

    assert wrong_identity.status_code == 409
    assert "server-authoritative attempt state" in wrong_identity.json()["detail"]


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_critical_action_replay_is_idempotent(db, stable_key):
    student = make_student(db, username=f"endpoint-action-replay-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    _reach_remediation(client, student, attempt_id, stable_key)
    event_type, payload = _REMEDIATION_EVENT[stable_key]
    request = {
        "idempotency_key": "critical-remediation-once",
        "event_type": event_type,
        "tool": "device",
        "payload": payload,
    }
    path = f"/api/service-desk/attempts/{attempt_id}/actions"

    first = client.post(path, headers=auth_headers(student), json=request)
    replay = client.post(path, headers=auth_headers(student), json=request)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert first.json() == replay.json()
    assert (
        db.query(ServiceDeskAttemptEvent)
        .filter_by(attempt_id=attempt_id, idempotency_key="critical-remediation-once")
        .count()
        == 1
    )


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_rejects_cross_ticket_device_evidence(db, stable_key):
    student = make_student(db, username=f"endpoint-cross-ticket-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    ticket_id = _process_ticket_id(stable_key)
    wrong_ticket_id = "INC3002" if ticket_id == "INC3001" else "INC3001"

    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": "cross-ticket-inspection",
            "event_type": "device.inspect_record",
            "tool": "device",
            "payload": {
                "ticketId": wrong_ticket_id,
                "deviceId": "device-nex-lt-2214" if ticket_id == "INC3001" else "device-nex-lt-3390",
            },
        },
    )

    assert response.status_code == 201
    event = (
        db.query(ServiceDeskAttemptEvent)
        .filter_by(attempt_id=attempt_id, idempotency_key="cross-ticket-inspection")
        .one()
    )
    assert event.trusted is False


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_replay_is_idempotent_and_starts_new_attempt(db, stable_key):
    student = make_student(db, username=f"endpoint-replay-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    first_attempt_id = start(client, student, assignment).json()["id"]
    complete_process_workflow(client, student, first_attempt_id, stable_key)
    close(client, student, first_attempt_id)

    body = {"idempotency_key": "complete-1"}
    first = client.post(
        f"/api/service-desk/attempts/{first_attempt_id}/complete",
        headers=auth_headers(student),
        json=body,
    )
    second = client.post(
        f"/api/service-desk/attempts/{first_attempt_id}/complete",
        headers=auth_headers(student),
        json=body,
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json() == second.json()

    db.refresh(student)
    xp_rows = (
        db.query(XPLedger)
        .filter_by(student_id=student.id, source_type="service_desk_mastery", source_id=assignment.scenario_id)
        .all()
    )
    assert len(xp_rows) == 1

    replay = start(client, student, assignment)
    assert replay.status_code == 201
    assert replay.json()["attempt_number"] == 2


@pytest.mark.parametrize("stable_key", ENDPOINT_STABLE_KEYS)
def test_endpoint_scenario_attempt_is_isolated_to_its_owning_student(db, stable_key):
    owner = make_student(db, username=f"endpoint-owner-{stable_key}")
    other = make_student(db, username=f"endpoint-other-{stable_key}")
    assignment = setup_assignment(db, owner, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, owner, assignment).json()["id"]

    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(other)).status_code == 403
    assert (
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/complete",
            headers=auth_headers(other),
            json={"idempotency_key": "trespass-complete"},
        ).status_code
        == 403
    )


def test_endpoint_device_events_require_a_device_id_at_the_api_boundary(db):
    student = make_student(db, username="endpoint-missing-device-id")
    assignment = setup_assignment(db, student, stable_key="bitlocker-recovery", process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]

    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": "missing-device-id",
            "event_type": "device.inspect_record",
            "tool": "device",
            "payload": {},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Device events require deviceId"


def test_endpoint_device_events_require_a_ticket_id_at_the_api_boundary(db):
    student = make_student(db, username="endpoint-missing-ticket-id")
    assignment = setup_assignment(db, student, stable_key="bitlocker-recovery", process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]

    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": "missing-ticket-id",
            "event_type": "device.inspect_record",
            "tool": "device",
            "payload": {"deviceId": "device-nex-lt-2214"},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Device events require ticketId"
