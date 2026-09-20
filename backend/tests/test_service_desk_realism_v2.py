"""New immutable versions: HTTP transitions, ordered evidence and real outcomes."""

from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from app.models.service_desk import ServiceDeskAssignment
from app.services.service_desk_realism import replay, run_command
from app.services.service_desk_objectives import (
    evaluate_objectives,
    objective_definition,
)
from app.services.service_desk_workspace_view import build_debrief
from app.routers import service_desk
from conftest import auth_headers
from test_service_desk_attempts import close, start
from test_service_desk_realism import ROOT, FIXTURES, setup, action, walk, ledger

TRACES = json.loads(
    (
        ROOT / "service-desk-app/packages/shared/src/realism-v2-traces.test.json"
    ).read_text()
)
TRACES_V1 = json.loads(
    (ROOT / "service-desk-app/packages/shared/src/realism-traces.test.json").read_text()
)
ALL_TRACES = {**TRACES_V1, **TRACES}
ACTIVE_SERVICE_DESK_TRACES = tuple(
    ticket for ticket in sorted(ALL_TRACES) if ticket != "INC2504"
)


def add_note(client, student, attempt, ticket):
    result = action(
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
    assert result.status_code in {200, 201}, result.text


def complete(client, student, attempt):
    result = client.post(
        f"/api/service-desk/attempts/{attempt}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "complete"},
    )
    assert result.status_code == 201, result.text
    return result.json()


@pytest.mark.parametrize("ticket", ACTIVE_SERVICE_DESK_TRACES)
def test_all_ten_current_scenarios_reject_the_wizard_and_reach_terminal_outcome(
    db, ticket
):
    """Compact current-catalog integration check across both realism versions."""
    client, student, attempt, version = setup(db, ticket)
    fixture = FIXTURES[ticket]

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
                "assetTag": fixture["assetTag"],
                "stepId": f"scenario.{step}",
            },
            suffix=f"smoke-{step}",
        )
        assert response.status_code == 409

    trace = ALL_TRACES[ticket]
    walk(client, student, attempt, ticket, trace["commands"])
    response = action(
        client,
        student,
        attempt,
        ticket,
        event_type="remote_desktop.add_internal_note",
        payload={
            "ticketId": ticket,
            "assetTag": fixture["assetTag"],
            "text": trace["note"],
        },
        suffix="smoke-note",
    )
    assert response.status_code in {200, 201}, response.text

    route = fixture.get("escalation")
    if route:
        response = action(
            client,
            student,
            attempt,
            ticket,
            event_type="ticket.escalate",
            payload={
                "ticketId": ticket,
                "routeTeam": route["route"],
                "reason": route["reasons"][0],
            },
            suffix="smoke-escalate",
        )
        assert response.status_code in {200, 201}, response.text
    elif ticket == "INC2509":
        response = action(
            client,
            student,
            attempt,
            ticket,
            event_type="ticket.escalate",
            payload={
                "ticketId": ticket,
                "routeTeam": "Application Support",
                "reason": "change-approval-required",
            },
            suffix="smoke-escalate",
        )
        assert response.status_code in {200, 201}, response.text
    else:
        close(client, student, attempt)

    grade = complete(client, student, attempt)
    assert grade["passed"] is True, (ticket, grade)
    assert version.definition_json["simulation_fixture"]["commands"]


@pytest.mark.parametrize("ticket", TRACES)
def test_ordered_real_workflow_passes_and_only_applicable_categories_earn_credit(
    db, ticket
):
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket, TRACES[ticket]["commands"])
    add_note(client, student, attempt, ticket)
    ready, checks = evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )
    assert ready, checks
    route = FIXTURES[ticket].get("escalation")
    if route:
        response = action(
            client,
            student,
            attempt,
            ticket,
            event_type="ticket.escalate",
            payload={
                "ticketId": ticket,
                "routeTeam": route["route"],
                "reason": route["reasons"][0],
            },
        )
        assert response.status_code in {200, 201}, response.text
    else:
        close(client, student, attempt)
    grade = complete(client, student, attempt)
    assert grade["passed"], grade
    assert grade["details"]["process_weights"] == dict(
        investigation=15,
        diagnosis=25,
        remediation=30,
        verification=20,
        documentation=10,
    )
    if route and not route["verificationApplicable"]:
        assert not checks["verification"]
        assert grade["details"]["verification_applicable"] is False


