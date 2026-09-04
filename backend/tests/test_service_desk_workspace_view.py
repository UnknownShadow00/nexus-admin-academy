import json
from types import SimpleNamespace

from app.services.service_desk_objectives import (
    PROCESS_CATALOG_VERSION,
    SCENARIO_OBJECTIVES,
)
from app.services.service_desk_workspace_view import build_debrief, process_progress


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
    # Escalation is offered on every ticket, route-free, with no verdict.
    assert view["escalation"] == {"available": True}
    assert "route" not in view["escalation"]
    assert "resolve_blockers" not in view


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


def test_escalation_scenario_pre_decision_view_leaks_no_route_or_verdict():
    definition = SCENARIO_OBJECTIVES["inc2506"]
    view = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        objective_def=definition,
        stable_key="inc2506",
        attempt=SimpleNamespace(status="in_progress"),
    )
    assert view["escalation"] == {"available": True}
    serialized = json.dumps(view)
    for leak in ("Identity & Access", "expected", "route", "rationale"):
        assert leak not in serialized
    # The workflow rail must not pre-announce that escalation is the answer.
    fix_stage = next(stage for stage in view["stages"] if stage["key"] == "fix")
    assert fix_stage["mode"] == "fix"


def test_ordinary_and_escalation_scenarios_have_identical_escalation_affordance():
    """Fix 2: the pre-decision shape must not reveal which tickets escalate."""
    shapes = set()
    for key in ("inc2401", "inc2506", "inc2508"):
        view = process_progress(
            {"objective_catalog_version": PROCESS_CATALOG_VERSION},
            [],
            objective_def=SCENARIO_OBJECTIVES[key],
            stable_key=key,
            attempt=SimpleNamespace(status="in_progress"),
        )
        assert view["escalation"] == {"available": True}
        shapes.add(json.dumps(view["escalation"], sort_keys=True))
    assert len(shapes) == 1


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
    assert assignment_view["escalation"] == {"available": True}
    assert "resolve_blockers" not in assignment_view


def _grade(details, *, passed, score):
    return SimpleNamespace(details_json=details, passed=passed, overall_score=score)


def test_in_progress_view_never_carries_the_ordered_path():
    definition = SCENARIO_OBJECTIVES["inc2401"]
    live = process_progress(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        objective_def=definition,
        stable_key="inc2401",
        attempt=SimpleNamespace(status="in_progress"),
    )
    assert "stronger_path" not in json.dumps(live)


def _failed_debrief(stable_key, *, attempts_remaining, checks=None):
    definition = SCENARIO_OBJECTIVES[stable_key]
    return build_debrief(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        _grade(
            {
                "objective_checks": checks or {"investigation": True},
                "escalated": False,
            },
            passed=False,
            score=20,
        ),
        stable_key=stable_key,
        objective_def=definition,
        attempts_remaining=attempts_remaining,
    )


def test_failed_debrief_with_retries_is_limited_and_leak_free():
    """Fix 4: a graded retry must not become a transcription exercise."""
    debrief = _failed_debrief("inc2506", attempts_remaining=2)
    assert debrief["coaching_tier"] == "limited"
    assert debrief["stronger_path"] == []
    assert debrief["escalation_feedback"] is None
    assert debrief["result"]["outcome"] == "needs_another_try"
    serialized = json.dumps(debrief)
    for leak in ("Identity & Access", "Escalate to", "add_internal_note"):
        assert leak not in serialized
    # Broad category status is still allowed - it is "which areas were weak".
    investigation = next(
        c for c in debrief["categories"] if c["key"] == "investigation"
    )
    assert investigation["status"] == "full"


def test_failed_debrief_on_final_attempt_reveals_full_coaching():
    for remaining in (0, None):
        debrief = _failed_debrief("inc2401", attempts_remaining=remaining)
        assert debrief["coaching_tier"] == "full"
        assert debrief["stronger_path"]
        assert debrief["escalation_feedback"] is not None
        assert debrief["result"]["outcome"] == "needs_another_try"


def test_debrief_marks_escalation_verification_not_applicable():
    definition = SCENARIO_OBJECTIVES["inc2506"]
    debrief = build_debrief(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        _grade(
            {
                "objective_checks": {
                    "investigation": True,
                    "diagnosis": True,
                    "documentation": True,
                },
                "escalated": True,
                "escalation_correct": True,
                "verification_applicable": False,
                "escalation_expected": True,
            },
            passed=True,
            score=100,
        ),
        stable_key="inc2506",
        objective_def=definition,
        attempts_remaining=2,
    )
    verification = next(
        c for c in debrief["categories"] if c["key"] == "verification"
    )
    assert verification["status"] == "not_applicable"
    assert verification["points"] == 0
    escalation_slot = next(
        c for c in debrief["categories"] if c["key"] == "remediation"
    )
    assert escalation_slot["status"] == "full"
    assert debrief["result"]["outcome"] == "escalated"
    assert debrief["escalation_feedback"]["appropriate"] is True
    assert "Escalate to Identity & Access with your findings" in debrief[
        "stronger_path"
    ]


def test_debrief_escalation_feedback_for_ordinary_scenario():
    definition = SCENARIO_OBJECTIVES["inc2507"]
    debrief = build_debrief(
        {"objective_catalog_version": PROCESS_CATALOG_VERSION},
        [],
        _grade({"objective_checks": {}}, passed=False, score=0),
        stable_key="inc2507",
        objective_def=definition,
        attempts_remaining=None,
    )
    assert debrief["escalation_feedback"]["appropriate"] is False
