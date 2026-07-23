"""Executable health validation for published declarative scenarios."""

from app.schemas.service_desk import ScenarioMode
from app.services.service_desk_definitions import published_definition
from app.services.service_desk_engine import apply_action


def run_definition_health(definition) -> dict:
    """Exercise the authored valid path without a database or a browser."""
    state = dict(definition.initial_state)
    earned: set[str] = set()
    for index, step in enumerate(definition.health_path, start=1):
        outcome = apply_action(
            definition,
            state,
            action=step.action,
            payload=step.payload,
            mode=ScenarioMode.LEARNING,
        )
        if not outcome.success or outcome.critical_failure:
            return {"valid": False, "error": f"Health path step {index} did not succeed"}
        state = outcome.state
        if outcome.score_key:
            earned.add(outcome.score_key)
    technical_complete = all(state.get(condition.field) == condition.equals for condition in definition.success_conditions)
    score = sum(points for key, points in definition.scoring.point_values.items() if key in earned)
    passed = technical_complete and not state.get("critical_failure", False) and score >= definition.scoring.passing_score
    return {
        "valid": passed,
        "state": state,
        "score": score,
        "technical_complete": technical_complete,
        "passed": passed,
        "step_count": len(definition.health_path),
    }


def run_published_scenario_health(version) -> dict:
    return run_definition_health(published_definition(version))
