"""Leak-safe, server-authoritative state for the student ticket workspace."""

from __future__ import annotations

from typing import Any

from app.services.service_desk_escalation import escalation_profile
from app.services.service_desk_objectives import (
    PROCESS_WEIGHTS,
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
            # MUST stay the literal string "fix" for every scenario, including
            # escalation scenarios. The student workspace must NEVER receive an
            # "expected escalation outcome" signal before completion. Do NOT wire
            # this to escalation_profile / profile.expected - doing so leaks the
            # answer. The post-completion debrief (build_debrief) is the only
            # place escalation appropriateness may be revealed. The frontend no
            # longer consumes this value (see WorkflowRail.tsx); it is retained
            # only so the stage shape is stable.
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

    return {
        "stages": stages,
        "evidence": evidence,
        "documentation_target": _documentation_target(objective_def),
        # Escalation is a professional option on EVERY ticket. This in-progress
        # contract deliberately carries no route, no rationale, and no
        # "expected" flag: exposing any of those before the student decides
        # would teach the answer. The presence of the block is identical for
        # ordinary and escalation scenarios. The server still grades whether
        # escalation was appropriate and correctly routed - see
        # service_desk_grading.compute_grade and
        # service_desk._action_allowed's ``ticket.escalate`` branch.
        "escalation": {"available": True},
    }


# --------------------------------------------------------------------------- #
# Post-completion debrief.  This is the ONLY place the full authored path and
# the ordering narrative are allowed to appear - never while in_progress.
# --------------------------------------------------------------------------- #

DEBRIEF_CATEGORY_ORDER = (
    "investigation",
    "diagnosis",
    "remediation",
    "verification",
    "documentation",
)

_NOTE_CAUSE_HINTS = (
    "because",
    "caused by",
    "root cause",
    "due to",
    "the cause",
    "reason was",
)
_NOTE_ACTION_HINTS = (
    "cleared",
    "reset",
    "renewed",
    "reinstalled",
    "escalated",
    "applied",
    "replaced",
    "configured",
    "restarted",
    "removed",
    "updated",
    "handed off",
    "raised with",
)
_NOTE_VERIFY_HINTS = (
    "verified",
    "confirmed",
    "re-tested",
    "retested",
    "tested again",
    "user confirmed",
    "working now",
    "signed in",
)


def _note_dimensions(text: str) -> dict[str, bool]:
    lowered = (text or "").lower()
    return {
        "cause": any(hint in lowered for hint in _NOTE_CAUSE_HINTS),
        "action": any(hint in lowered for hint in _NOTE_ACTION_HINTS),
        "verification": any(hint in lowered for hint in _NOTE_VERIFY_HINTS),
    }


def _last_student_note(events: list[Any]) -> str:
    note = ""
    for event in events:
        if (
            event.event_type in ("ticket.add_note", "remote_desktop.add_internal_note")
            and event.trusted is True
            and event.success is True
        ):
            payload = event.payload_json or {}
            note = payload.get("body") or payload.get("text") or note
    return note


def _first_repair_position(
    events: list[Any], objective_def: ScenarioObjectiveDefinition | None
) -> int | None:
    if not objective_def or not objective_def.is_process_profile:
        return None
    remediation = next(
        (c for c in objective_def.categories if c.name == "remediation"), None
    )
    if remediation is None:
        return None
    positions = [
        position
        for objective in remediation.objectives
        for position in _matching_positions(events, objective)
    ]
    return min(positions, default=None)


def _category_explanation(
    name: str,
    met: bool,
    events: list[Any],
    objective_def: ScenarioObjectiveDefinition,
    first_repair: int | None,
) -> str:
    category = next((c for c in objective_def.categories if c.name == name), None)
    if category is None:
        return ""
    if met:
        return {
            "investigation": "You gathered evidence before changing anything.",
            "diagnosis": "You identified the cause from your evidence.",
            "remediation": "You applied the correct repair.",
            "verification": "You re-checked the original symptom after the repair.",
            "documentation": "You recorded a closure note.",
        }.get(name, "Completed.")
    # Not met: distinguish "never done" from "done in the wrong order".
    has_any = any(
        _matching_positions(events, objective) for objective in category.objectives
    )
    if has_any and name in ("investigation", "diagnosis") and first_repair is not None:
        return (
            "Your evidence for this step was recorded after you changed "
            "something, so it could not count as pre-change work."
        )
    if has_any and name == "verification":
        return (
            "Your verification happened before the final repair, so it did "
            "not confirm the fix."
        )
    return {
        "investigation": "No pre-change investigation evidence was recorded.",
        "diagnosis": "The cause was never isolated from evidence.",
        "remediation": "The correct repair was not applied.",
        "verification": "The original symptom was never re-checked after the repair.",
        "documentation": "No closure note was recorded.",
    }.get(name, "Not completed.")


def _stronger_path(
    objective_def: ScenarioObjectiveDefinition | None, profile: Any
) -> list[str]:
    if not objective_def or not objective_def.is_process_profile:
        return []
    labels: dict[str, str] = {}
    for category in objective_def.categories:
        if category.objectives:
            labels[category.name] = evidence_objective_label(category.objectives[0].id)
    if profile is not None and profile.expected:
        steps = [
            labels.get("investigation", "Reproduce and scope the reported problem"),
            labels.get("diagnosis", "Identify the cause from your evidence"),
        ]
        if profile.required_containment:
            steps.append("Perform the permitted containment step")
        steps.append(f"Escalate to {profile.route} with your findings")
        steps.append(labels.get("documentation", "Write the hand-off note"))
        return steps
    return [labels[name] for name in DEBRIEF_CATEGORY_ORDER if name in labels]


def _limited_category_explanation(met: bool) -> str:
    """Generic, leak-free coaching for the failed-with-retries debrief tier."""
    return (
        "This part of your process met the bar."
        if met
        else "This is one of the areas to strengthen before your next attempt."
    )


def _escalation_feedback(profile: Any, escalated: bool, passed: bool) -> dict[str, Any]:
    if profile is not None and profile.expected:
        return {
            "appropriate": True,
            "text": profile.rationale
            or f"Yes - this ticket needed to go to {profile.route}.",
        }
    return {
        "appropriate": False,
        "text": "No - this was within your access and authority to resolve.",
    }


def build_debrief(
    definition_json: dict[str, Any],
    events: list[Any],
    grade: Any,
    *,
    stable_key: str,
    objective_def: ScenarioObjectiveDefinition | None,
    attempts_remaining: int | None,
    retries_available: bool | None = None,
) -> dict[str, Any]:
    """Post-completion debrief.

    Coaching is tiered so a failed attempt with retries left cannot be turned
    into a transcription exercise:

    * ``full``    - passed, or failed with no graded attempt left.  The authored
                    ordered path, the correct escalation route, and the full
                    per-category narrative are all revealed.
    * ``limited`` - failed with at least one attempt remaining.  The student
                    sees the score, which broad process areas were weak, and
                    feedback on their own note - but never the ordered path, the
                    exact missing evidence/fix, or the correct escalation
                    destination.
    """
    details = grade.details_json or {}
    checks = details.get("objective_checks", {})
    profile = escalation_profile(stable_key)
    realism_handoff = (
        definition_json.get("simulation_fixture", {}).get("escalation")
        if definition_json.get("objective_catalog_version") == "realism-v2"
        else None
    )
    escalated = bool(details.get("escalated"))
    passed = bool(grade.passed)
    limited = not passed and (
        retries_available
        if retries_available is not None
        else attempts_remaining is not None and attempts_remaining > 0
    )
    first_repair = _first_repair_position(events, objective_def)

    outcome = (
        "escalated"
        if escalated and passed
        else "resolved"
        if passed
        else "needs_another_try"
    )

    categories: list[dict[str, Any]] = []
    if objective_def and objective_def.is_process_profile:
        for name in DEBRIEF_CATEGORY_ORDER:
            weight = PROCESS_WEIGHTS[name]
            met = bool(checks.get(name, False))
            label = name.replace("_", " ").title()
            status = "full" if met else "missed"
            points = weight if met else 0
            explanation = (
                _limited_category_explanation(met)
                if limited
                else _category_explanation(
                    name, met, events, objective_def, first_repair
                )
            )

            if not limited and realism_handoff:
                if name == "remediation":
                    label = "Escalation / hand-off"
                    correct = bool(details.get("escalation_correct"))
                    status = "full" if correct else "missed"
                    points = weight if correct else 0
                    explanation = definition_json["simulation_fixture"]["completion"]["whyItWorked"]
                elif name == "verification" and not realism_handoff["verificationApplicable"]:
                    status, points, weight = "not_applicable", 0, 0
                    explanation = "The receiving team owns restoration; no local verification was claimed."
            elif not limited and profile is not None and profile.expected:
                if name == "remediation":
                    label = "Escalation / hand-off"
                    correct = bool(details.get("escalation_correct"))
                    status = "full" if correct else "missed"
                    points = weight if correct else 0
                    explanation = (
                        profile.rationale
                        if correct
                        else (
                            profile.no_escalation_rationale
                            or f"This ticket needed to be handed to {profile.route}."
                        )
                    )
                elif name == "verification" and not details.get(
                    "verification_applicable"
                ):
                    status = "not_applicable"
                    points = 0
                    weight = 0
                    explanation = (
                        "This outcome is an escalation, so there was no repair "
                        "for you to verify."
                    )

            categories.append(
                {
                    "key": name,
                    "label": label,
                    "points": points,
                    "max": weight,
                    "status": status,
                    "explanation": explanation,
                }
            )

    note_text = _last_student_note(events)
    return {
        "coaching_tier": "limited" if limited else "full",
        "result": {
            "passed": passed,
            "score": grade.overall_score,
            "attempts_remaining": attempts_remaining,
            "outcome": outcome,
        },
        "categories": categories,
        "student_note": note_text,
        "note_dimensions": _note_dimensions(note_text),
        # The ordered path and the correct escalation destination are withheld
        # while the student still has a graded attempt to copy them into.
        "stronger_path": []
        if limited
        else (
            list(definition_json["simulation_fixture"]["completion"].values())
            if definition_json.get("objective_catalog_version") in {"realism-v1", "realism-v2"}
            else _stronger_path(objective_def, profile)
        ),
        # Whether escalation was the right call - and, by implication, the
        # correct team - is only revealed once there is no graded attempt left.
        "escalation_feedback": (
            None
            if limited
            else (
                {
                    "appropriate": stable_key == "inc2509" or bool(definition_json["simulation_fixture"].get("escalation")),
                    "text": definition_json["simulation_fixture"]["completion"][
                        "whyItWorked"
                    ],
                }
                if definition_json.get("objective_catalog_version") in {"realism-v1", "realism-v2"}
                else _escalation_feedback(profile, escalated, passed)
            )
        ),
    }
