"""Server-side grading for the Phase 4C.3 final-shift incident queue.

Mirrors the weighted, server-computed rubric style already established by
app/services/service_desk_grading.py: the score is recomputed exclusively
from the LabTemplate's stored case definition (the answer key, never sent to
the client — see app/routers/final_shift.py's student-safe serializer) and
the LabRun's accumulated structured_feedback (the student's actions).
"""

from __future__ import annotations

from math import floor
from typing import Any

DIMENSION_WEIGHTS = {
    "prioritization": 15,
    "investigation": 20,
    "diagnosis": 20,
    "safe_action": 20,
    "verification": 10,
    "documentation": 10,
    "handoff": 5,
}
PASS_THRESHOLD_PCT = 80
DOCUMENTATION_FIELDS = ("issue", "evidence", "action", "verification")


def _js_round(value: float) -> int:
    return floor(value + 0.5)


def _incident_state(feedback: dict, key: str) -> dict:
    return (feedback.get("incidents") or {}).get(key) or {}


def _investigation_score(incident: dict, state: dict) -> float:
    required = set(incident["required_inspections"])
    if not required:
        return 100.0
    inspected = set(state.get("inspected_panel_ids", []))
    return 100.0 * len(required & inspected) / len(required)


def _diagnosis_score(incident: dict, state: dict) -> float:
    return 100.0 if state.get("diagnosis_answer") == incident["diagnosis"]["correct"] else 0.0


def _safe_action_score(incident: dict, state: dict) -> float:
    action_choice = state.get("action_choice")
    ever_unsafe = bool(state.get("unsafe_action_attempted"))
    if action_choice != incident["correct_action_id"]:
        return 0.0
    return 60.0 if ever_unsafe else 100.0


def _final_action_is_safe(incident: dict, state: dict) -> bool:
    action_choice = state.get("action_choice")
    actions_by_id = {action["id"]: action for action in incident["actions"]}
    chosen = actions_by_id.get(action_choice)
    return bool(chosen and chosen["safe"] and action_choice == incident["correct_action_id"])


def _verification_score(state: dict) -> float:
    return 100.0 if state.get("status") in {"resolved", "escalated"} else 0.0


def _documentation_score(incident: dict, state: dict) -> float:
    doc = state.get("documentation") or {}
    required = list(DOCUMENTATION_FIELDS)
    if incident.get("requires_user_update"):
        required.append("user_update")
    if incident.get("requires_escalation"):
        required.append("escalation")
    if not required:
        return 100.0
    present = sum(1 for field in required if str(doc.get(field, "")).strip())
    return 100.0 * present / len(required)


def _priority_score(incidents: list[dict], feedback: dict) -> float:
    chosen_order = feedback.get("queue_order") or []
    keys = [incident["key"] for incident in incidents]
    if set(chosen_order) != set(keys) or len(chosen_order) < 2:
        return 0.0
    expected_rank = {incident["key"]: incident["expected_priority_rank"] for incident in incidents}
    pairs = [(a, b) for i, a in enumerate(keys) for b in keys[i + 1 :]]
    correct_pairs = 0
    for a, b in pairs:
        chosen_a_first = chosen_order.index(a) < chosen_order.index(b)
        expected_a_first = expected_rank[a] < expected_rank[b]
        if chosen_a_first == expected_a_first:
            correct_pairs += 1
    return 100.0 * correct_pairs / len(pairs) if pairs else 100.0


def _handoff_score(case: dict, feedback: dict) -> float:
    handoff = feedback.get("handoff") or {}
    fields = case["final_shift"]["handoff_fields"]
    if not fields:
        return 100.0
    present = sum(1 for field in fields if str(handoff.get(field, "")).strip())
    return 100.0 * present / len(fields)


def compute_final_shift_grade(case: dict, feedback: dict) -> dict[str, Any]:
    """Recompute a final-shift grade exclusively from the case definition and structured_feedback."""
    incidents = case["final_shift"]["incidents"]
    per_incident: dict[str, dict] = {}
    dim_totals = {dim: 0.0 for dim in DIMENSION_WEIGHTS if dim not in {"prioritization", "handoff"}}

    all_resolved_or_escalated = True
    safety_gate_ok = True
    for incident in incidents:
        state = _incident_state(feedback, incident["key"])
        investigation = _investigation_score(incident, state)
        diagnosis = _diagnosis_score(incident, state)
        safe_action = _safe_action_score(incident, state)
        verification = _verification_score(state)
        documentation = _documentation_score(incident, state)
        dim_totals["investigation"] += investigation
        dim_totals["diagnosis"] += diagnosis
        dim_totals["safe_action"] += safe_action
        dim_totals["verification"] += verification
        dim_totals["documentation"] += documentation
        per_incident[incident["key"]] = {
            "investigation": investigation,
            "diagnosis": diagnosis,
            "safe_action": safe_action,
            "verification": verification,
            "documentation": documentation,
            "status": state.get("status"),
        }
        if state.get("status") not in {"resolved", "escalated"}:
            all_resolved_or_escalated = False
        if not _final_action_is_safe(incident, state):
            safety_gate_ok = False

    incident_count = len(incidents) or 1
    dimension_scores = {dim: total / incident_count for dim, total in dim_totals.items()}
    dimension_scores["prioritization"] = _priority_score(incidents, feedback)
    dimension_scores["handoff"] = _handoff_score(case, feedback)

    overall_score = _js_round(
        sum(dimension_scores[dim] * weight / 100 for dim, weight in DIMENSION_WEIGHTS.items())
    )
    passed = overall_score >= PASS_THRESHOLD_PCT and safety_gate_ok and all_resolved_or_escalated

    if not all_resolved_or_escalated:
        feedback_summary = "Every incident must reach resolved or escalated before the shift can be handed off."
    elif not safety_gate_ok:
        feedback_summary = "An unsafe action was left in place on at least one incident. A high score cannot offset an unsafe final decision."
    elif passed:
        feedback_summary = "The shift is complete: all incidents were investigated, actioned safely, verified, and documented."
    else:
        feedback_summary = f"Overall score is below the {PASS_THRESHOLD_PCT}% pass threshold. Review investigation and diagnosis on the lowest-scoring incidents."

    return {
        "passed": passed,
        "overall_score": overall_score,
        "dimension_scores": {dim: round(score, 1) for dim, score in dimension_scores.items()},
        "dimension_weights": DIMENSION_WEIGHTS,
        "per_incident": per_incident,
        "all_resolved_or_escalated": all_resolved_or_escalated,
        "safety_gate_ok": safety_gate_ok,
        "feedback_summary": feedback_summary,
        "rubric_version": "final-shift-v1",
    }
