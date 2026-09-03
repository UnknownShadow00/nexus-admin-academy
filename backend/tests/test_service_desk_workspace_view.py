import json
from types import SimpleNamespace

from app.services.service_desk_objectives import (
    PROCESS_CATALOG_VERSION,
    SCENARIO_OBJECTIVES,
)
from app.services.service_desk_workspace_view import process_progress


def _event(event_type, payload, *, trusted=True, success=True):
    return SimpleNamespace(
        event_type=event_type,
        payload_json=payload,
        trusted=trusted,
        success=success,
    )


def test_partial_in_progress_view_exposes_only_met_evidence():
    definition = SCENARIO_OBJECTIVES["inc2401"]
    matched_rule = definition.categories[0].objectives[0].any_of[0]
    view = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [_event(matched_rule.event_type, matched_rule.payload)],
        objective_def=definition,
        stable_key="inc2401",
        attempt=SimpleNamespace(status="in_progress"),
    )

    assert view["evidence"] == [
        {"id": "profile-evidence-reviewed", "label": "Profile evidence reviewed"}
    ]
    serialized = json.dumps(view)
    for hidden in (
        "sign-in-loop-reproduced",
        "Sign-in loop reproduced",
        "profile-storage-cleared",
        "Profile storage cleared",
        "finance-portal-restored",
        "stronger_path",
    ):
        assert hidden not in serialized
    assert view["stages"][0]["status"] == "complete"
    assert view["stages"][1]["status"] == "complete"
    assert view["stages"][2]["status"] == "current"
    assert view["stages"][3]["mode"] == "fix"
    assert view["documentation_target"] == "remote_desktop"
    assert view["escalation"] is None


def test_untrusted_and_failed_events_do_not_appear_as_evidence():
    definition = SCENARIO_OBJECTIVES["inc2402"]
    rule = definition.categories[0].objectives[0].any_of[0]
    view = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [
            _event(rule.event_type, rule.payload, trusted=False),
            _event(rule.event_type, rule.payload, success=False),
        ],
        objective_def=definition,
        stable_key="inc2402",
        attempt=SimpleNamespace(status="in_progress"),
    )
    assert view["evidence"] == []
    assert view["stages"][1]["needs_more_evidence"] is True


def test_escalation_scenarios_expose_route_but_not_a_verdict():
    definition = SCENARIO_OBJECTIVES["inc2506"]
    view = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        objective_def=definition,
        stable_key="inc2506",
        attempt=SimpleNamespace(status="in_progress"),
    )
    assert view["escalation"] == {"available": True, "route": "Identity & Access"}
    # The workflow rail must not pre-announce that escalation is the answer.
    fix_stage = next(stage for stage in view["stages"] if stage["key"] == "fix")
    assert fix_stage["mode"] == "fix"


def test_non_escalation_scenarios_have_no_escalation_block():
    definition = SCENARIO_OBJECTIVES["inc2401"]
    view = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        objective_def=definition,
        stable_key="inc2401",
        attempt=SimpleNamespace(status="in_progress"),
    )
    assert view["escalation"] is None


def test_pre_attempt_assignment_view_has_minimal_rail_contract():
    definition = SCENARIO_OBJECTIVES["inc2401"]
    assignment_view = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        objective_def=definition,
        stable_key="inc2401",
        attempt=None,
    )
    assert len(assignment_view["stages"]) == 6
    assert assignment_view["stages"][0]["status"] == "current"
    assert assignment_view["documentation_target"] == "remote_desktop"
    assert assignment_view["escalation"] is None
