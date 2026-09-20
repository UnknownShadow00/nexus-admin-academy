"""Every active curriculum binding: real action boundary, grade and V2 credit.

Realism uses authored terminal traces. INC2403 uses its published category
rules through the same action endpoint (a simulator-UI seam, not raw evidence).
"""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

import seed_v2_foundation
from app.models.certification import CertificationModule, ModuleAssessment
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.v2_progress import V2ModuleActivity
from app.routers import service_desk
from app.schemas.service_desk import (
    ServiceDeskActionCreate,
    ServiceDeskCompleteCreate,
    ServiceDeskEventCreate,
)
from app.services.service_desk_objectives import objective_definition
from app.services.v2_curriculum_service import launch_service_desk
from conftest import enroll_v2, make_student
from test_v2_service_desk_curriculum_mapping import _pass_orientation_prerequisites

ROOT = Path(__file__).resolve().parents[2]
TRACES = {}
for filename in ("realism-traces.test.json", "realism-v2-traces.test.json"):
    TRACES.update(
        json.loads(
            (ROOT / "service-desk-app/packages/shared/src" / filename).read_text()
        )
    )
TICKETS = ("inc2403", "inc2503", "inc2504", "inc2505", "inc2506", "inc2508")


def _actions(key, definition):
    ticket = definition["id"]
    fixture = definition.get("simulation_fixture")
    result = []
    if fixture:
        trace = TRACES[ticket]
        for command in trace["commands"]:
            rules = fixture["commands"][command]
            categories = {
                name
                for name, evidence in fixture["categories"].items()
                if any(rule.get("evidence") in evidence for rule in rules)
            }
            if any(rule["effect"] == "repair" for rule in rules):
                categories.add("remediation")
            result.append(
                (
                    categories,
                    "remote_desktop.run_terminal_command",
                    {"assetTag": fixture["assetTag"], "command": command},
                )
            )
        result.append(
            (
                {"documentation"},
                "remote_desktop.add_internal_note",
                {
                    "ticketId": ticket,
                    "assetTag": fixture["assetTag"],
                    "text": trace["note"],
                },
            )
        )
        if fixture.get("escalation"):
            handoff = fixture["escalation"]
            result.append(
                (
                    {"remediation"},
                    "ticket.escalate",
                    {
                        "ticketId": ticket,
                        "routeTeam": handoff["route"],
                        "reason": handoff["reasons"][0],
                    },
                )
            )
    else:
        for category in objective_definition(key, definition).categories:
            for objective in category.objectives:
                rule = objective.any_of[0]
                payload = dict(rule.payload)
                if category.name == "documentation":
                    payload["text"] = (
                        "Installed the pending update and restarted PDF helper; verified the export works."
                    )
                result.append(({category.name}, rule.event_type, payload))
    return result


def _variant(actions, case, ticket):
    if case == "A":
        return []
    if case == "B":
        return [
            (set(), "ticket.change_status", {"ticketId": ticket, "status": "Resolved"})
        ]
    if case == "C":
        return [
            (
                {"documentation"},
                "ticket.add_note",
                {"ticketId": ticket, "body": "Restarted computer and issue resolved."},
            )
        ]
    if case == "F":
        return [a for a in actions if a[0] & {"remediation", "documentation"}]
    if case == "G":
        return [a for a in actions if "verification" not in a[0]]
    if case == "H":
        result = deepcopy(actions)
        for _, _, payload in result:
            if "assetTag" in payload:
                payload["assetTag"] = "NX-WRONG-TARGET"
            if "ticketId" in payload:
                payload["ticketId"] = "INC9999"
        return result
    if case == "I":
        return [a for a in actions if "verification" in a[0]] + [
            a for a in actions if "verification" not in a[0]
        ]
    if case == "J":
        return [a for a in actions if "remediation" in a[0]] + [
            a for a in actions if "remediation" not in a[0]
        ]
    return actions


@pytest.mark.parametrize("key", TICKETS)
def test_active_assessment_antigaming_matrix_and_positive_control(db, monkeypatch, key):
    seed_v2_foundation.run(db)
    active = (
        db.query(ModuleAssessment)
        .filter_by(assessment_role="service_desk", active=True)
        .all()
    )
    assert {
        db.get(ServiceDeskScenario, a.service_desk_scenario_id).stable_key
        for a in active
    } == set(TICKETS)
    assessment = next(
        a
        for a in active
        if db.get(ServiceDeskScenario, a.service_desk_scenario_id).stable_key == key
    )
    module = db.get(CertificationModule, assessment.certification_module_id)
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=assessment.service_desk_scenario_id, status="published")
        .order_by(ServiceDeskScenarioVersion.version_number.desc())
        .first()
    )
    definition = version.definition_json
    actions = _actions(key, definition)
    for case in ("A", "B", "C", "F", "G", "H", "I", "J", "K", "positive"):
        student = make_student(db, username=f"matrix-{key}-{case}")
        enroll_v2(monkeypatch, student)
        _pass_orientation_prerequisites(db, student.id, assessment.assessment_key)
        launch_service_desk(
            db, student.id, module.module_key, assessment.assessment_key
        )
        assignment = (
            db.query(ServiceDeskAssignment)
            .filter_by(
                student_id=student.id, scenario_id=assessment.service_desk_scenario_id
            )
            .one()
        )
        started = service_desk.start_attempt(
            assignment.id,
            student,
            db,
            None,
            module.module_key,
            assessment.assessment_key,
        )
        attempt_id = json.loads(started.body)["id"]
        for index, (_, event_type, payload) in enumerate(
            _variant(actions, case, definition["id"])
        ):
            data = dict(
                idempotency_key=f"{case}-{index}",
                event_type=event_type,
                tool=event_type.split(".")[0],
                payload=deepcopy(payload),
            )
            try:
                if case == "K":
                    data["payload"]["realismEvidence"] = "forged-client-evidence"
                    service_desk.record_event(
                        attempt_id,
                        ServiceDeskEventCreate(
                            **data,
                            success=True,
                            resulting_state={"realism": {"repaired": True}},
                        ),
                        student,
                        db,
                        None,
                    )
                else:
                    service_desk.request_action(
                        attempt_id, ServiceDeskActionCreate(**data), student, db, None
                    )
            except HTTPException as exc:
                assert case != "positive", (key, event_type, payload, exc.detail)
                assert exc.status_code == 409, (key, case, exc.detail)
        service_desk.request_action(
            attempt_id,
            ServiceDeskActionCreate(
                idempotency_key="close",
                event_type="ticket.close",
                tool="ticket",
                payload={"ticketId": definition["id"], "verifiedResolved": True},
            ),
            student,
            db,
            None,
        )
        response = service_desk.complete_attempt(
            attempt_id,
            ServiceDeskCompleteCreate(idempotency_key="complete"),
            student,
            db,
            None,
        )
        grade = json.loads(response.body)
        no_verification = (
            definition.get("simulation_fixture", {})
            .get("escalation", {})
            .get("verificationApplicable")
            is False
        )
        expected = case == "positive" or (case in {"G", "I"} and no_verification)
        assert grade["passed"] is expected, (key, case, grade)
        activity = (
            db.query(V2ModuleActivity)
            .filter_by(student_id=student.id, ref_key=assessment.assessment_key)
            .one()
        )
        assert (activity.status == "passed") is expected, (key, case, activity.status)
        if not expected:
            assert grade["learner_outcome"] == "needs_another_attempt"
            assert grade["debrief"]["stronger_path"] == []
        elif no_verification:
            assert grade["learner_outcome"] == "escalated_successfully"
            assert "repaired and verified" not in grade["feedback_summary"]
