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
from app.services.service_desk_objectives import evaluate_objectives


POINTS_BY_PRIORITY = {"critical": 160, "high": 120, "medium": 80, "low": 50}
UNRESOLVED_CLOSE_PENALTY_RATE = 0.25
HINT_PENALTY_POINTS = 5
FREE_HINT_COUNT = 1
RUBRIC_VERSION = "server-objectives-v2"

class AttemptNotClosedError(Exception):
    """Raised when a grade is requested before a close event is recorded."""


def _js_round(value: float) -> int:
    """Match JavaScript Math.round for the non-negative grading values."""
    return floor(value + 0.5)


def compute_grade(db: Session, attempt: ServiceDeskAttempt) -> dict[str, Any]:
    """Recompute an attempt grade exclusively from its published definition and events."""
    version = db.query(ServiceDeskScenarioVersion).filter_by(id=attempt.scenario_version_id).one()
    scenario = db.query(ServiceDeskScenario).filter_by(id=version.scenario_id).one()
    definition = version.definition_json or {}
    priority = definition.get("priority")
    points_possible = POINTS_BY_PRIORITY.get(priority, 0)
    events = db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt.id).order_by(
        ServiceDeskAttemptEvent.sequence_number
    ).all()

    close_events = [event for event in events if event.event_type == "ticket.close"]
    if not close_events:
        raise AttemptNotClosedError("Attempt has not been closed yet")
    # ticket.close is only a request to grade.  Its success flag and payload
    # are browser assertions and are never resolution evidence.
    was_closed = True
    resolved, objective_checks = evaluate_objectives(scenario.stable_key, events, definition)
    hints_used = sum(event.event_type == "hint_requested" for event in events)
    # Learning Mode is for practicing without penalty: hint use and an
    # unresolved close still get recorded and shown to the student, but do
    # not reduce the score. Simulation Mode is unaffected.
    is_learning_mode = attempt.mode == "learning"

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
    penalty_points = unresolved_penalty + hint_penalty
    objective_points = points_possible if resolved else 0
    points_before_penalty = objective_points if resolved or was_closed else 0
    points_awarded = max(0, points_before_penalty - penalty_points)
    overall_score = _js_round((points_awarded / points_possible) * 100) if points_possible else 0

    if is_learning_mode:
        feedback_summary = (
            "Learning Mode: hints and retries do not affect your score. "
            + (
                "All required diagnosis, repair, verification, note, and closure checks passed."
                if resolved
                else "Review the ticket and try again to fully resolve it."
            )
        )
    elif resolved:
        feedback_summary = (
            f"All required workflow checks passed. The final score includes {penalty_points} hint or closure penalty points."
            if penalty_points > 0
            else "All required diagnosis, repair, verification, note, and closure checks passed."
        )
    else:
        feedback_summary = "Your ticket could not be verified yet. Review the required troubleshooting steps and try again."

    return {
        "technical_complete": resolved,
        "critical_failure": False,
        "overall_score": overall_score,
        "passed": resolved,
        "feedback_summary": feedback_summary,
        "details": {
            "points_possible": points_possible,
            "points_awarded": points_awarded,
            "penalty_points": penalty_points,
            "hints_used": hints_used,
            "resolved": resolved,
            "was_closed": was_closed,
            "objective_checks": objective_checks,
            "is_learning_mode": is_learning_mode,
        },
        "rubric_version": RUBRIC_VERSION,
    }
