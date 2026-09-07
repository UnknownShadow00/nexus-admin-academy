"""Server-side grading for the deterministic Service Desk simulation."""

from __future__ import annotations

from math import floor
from typing import Any

from sqlalchemy.orm import Session

from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.services.service_desk_escalation import escalation_profile
from app.services.service_desk_objectives import (
    PROCESS_WEIGHTS,
    evaluate_objectives,
    objective_definition,
    payload_matches,
)


POINTS_BY_PRIORITY = {"critical": 160, "high": 120, "medium": 80, "low": 50}
UNRESOLVED_CLOSE_PENALTY_RATE = 0.25
HINT_PENALTY_POINTS = 5
FREE_HINT_COUNT = 1
WRONG_ACCOUNT_ACTION_PENALTY_POINTS = 10
RUBRIC_VERSION = "server-process-v3"

ACCOUNT_REMEDIATION_EVENT_TYPES = {
    "directory.reset_mfa",
    "directory.reset_password",
    "directory.unlock_account",
}


class AttemptNotClosedError(Exception):
    """Raised when a grade is requested before a close event is recorded."""


def _js_round(value: float) -> int:
    """Match JavaScript Math.round for the non-negative grading values."""
    return floor(value + 0.5)


def compute_grade(db: Session, attempt: ServiceDeskAttempt) -> dict[str, Any]:
    """Recompute an attempt grade exclusively from its published definition and events."""
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(id=attempt.scenario_version_id)
        .one()
    )
    scenario = db.query(ServiceDeskScenario).filter_by(id=version.scenario_id).one()
    definition = version.definition_json or {}
    priority = definition.get("priority")
    points_possible = POINTS_BY_PRIORITY.get(priority, 0)
    events = (
        db.query(ServiceDeskAttemptEvent)
        .filter_by(attempt_id=attempt.id)
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )

    close_events = [event for event in events if event.event_type == "ticket.close"]
    escalate_events = [
        event
        for event in events
        if event.event_type == "ticket.escalate"
        and event.trusted is True
        and event.success is True
    ]
    # A trusted escalation terminates the attempt exactly like a close does.
    if not close_events and not escalate_events:
        raise AttemptNotClosedError("Attempt has not been closed yet")
    # ticket.close is only a request to grade.  Its success flag and payload
    # are browser assertions and are never resolution evidence.
    was_closed = True
    resolved, objective_checks = evaluate_objectives(
        scenario.stable_key, events, definition
    )
    objective_definition_for_version = objective_definition(
        scenario.stable_key, definition
    )

    # First-class escalation grading.  Only scenarios with an
    # ``EscalationProfile.expected`` profile enter this branch; every ordinary
    # scenario's grading below is untouched.
    profile = escalation_profile(scenario.stable_key)
    if definition.get("objective_catalog_version") == "realism-v2":
        profile = None  # Historical converted profiles must not grade new versions.
    escalation_details: dict[str, Any] = {}
    escalation_process_points: int | None = None
    critical_failure = False
    _any_trusted_escalate = bool(escalate_events)
    if profile is not None and profile.expected:
        escalate_event = escalate_events[-1] if escalate_events else None
        escalate_payload = (escalate_event.payload_json or {}) if escalate_event else {}
        reason_ok = escalate_payload.get("reason") in profile.accepted_reasons
        route_ok = escalate_payload.get("routeTeam") == profile.route

        def _trusted_match(rule: Any) -> bool:
            return any(
                event.trusted is True
                and event.success is True
                and event.event_type == rule.event_type
                and payload_matches(event.payload_json or {}, rule.payload)
                for event in events
            )

        prohibited_hit = any(_trusted_match(rule) for rule in profile.prohibited)
        containment_met = all(
            _trusted_match(rule) for rule in profile.required_containment
        )
        escalation_valid = _any_trusted_escalate and reason_ok and route_ok
        escalation_correct = escalation_valid and containment_met and not prohibited_hit
        # Investigate -> Diagnose -> Fix/Escalate -> Verify -> Document. A
        # correctly routed hand-off is still not a passing ticket until the
        # closure/hand-off note is on the trusted ledger, exactly like an
        # ordinary resolved ticket. ``escalation_correct`` stays true so the
        # debrief can say "right call, documentation still required".
        documentation_complete = bool(objective_checks.get("documentation", False))

        resolved = escalation_correct and documentation_complete
        critical_failure = prohibited_hit

        # Normalize process credit across the categories that actually apply to
        # this escalation outcome.  Verification is N/A unless the profile
        # requires verifiable containment; it is never shown as earned work.
        earned = 0
        applicable_total = 0
        for category in ("investigation", "diagnosis", "documentation"):
            applicable_total += PROCESS_WEIGHTS[category]
            if objective_checks.get(category, False):
                earned += PROCESS_WEIGHTS[category]
        # The remediation weight becomes the "escalation/remediation" slot and
        # is awarded for a correct hand-off.
        applicable_total += PROCESS_WEIGHTS["remediation"]
        if escalation_correct:
            earned += PROCESS_WEIGHTS["remediation"]
        if profile.verification_applicable:
            applicable_total += PROCESS_WEIGHTS["verification"]
            if containment_met:
                earned += PROCESS_WEIGHTS["verification"]
        escalation_process_points = (
            _js_round(earned * 100 / applicable_total) if applicable_total else 0
        )

        escalation_details = {
            "escalated": _any_trusted_escalate,
            "escalation_expected": True,
            "escalation_route": escalate_payload.get("routeTeam"),
            "escalation_reason": escalate_payload.get("reason"),
            "escalation_valid": escalation_valid,
            "escalation_correct": escalation_correct,
            "documentation_complete": documentation_complete,
            "containment_required": profile.verification_applicable,
            "containment_met": (
                containment_met if profile.verification_applicable else None
            ),
            "prohibited_hit": prohibited_hit,
            "verification_applicable": profile.verification_applicable,
        }
    elif profile is None and any(
        event.event_type == "ticket.escalate" for event in events
    ):
        # Ordinary scenario: ``ticket.escalate`` is never trusted here, so
        # grading is byte-identical to not escalating.  Record only that the
        # student tried it, for advisory feedback - the score path is untouched.
        escalation_details = {
            "escalated": False,
            "escalation_expected": False,
            "escalation_attempted": True,
        }
    if definition.get("objective_catalog_version") in {"realism-v1", "realism-v2"}:
        from app.services.service_desk_realism import replay

        simulated = replay(definition["simulation_fixture"], events)
        critical_failure = simulated["realism"]["harmful"]
        resolved = resolved and not critical_failure
        if critical_failure:
            objective_checks["remediation"] = False
        route = definition["simulation_fixture"].get("escalation")
        if route:
            handed_off = bool(escalate_events)
            resolved = resolved and handed_off
            objective_checks["remediation"] = handed_off and not critical_failure
            applicable = {
                key: weight for key, weight in PROCESS_WEIGHTS.items()
                if key != "verification" or route["verificationApplicable"]
            }
            escalation_process_points = _js_round(
                sum(weight for key, weight in applicable.items() if objective_checks.get(key, False))
                * 100 / sum(applicable.values())
            )
            escalation_details = {
                "escalated": handed_off,
                "escalation_expected": True,
                "escalation_correct": handed_off and not critical_failure,
                "verification_applicable": route["verificationApplicable"],
                "containment_met": objective_checks.get("verification") if route["verificationApplicable"] else None,
                "documentation_complete": objective_checks.get("documentation", False),
            }
        if scenario.stable_key == "inc2509":
            handed_off = bool(escalate_events)
            resolved = resolved and handed_off
            escalation_details = {
                "escalated": handed_off,
                "escalation_expected": True,
                "escalation_correct": handed_off,
                "verification_applicable": True,
                "documentation_complete": objective_checks.get("documentation", False),
            }
    # Legacy process-v3 permits partial process credit after a technical fix.
    # Curriculum competency additionally requires evidence-led investigation
    # and diagnosis, in the order evaluated from the trusted ledger.
    v2_competency = any(
        event.event_type == "v2.curriculum_launch" and event.trusted is True
        for event in events
    )
    if v2_competency:
        resolved = resolved and all(
            objective_checks.get(category, False)
            for category in ("investigation", "diagnosis")
        )

    hints_used = sum(event.event_type == "hint_requested" for event in events)
    # Learning Mode is for practicing without penalty: hint use and an
    # unresolved close still get recorded and shown to the student, but do
    # not reduce the score. Simulation Mode is unaffected.
    is_learning_mode = attempt.mode == "learning"

    process_points = (
        escalation_process_points
        if escalation_process_points is not None
        else sum(
            weight
            for category, weight in PROCESS_WEIGHTS.items()
            if objective_checks.get(category, False)
        )
        if objective_definition_for_version
        and objective_definition_for_version.is_process_profile
        else 100
        if resolved
        else 0
    )
    unresolved_penalty = (
        _js_round(points_possible * UNRESOLVED_CLOSE_PENALTY_RATE)
        if was_closed and not resolved and not is_learning_mode
        else 0
    )
    hint_penalty = (
        0
        if is_learning_mode
        else max(0, hints_used - FREE_HINT_COUNT) * HINT_PENALTY_POINTS
    )
    remediation_rules = (
        tuple(
            rule
            for category in objective_definition_for_version.categories
            if category.name == "remediation"
            for objective in category.objectives
            for rule in objective.any_of
        )
        if objective_definition_for_version
        else ()
    )
    wrong_account_actions = (
        sum(
            event.success is True
            and event.event_type in ACCOUNT_REMEDIATION_EVENT_TYPES
            and not any(
                event.event_type == rule.event_type
                and payload_matches(event.payload_json or {}, rule.payload)
                for rule in remediation_rules
            )
            for event in events
        )
        if remediation_rules
        else 0
    )
    wrong_action_penalty = (
        0
        if is_learning_mode
        else wrong_account_actions * WRONG_ACCOUNT_ACTION_PENALTY_POINTS
    )
    penalty_points = unresolved_penalty + hint_penalty + wrong_action_penalty
    objective_points = _js_round(points_possible * process_points / 100)
    points_before_penalty = objective_points if was_closed else 0
    points_awarded = max(0, points_before_penalty - penalty_points)
    overall_score = (
        _js_round((points_awarded / points_possible) * 100) if points_possible else 0
    )

    if critical_failure:
        feedback_summary = (
            "You applied a change that was not yours to make. This ticket "
            "required escalation to the responsible team."
        )
        if definition.get("objective_catalog_version") in {"realism-v1", "realism-v2"}:
            feedback_summary = "Access was expanded beyond the recorded approval. A technically successful access test does not satisfy least privilege."
        if definition.get("objective_catalog_version") == "realism-v2":
            feedback_summary = "The attempt includes an unsafe action or an uncontained exposure. Technical success alone does not satisfy the professional outcome."
    elif profile is not None and profile.expected:
        if resolved:
            route = escalation_details.get("escalation_route") or profile.route
            feedback_summary = f"You correctly escalated this to {route}."
            if penalty_points > 0:
                feedback_summary += (
                    f" The final score includes {penalty_points} hint or "
                    "closure penalty points."
                )
        elif escalation_details.get(
            "escalation_correct"
        ) and not escalation_details.get("documentation_complete"):
            feedback_summary = (
                "You made the right call and routed this correctly, but the "
                "ticket cannot pass until you record a closure/hand-off note "
                "documenting what you found and where it went."
            )
        elif escalation_details.get("escalated") and profile.verification_applicable:
            feedback_summary = (
                "You escalated this, but the required containment step was not "
                "completed first."
            )
        elif escalation_details.get("escalated"):
            feedback_summary = (
                "Escalation is the right call here, but the destination team or "
                "reason did not match what this ticket needs."
            )
        else:
            feedback_summary = (
                f"This ticket needed to be escalated to {profile.route}. "
                "Closing it yourself is outside a help-desk technician's "
                "authority."
            )
    elif (
        profile is None
        and escalation_details.get("escalation_attempted")
        and not resolved
    ):
        feedback_summary = (
            "This ticket was within your authority - it did not need "
            "escalation. Review what a full fix looks like."
        )
    elif resolved and escalation_details.get("escalation_expected"):
        feedback_summary = "You completed the required professional hand-off. The receiving team owns restoration."
    elif is_learning_mode:
        feedback_summary = (
            "Learning Mode: hints and retries do not affect your score. "
            + (
                "The repair, verification, and closure checks passed; complete the evidence steps for full process credit."
                if resolved
                else "Review the ticket and try again to fully resolve it."
            )
        )
    elif resolved:
        feedback_summary = (
            f"The original symptom was repaired and verified. The final score includes {penalty_points} hint or closure penalty points."
            if penalty_points > 0
            else "The original symptom was repaired and verified. Evidence-led investigation and diagnosis determine full process credit."
        )
    else:
        feedback_summary = "Your ticket could not be verified yet. Review the required troubleshooting steps and try again."

    # A single, unambiguous learner-facing outcome, distinct from the ticket's
    # operational status. "awaiting_review" is layered on by the caller when a
    # mentor/AI grade is still pending; grading alone only ever produces a
    # decisive pass / escalation / retry result.
    if not resolved:
        learner_outcome = "needs_another_attempt"
    elif escalation_details.get("escalation_expected"):
        learner_outcome = "escalated_successfully"
    else:
        learner_outcome = "pass"

    return {
        "technical_complete": resolved,
        "critical_failure": critical_failure,
        "overall_score": overall_score,
        "passed": resolved,
        "learner_outcome": learner_outcome,
        "feedback_summary": feedback_summary,
        "details": {
            "learner_outcome": learner_outcome,
            "points_possible": points_possible,
            "points_awarded": points_awarded,
            "process_points": process_points,
            "process_weights": PROCESS_WEIGHTS
            if objective_definition_for_version
            and objective_definition_for_version.is_process_profile
            else None,
            "penalty_points": penalty_points,
            "hints_used": hints_used,
            "wrong_account_actions": wrong_account_actions,
            "wrong_action_penalty": wrong_action_penalty,
            "resolved": resolved,
            "was_closed": was_closed,
            "objective_checks": objective_checks,
            "is_learning_mode": is_learning_mode,
            **escalation_details,
        },
        "rubric_version": RUBRIC_VERSION,
    }