@pytest.mark.parametrize("ticket", TRACES)
def test_all_five_wizard_steps_and_wrong_targets_are_rejected(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    for step in [
        "inspect-symptom",
        "collect-evidence",
        "isolate-root-cause",
        "apply-safe-remediation",
        "verify-original-symptom",
    ]:
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
    for payload in [
        {"assetTag": "NX-OTHER", "command": "help"},
        {
            "assetTag": FIXTURES[ticket]["assetTag"],
            "command": "Reset-Password other.student",
        },
        {
            "assetTag": FIXTURES[ticket]["assetTag"],
            "command": "Ask-Requester arbitrary-client-text",
        },
    ]:
        assert (
            action(client, student, attempt, ticket, payload=payload).status_code == 409
        )
    response = action(
        client,
        student,
        attempt,
        ticket,
        payload={
            "assetTag": FIXTURES[ticket]["assetTag"],
            "command": "help",
            "realismEvidence": "fabricated",
        },
    )
    assert response.status_code in {200, 201}
    assert not replay(FIXTURES[ticket], ledger(db, attempt))["realism"]["observed"]
    assert not evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )[0]


@pytest.mark.parametrize("ticket", TRACES)
def test_resume_retry_and_limited_coaching_are_isolated(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket, TRACES[ticket]["commands"][:2])
    before = replay(FIXTURES[ticket], ledger(db, attempt))
    assert (
        client.get(
            f"/api/service-desk/attempts/{attempt}", headers=auth_headers(student)
        ).status_code
        == 200
    )
    assert replay(FIXTURES[ticket], ledger(db, attempt)) == before
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
    close(client, student, attempt)
    assert not complete(client, student, attempt)["passed"]
    assignment = (
        db.query(ServiceDeskAssignment)
        .filter_by(student_id=student.id, scenario_id=version.scenario_id)
        .one()
    )
    fresh = start(client, student, assignment)
    assert fresh.status_code in {200, 201}
    assert fresh.json()["id"] != attempt
    assert (
        replay(FIXTURES[ticket], ledger(db, fresh.json()["id"]))
        == FIXTURES[ticket]["initial"]
    )


def run(ticket, commands):
    fixture = FIXTURES[ticket]
    state = deepcopy(fixture["initial"])
    outputs = []
    for command in commands:
        state, output, success = run_command(state, fixture, command)
        assert success, command
        outputs.append(output)
    return state, outputs


def test_excel_wrong_extension_blank_and_application_repair_do_not_isolate_or_fix():
    state, output = run(
        "INC2502",
        [
            "excel new",
            "excel disable PDF-Export",
            "excel repair",
            "excel open Monthly.xlsx",
        ],
    )
    assert "closed" in str(output[-1])
    assert not state["realism"]["repaired"]
    assert "reproduced" not in state["realism"]["observed"]
    state, _ = run(
        "INC2502",
        ["excel disable all", "excel open Monthly.xlsx", "excel save Monthly.xlsx"],
    )
    assert state["office"]["saved"]  # Technically usable, but not targeted remediation.
    assert not state["realism"]["repaired"]
    assert "normal-save" not in state["realism"]["observed"]


@pytest.mark.parametrize(
    "temporary", ["Unlock-Account avery.monroe", "Reset-Password avery.monroe"]
)
def test_lockout_recurrence_is_a_real_failing_check(temporary):
    state, _ = run(
        "INC2507", [temporary, "Advance-Time 15", "Test-Account avery.monroe"]
    )
    assert state["account"]["locked"]
    assert not state["account"]["observedStable"]
    stable, _ = run("INC2507", TRACES["INC2507"]["commands"])
    assert stable["account"]["observedStable"] and not stable["account"]["locked"]


def test_password_only_leaves_phishing_sessions_and_delay_worsens_risk():
    state, _ = run(
        "INC2508", ["Reset-Password riley.brown", "Test-Containment riley.brown"]
    )
    assert state["security"]["sessionsActive"] and not state["security"]["controlled"]
    delayed, _ = run("INC2508", ["Advance-Time 15", "Advance-Time 15"])
    assert delayed["security"]["mailboxRule"] and delayed["realism"]["harmful"]
    safe, _ = run(
        "INC2508",
        TRACES["INC2508"]["commands"] + ["Advance-Time 15", "Advance-Time 15"],
    )
    assert not safe["realism"]["harmful"]


