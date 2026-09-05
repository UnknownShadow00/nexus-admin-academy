"""HTTP/ledger integration tests for the four immutable realism fixtures."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttemptEvent,
    ServiceDeskScenarioVersion,
)
from app.routers import service_desk
from app.services.service_desk_realism import fixture_catalog, replay, run_command
from app.services.service_desk_objectives import evaluate_objectives
from conftest import auth_headers, make_client, make_student
from test_service_desk_attempts import setup_assignment, start, close

ROOT = Path(__file__).resolve().parents[2]
TRACES = json.loads(
    (ROOT / "service-desk-app/packages/shared/src/realism-traces.test.json").read_text()
)
FIXTURES = fixture_catalog()


def setup(db, ticket):
    student = make_student(db, username=f"realism-{ticket}")
    assignment = setup_assignment(
        db, student, stable_key=ticket.lower(), process_profile=True, mode="learning"
    )
    version = ServiceDeskScenarioVersion(
        scenario_id=assignment.scenario_id,
        version_number=2,
        status="published",
        definition_hash=f"realism-{ticket}",
        definition_json={
            "id": ticket,
            "priority": "high",
            "objective_catalog_version": "realism-v1",
            "simulation_fixture": FIXTURES[ticket],
        },
    )
    db.add(version)
    db.commit()
    client = make_client(service_desk.router)
    response = start(client, student, assignment)
    assert response.status_code in {200, 201}, response.text
    return client, student, response.json()["id"], version


def action(
    client,
    student,
    attempt,
    ticket,
    command=None,
    *,
    event_type="remote_desktop.run_terminal_command",
    payload=None,
    suffix="",
):
    return client.post(
        f"/api/service-desk/attempts/{attempt}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": f"{event_type}-{command}-{suffix}",
            "event_type": event_type,
            "tool": "ticket" if event_type.startswith("ticket.") else "remote_desktop",
            "payload": payload
            if payload is not None
            else {"assetTag": FIXTURES[ticket]["assetTag"], "command": command},
        },
    )


def ledger(db, attempt):
    return (
        db.query(ServiceDeskAttemptEvent)
        .filter_by(attempt_id=attempt)
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )


def walk(client, student, attempt, ticket, commands=None):
    for index, command in enumerate(commands or TRACES[ticket]["commands"]):
        response = action(client, student, attempt, ticket, command, suffix=str(index))
        assert response.status_code in {200, 201}, (command, response.text)


def note(client, student, attempt, ticket):
    response = action(
        client,
        student,
        attempt,
        ticket,
        event_type="remote_desktop.add_internal_note",
        payload={
            "ticketId": ticket,
            "assetTag": FIXTURES[ticket]["assetTag"],
            "text": TRACES[ticket]["note"],
        },
    )
    assert response.status_code in {200, 201}, response.text


def test_packaged_fixture_is_identical_to_shared_source():
    assert FIXTURES == json.loads(
        (
            ROOT / "service-desk-app/packages/shared/src/service-desk-realism-v1.json"
        ).read_text()
    )


@pytest.mark.parametrize("ticket", TRACES)
def test_real_tool_path_passes_with_exact_rubric(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket)
    note(client, student, attempt, ticket)
    complete, checks = evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )
    assert complete, checks
    if ticket == "INC2509":
        response = action(
            client,
            student,
            attempt,
            ticket,
            event_type="ticket.escalate",
            payload={
                "ticketId": ticket,
                "reason": "change-approval-required",
                "routeTeam": "Application Support",
            },
        )
        assert response.status_code in {200, 201}, response.text
    else:
        close(client, student, attempt)
    response = client.post(
        f"/api/service-desk/attempts/{attempt}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "complete"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["passed"] is True, response.json()
    assert response.json()["details"]["process_weights"] == {
        "investigation": 15,
        "diagnosis": 25,
        "remediation": 30,
        "verification": 20,
        "documentation": 10,
    }


@pytest.mark.parametrize("ticket", TRACES)
def test_wizard_and_forged_client_evidence_cannot_pass(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    for step in (
        "inspect-symptom",
        "collect-evidence",
        "isolate-root-cause",
        "apply-safe-remediation",
        "verify-original-symptom",
    ):
        response = action(
            client,
            student,
            attempt,
            ticket,
            event_type="remote_desktop.perform_scenario_step",
            payload={
                "ticketId": ticket,
                "assetTag": FIXTURES[ticket]["assetTag"],
                "stepId": f"scenario.{step}",
            },
            suffix=step,
        )
        assert response.status_code == 409
    response = action(
        client,
        student,
        attempt,
        ticket,
        payload={
            "assetTag": FIXTURES[ticket]["assetTag"],
            "command": "help",
            "realismEvidence": FIXTURES[ticket]["categories"]["remediation"][0],
        },
    )
    assert response.status_code in {200, 201}
    assert not evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )[0]
    assert not replay(FIXTURES[ticket], ledger(db, attempt))["realism"]["observed"]


@pytest.mark.parametrize("ticket", TRACES)
def test_wrong_device_rejected_and_raw_events_cannot_mutate_state(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    response = action(
        client,
        student,
        attempt,
        ticket,
        payload={"assetTag": "NX-9999", "command": "help"},
    )
    assert response.status_code == 409
    command = TRACES[ticket]["commands"][-1]
    response = client.post(
        f"/api/service-desk/attempts/{attempt}/events",
        headers=auth_headers(student),
        json={
            "idempotency_key": "fabricated",
            "event_type": "remote_desktop.run_terminal_command",
            "tool": "remote_desktop",
            "payload": {
                "assetTag": FIXTURES[ticket]["assetTag"],
                "command": command,
                "realismEvidence": FIXTURES[ticket]["categories"]["verification"][0],
            },
            "success": True,
            "resulting_state": {"realism": {"repaired": True}},
        },
    )
    assert response.status_code in {200, 201}
    assert replay(FIXTURES[ticket], ledger(db, attempt)) == FIXTURES[ticket]["initial"]
    assert not evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )[0]


def test_broad_access_opens_share_but_cannot_pass_even_after_correct_change(db):
    ticket = "INC2505"
    client, student, attempt, version = setup(db, ticket)
    walk(
        client,
        student,
        attempt,
        ticket,
        [
            "Add-ADGroupMember -Identity All-Departments-RW -Members taylor.reed",
            "Start-UserSession taylor.reed",
        ],
    )
    state = replay(FIXTURES[ticket], ledger(db, attempt))
    _, output, success = run_command(
        state, FIXTURES[ticket], TRACES[ticket]["commands"][-1]
    )
    assert success and "Share opens" in output[0]
    walk(client, student, attempt, ticket)
    note(client, student, attempt, ticket)
    assert not evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )[0]
    close(client, student, attempt)
    grade = client.post(
        f"/api/service-desk/attempts/{attempt}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "harmful-complete"},
    ).json()
    assert grade["critical_failure"] is True
    assert grade["passed"] is False


def test_early_repair_cannot_earn_prechange_evidence_retroactively(db):
    ticket = "INC2504"
    client, student, attempt, version = setup(db, ticket)
    walk(
        client,
        student,
        attempt,
        ticket,
        ["Set-PrinterPort -Name ENG-COPIER -PrinterHostAddress 10.26.19.94"],
    )
    walk(client, student, attempt, ticket)
    note(client, student, attempt, ticket)
    passed, checks = evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )
    assert not passed and not checks["investigation"] and not checks["diagnosis"]


@pytest.mark.parametrize("ticket", TRACES)
def test_verification_before_repair_is_not_final_verification(ticket):
    fixture = FIXTURES[ticket]
    state = deepcopy(fixture["initial"])
    state, _, _ = run_command(state, fixture, TRACES[ticket]["commands"][-1])
    assert state["realism"]["lastEvidence"] not in fixture["categories"]["verification"]


def test_profile_data_is_preserved_when_destructive_operation_is_refused():
    fixture = FIXTURES["INC2501"]
    state, _, success = run_command(
        fixture["initial"], fixture, "Remove-UserProfile -User morgan.ellis"
    )
    assert not success and state["filesystem"]["nodes"]["documents"]["available"]


def test_cleanup_is_ineffective_against_recurrence():
    fixture = FIXTURES["INC2509"]
    state, _, success = run_command(fixture["initial"], fixture, "Clear-TempFiles C:")
    assert success and state["storage"]["freeBytes"] == 4 * 1024**3
    assert (
        state["storage"]["retention"] == "unbounded"
        and not state["realism"]["repaired"]
    )


@pytest.mark.parametrize("ticket", TRACES)
def test_resume_preserves_ledger_and_retry_starts_clean(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket, TRACES[ticket]["commands"][:2])
    before = replay(FIXTURES[ticket], ledger(db, attempt))
    response = client.get(
        f"/api/service-desk/attempts/{attempt}", headers=auth_headers(student)
    )
    assert response.status_code == 200
    assert replay(FIXTURES[ticket], ledger(db, attempt)) == before
    close(client, student, attempt)
    response = client.post(
        f"/api/service-desk/attempts/{attempt}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "failed-close"},
    )
    assert response.status_code == 201 and not response.json()["passed"]
    assignment = (
        db.query(ServiceDeskAssignment)
        .filter_by(student_id=student.id, scenario_id=version.scenario_id)
        .one()
    )
    fresh = start(client, student, assignment)
    assert fresh.status_code in {200, 201}, fresh.text
    assert fresh.json()["id"] != attempt
    assert (
        replay(FIXTURES[ticket], ledger(db, fresh.json()["id"]))
        == FIXTURES[ticket]["initial"]
    )


@pytest.mark.parametrize("ticket", TRACES)
def test_unfinished_workspace_and_limited_debrief_do_not_disclose_solution(db, ticket):
    from types import SimpleNamespace
    from app.services.service_desk_workspace_view import build_debrief
    from app.services.service_desk_objectives import objective_definition

    client, student, attempt, version = setup(db, ticket)
    visible = service_desk._student_scenario_definition(
        version.definition_json, "guided"
    )
    assert "simulation_fixture" not in visible
    brief = build_debrief(
        version.definition_json,
        [],
        SimpleNamespace(passed=False, overall_score=0, details_json={}),
        stable_key=ticket.lower(),
        objective_def=objective_definition(ticket.lower(), version.definition_json),
        attempts_remaining=2,
    )
    assert brief["stronger_path"] == [] and brief["escalation_feedback"] is None
    assert FIXTURES[ticket]["completion"]["rootCause"] not in json.dumps(brief)


def test_restoring_the_stale_port_after_verification_invalidates_completion(db):
    ticket = "INC2504"
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket)
    note(client, student, attempt, ticket)
    walk(
        client,
        student,
        attempt,
        ticket,
        ["Set-PrinterPort -Name ENG-COPIER -PrinterHostAddress 10.26.19.80"],
    )
    passed, checks = evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )
    assert not passed and not checks["verification"]
