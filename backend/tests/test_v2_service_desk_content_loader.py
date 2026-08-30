"""Curriculum-owned scenarios use the existing versioned Service Desk engine."""

from __future__ import annotations

from types import SimpleNamespace

import yaml

from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services.curriculum_intake import _normalize_inline_service_desk
from app.services.service_desk_objectives import evaluate_objectives
from app.services.v2_content_loader import load_service_desk_scenarios


def _source(title="Approval-bound access"):
    return {
        "title": title,
        "mode": "Learning Mode",
        "objectives": ["4.1", "4.7"],
        "ticket": {
            "requester": "New coordinator",
            "complaint": "The approved shared service is missing.",
            "business_impact": "Orientation can continue while access is pending.",
            "initial_priority": "Low/standard request",
            "twist": "Required approval is not yet recorded.",
        },
        "stages": {
            "Investigation": ["Confirm identity and intended access."],
            "Diagnosis": ["Identify missing authorized access."],
            "Remediation": ["Follow the approval and escalation path."],
            "Verification": ["Verify access only after approval."],
            "Documentation": ["Record the pending or completed outcome."],
        },
        "grading_anchors": [
            {"name": "investigation", "weight": 20},
            {"name": "diagnosis", "weight": 20},
            {"name": "safe_action_or_escalation", "weight": 20},
            {"name": "verification", "weight": 20},
            {"name": "documentation", "weight": 20},
        ],
        "correct_failure_behavior": (
            "If approval is unavailable, escalation/pending with a user update is correct; "
            "unauthorized access is not."
        ),
        "hints": ["Check approval.", "Respect the boundary.", "Document the handoff."],
    }


def _write(path, scenario):
    path.write_text(yaml.safe_dump({"scenarios": [scenario]}, sort_keys=False))


def test_inline_scenario_loader_is_idempotent_and_versions_real_changes(db, tmp_path):
    source = _source()
    key, scenario = _normalize_inline_service_desk(
        source,
        "module.test.approval_workflow",
        {"4.1", "4.7"},
        set(),
    )
    path = tmp_path / "scenario.yaml"
    _write(path, scenario)

    first = load_service_desk_scenarios(db, str(path))
    db.commit()
    second = load_service_desk_scenarios(db, str(path))
    db.commit()
    assert first.by_entity["service_desk_scenario"]["created"] == 1
    assert second.by_entity["service_desk_scenario"]["unchanged"] == 1
    assert db.query(ServiceDeskScenario).filter_by(stable_key=key).count() == 1
    assert db.query(ServiceDeskScenarioVersion).count() == 1

    changed_source = _source("Changed approved title")
    changed_key, changed_scenario = _normalize_inline_service_desk(
        changed_source,
        "module.test.approval_workflow",
        {"4.1", "4.7"},
        set(),
    )
    assert changed_key == key
    _write(path, changed_scenario)
    changed = load_service_desk_scenarios(db, str(path))
    db.commit()
    versions = db.query(ServiceDeskScenarioVersion).order_by(
        ServiceDeskScenarioVersion.version_number
    ).all()
    assert changed.by_entity["service_desk_scenario_version"]["created"] == 1
    assert len(versions) == 2
    assert [version.status for version in versions] == ["disabled", "published"]
    latest = versions[-1].definition_json
    assert latest["curriculum"]["stages"] == changed_source["stages"]
    assert latest["grading_anchors"] == changed_source["grading_anchors"]
    assert latest["successful_professional_outcomes"] == [
        "pending",
        "escalated",
        "handed_off",
    ]
    event = SimpleNamespace(
        event_type="ticket.add_note",
        payload_json={"ticketId": key.upper()},
        success=True,
        trusted=True,
    )
    complete, checks = evaluate_objectives(key, [event], latest)
    assert complete is True
    assert checks["server_verifiable"] is True
