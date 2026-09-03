"""Leak-safe, server-authoritative state for the student ticket workspace."""

from __future__ import annotations

from typing import Any

from app.services.service_desk_escalation import escalation_profile
from app.services.service_desk_objectives import (
    ScenarioObjectiveDefinition,
    _matching_positions,
    evaluate_objectives,
    evidence_objective_label,
)


STAGE_CATEGORIES = (
    ("investigate", "investigation"),
    ("diagnose", "diagnosis"),
    ("fix", "remediation"),
    ("verify", "verification"),
    ("document", "documentation"),
)


def _documentation_target(objective_def: ScenarioObjectiveDefinition | None) -> str:
    if objective_def and objective_def.is_process_profile:
        documentation = next(
            (
                category
                for category in objective_def.categories
                if category.name == "documentation"
            ),
            None,
        )
        if documentation and any(
            rule.event_type == "remote_desktop.add_internal_note"
            for objective in documentation.objectives
            for rule in objective.any_of
        ):
            return "remote_desktop"
    return "ticket"


def process_progress(
    definition_json: dict[str, Any],
    events: list[Any],
    *,
    objective_def: ScenarioObjectiveDefinition | None,
    stable_key: str,
    attempt: Any | None,
) -> dict[str, Any]:
    """Build the in-progress workspace contract without revealing unmet rules."""
    _, objective_checks = evaluate_objectives(stable_key, events, definition_json)

    stage_complete = {"understand": attempt is not None}
    stage_complete.update(
        {
            stage_key: bool(objective_checks.get(category_name, False))
            for stage_key, category_name in STAGE_CATEGORIES
        }
    )
    current_found = False
    stages: list[dict[str, Any]] = []
    for stage_key in ("understand", *(key for key, _ in STAGE_CATEGORIES)):
        complete = stage_complete[stage_key]
        if current_found:
            status = "not_started"
        elif complete:
            status = "complete"
        else:
            status = "current"
            current_found = True
        stage: dict[str, Any] = {
            "key": stage_key,
            "status": status,
            "needs_more_evidence": not complete,
        }
        if stage_key == "fix":
            # Deliberately neutral before the outcome is chosen: the student may
            # see that escalation is *available* (below) but is never told it is
            # the correct answer. The debrief reveals appropriateness.
            stage["mode"] = "fix"
        stages.append(stage)

    # Only successful trusted matches become visible. In particular, no entry
    # is emitted for an unmet objective—not even an id or placeholder label.
    evidence = []
    if objective_def and objective_def.is_process_profile:
        for category in objective_def.categories:
            for objective in category.objectives:
                if _matching_positions(events, objective):
                    evidence.append(
                        {
                            "id": objective.id,
                            "label": evidence_objective_label(objective.id),
                        }
                    )

    blockers = []
    if not objective_checks.get("diagnosis", False):
        blockers.append("need_diagnosis_evidence")
    if not objective_checks.get("remediation", False):
        blockers.append("complete_fix")
    if not objective_checks.get("verification", False):
        blockers.append("verify_first")
    if not objective_checks.get("documentation", False):
        blockers.append("add_note")

    profile = escalation_profile(stable_key)
    escalation = (
        {"available": True, "route": profile.route}
        if profile is not None and profile.expected
        else None
    )

    return {
        "stages": stages,
        "evidence": evidence,
        "documentation_target": _documentation_target(objective_def),
        "resolve_blockers": blockers,
        "escalation": escalation,
    }
