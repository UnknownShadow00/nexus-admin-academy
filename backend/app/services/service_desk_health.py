"""Executable health validation for published declarative scenarios."""

from app.services.service_desk_definitions import published_definition
from app.services.service_desk_engine import apply_action


def run_definition_health(definition) -> dict:
    """Exercise valid paths in every published mode without a database or browser."""
    mode_reports = {}
    for mode in definition.supported_modes:
        state = dict(definition.initial_state)
        earned: set[str] = set()
        for index, step in enumerate(definition.health_path, start=1):
            outcome = apply_action(definition, state, action=step.action, payload=step.payload, mode=mode)
            if not outcome.success or outcome.critical_failure:
                return {"valid": False, "error": f"{mode.value} health path step {index} did not succeed"}
            state = outcome.state
            if outcome.score_key:
                earned.add(outcome.score_key)
        technical_complete = all(state.get(condition.field) == condition.equals for condition in definition.success_conditions)
        score = sum(points for key, points in definition.scoring.point_values.items() if key in earned)
        passed = technical_complete and not state.get("critical_failure", False) and score >= definition.scoring.passing_score
        mode_reports[mode.value] = {"passed": passed, "score": score, "state": state}
        if not passed:
            return {"valid": False, "error": f"{mode.value} health path did not pass"}
    return {
        "valid": all(report["passed"] for report in mode_reports.values()),
        "state": next(iter(mode_reports.values()))["state"],
        "score": next(iter(mode_reports.values()))["score"],
        "technical_complete": True,
        "passed": True,
        "step_count": len(definition.health_path),
        "modes": mode_reports,
    }


def run_published_scenario_health(version) -> dict:
    return run_definition_health(published_definition(version))
