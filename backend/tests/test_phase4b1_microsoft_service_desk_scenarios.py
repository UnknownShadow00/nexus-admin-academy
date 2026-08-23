"""Phase 4B.1 verification: real API-driven attempt/event/grading pipeline
coverage for the two new live Microsoft Workplace Service Desk scenarios
(m365-entra-auth-method, m365-signin-conditional-access). Reuses the same
harness as the existing account-process scenarios (locked-user-account,
password-reset, mfa-reset) since both new scenarios are built with the same
_account_process() factory in service_desk_objectives.py -- this proves the
real API pipeline grades them correctly, not just that their objective
definitions parse.
"""
import pytest

from app.models.xp_ledger import XPLedger
from app.routers import service_desk
from conftest import auth_headers, make_client, make_student
from test_service_desk_attempts import (
    _process_ticket_id,
    close,
    complete_process_workflow,
    setup_assignment,
    start,
)

M365_STABLE_KEYS = ["m365-entra-auth-method", "m365-signin-conditional-access"]


@pytest.mark.parametrize("stable_key", M365_STABLE_KEYS)
def test_m365_scenario_correct_flow_passes(db, stable_key):
    student = make_student(db, username=f"m365-correct-{stable_key}")
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


@pytest.mark.parametrize("stable_key", M365_STABLE_KEYS)
def test_m365_scenario_rejects_premature_fix_before_investigation(db, stable_key):
    """Jumping straight to the remediation action (skipping identity
    verification / diagnosis) must be rejected by server-authoritative state,
    not merely graded low -- proving this isn't a self-attested checkbox."""
    student = make_student(db, username=f"m365-premature-{stable_key}")
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

    # The remediation event for each m365 scenario, attempted with no prior
    # identity verification or diagnosis step.
    remediation_event_type = "directory.reset_mfa" if stable_key == "m365-entra-auth-method" else "directory.enable_account"
    remediation_directory_user_id = (
        "directory-user-priya-nair" if stable_key == "m365-entra-auth-method" else "directory-user-owen-mackay"
    )
    response = client.post(
        path,
        headers=headers,
        json={
            "idempotency_key": "guessed-fix",
            "event_type": remediation_event_type,
            "tool": "directory",
            "payload": {"directoryUserId": remediation_directory_user_id},
        },
    )
    assert response.status_code == 409
    assert "server-authoritative attempt state" in response.json()["detail"]


@pytest.mark.parametrize("stable_key", M365_STABLE_KEYS)
def test_m365_scenario_replay_is_idempotent_and_starts_a_new_attempt_number(db, stable_key):
    student = make_student(db, username=f"m365-replay-{stable_key}")
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
    assert first.json() == second.json(), "replaying the same idempotency_key must not re-grade or double-award"

    db.refresh(student)
    xp_rows = (
        db.query(XPLedger)
        .filter_by(student_id=student.id, source_type="service_desk_mastery", source_id=assignment.scenario_id)
        .all()
    )
    assert len(xp_rows) == 1, "XP must be awarded exactly once despite the replayed completion call"

    replay = start(client, student, assignment)
    assert replay.status_code == 201
    assert replay.json()["attempt_number"] == 2


@pytest.mark.parametrize("stable_key", M365_STABLE_KEYS)
def test_m365_scenario_attempt_is_isolated_to_its_owning_student(db, stable_key):
    owner = make_student(db, username=f"m365-owner-{stable_key}")
    other = make_student(db, username=f"m365-other-{stable_key}")
    assignment = setup_assignment(db, owner, stable_key=stable_key, process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, owner, assignment).json()["id"]

    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(other)).status_code == 403
    assert (
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/actions",
            headers=auth_headers(other),
            json={
                "idempotency_key": "trespass",
                "event_type": "ticket.assign",
                "tool": "ticket",
                "payload": {"ticketId": _process_ticket_id(stable_key)},
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/complete",
            headers=auth_headers(other),
            json={"idempotency_key": "trespass-complete"},
        ).status_code
        == 403
    )