def test_user_password_change_does_not_repair_computer_channel():
    state, output = run(
        "INC2510",
        ["Reset-Password sam.ortiz", "Test-DomainSignIn sam.ortiz -Computer NX-2510"],
    )
    assert state["trust"]["passwordVersion"] == 2
    assert state["machine"]["domainJoinState"] == "trust-broken"
    assert "failed" in str(output[-1])


@pytest.mark.parametrize(
    "ticket,command",
    [
        ("INC2503", "Set-SwitchPort B-17 -Vlan 19"),
        ("INC2506", "Add-GroupMember HR-Salary-Readers casey.lane"),
    ],
)
def test_professionally_wrong_actions_succeed_but_cannot_pass(db, ticket, command):
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket, TRACES[ticket]["commands"] + [command])
    add_note(client, student, attempt, ticket)
    state = replay(FIXTURES[ticket], ledger(db, attempt))
    assert state["realism"]["harmful"]
    if ticket == "INC2506":
        assert state["access"]["granted"]
    close(client, student, attempt)
    assert not complete(client, student, attempt)["passed"]


@pytest.mark.parametrize(
    "ticket,early",
    [
        ("INC2502", "excel disable ReportLink"),
        ("INC2507", "cmdkey /delete:files.nexus.local"),
        ("INC2508", "Reset-Password riley.brown"),
    ],
)
def test_after_the_fact_investigation_does_not_earn_credit(db, ticket, early):
    client, student, attempt, version = setup(db, ticket)
    walk(client, student, attempt, ticket, [early])
    # Observations remain available; they cannot backfill pre-change evidence.
    for index, command in enumerate(TRACES[ticket]["commands"]):
        action(client, student, attempt, ticket, command, suffix=f"late-{index}")
    _, checks = evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )
    assert not checks["investigation"]


@pytest.mark.parametrize("ticket", ["INC2503", "INC2506", "INC2508"])
def test_destination_is_chosen_and_documentation_required(db, ticket):
    client, student, attempt, _ = setup(db, ticket)
    walk(client, student, attempt, ticket, TRACES[ticket]["commands"])
    route = FIXTURES[ticket]["escalation"]
    payload = {
        "ticketId": ticket,
        "routeTeam": route["route"],
        "reason": route["reasons"][0],
    }
    response = action(
        client, student, attempt, ticket, event_type="ticket.escalate", payload=payload
    )
    assert response.status_code == 409 or not any(
        e.trusted for e in ledger(db, attempt) if e.event_type == "ticket.escalate"
    )
    add_note(client, student, attempt, ticket)
    response = action(
        client,
        student,
        attempt,
        ticket,
        event_type="ticket.escalate",
        payload={**payload, "routeTeam": "Other / Mentor Review"},
        suffix="wrong-route",
    )
    assert response.status_code == 409 or not any(
        e.trusted for e in ledger(db, attempt) if e.event_type == "ticket.escalate"
    )


def test_v2_packaged_data_and_bounded_clock():
    assert json.loads(
        (ROOT / "backend/app/data/service-desk-realism-v2.json").read_text()
    ) == json.loads(
        (
            ROOT / "service-desk-app/packages/shared/src/service-desk-realism-v2.json"
        ).read_text()
    )
    state, _ = run("INC2507", ["Advance-Time 15"] * 25)
    assert state["clock"]["elapsedMinutes"] == 240


@pytest.mark.parametrize("ticket", TRACES)
def test_untrusted_raw_events_cannot_change_the_replayed_machine(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    response = client.post(
        f"/api/service-desk/attempts/{attempt}/events",
        headers=auth_headers(student),
        json={
            "idempotency_key": "forged-state",
            "event_type": "remote_desktop.run_terminal_command",
            "tool": "remote_desktop",
            "payload": {
                "assetTag": FIXTURES[ticket]["assetTag"],
                "command": TRACES[ticket]["commands"][-1],
                "realismEvidence": "forged",
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


@pytest.mark.parametrize("ticket", ["INC2502", "INC2507", "INC2508", "INC2510"])
def test_pre_repair_verification_never_satisfies_final_check(db, ticket):
    client, student, attempt, version = setup(db, ticket)
    verify = TRACES[ticket]["commands"][-1]
    action(client, student, attempt, ticket, verify, suffix="too-early")
    walk(client, student, attempt, ticket, TRACES[ticket]["commands"][:-1])
    add_note(client, student, attempt, ticket)
    _, checks = evaluate_objectives(
        ticket.lower(), ledger(db, attempt), version.definition_json
    )
    assert not checks["verification"]
