"""Validation for administrator-authored Service Desk scenario definitions."""

from __future__ import annotations

from typing import Any


_PRIORITIES = {"low", "medium", "high", "critical"}
_DIFFICULTIES = {"easy", "medium", "hard"}
_PREDICATES = {
    "action_event_occurred",
    "directory_group_membership",
    "directory_user_field",
    "ticket_verified_resolved",
}


def _text(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} is required.")


def _record(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object.")
        return {}
    return value


def _list(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list.")
        return []
    return value


def validate_scenario_definition(definition: dict[str, Any]) -> list[str]:
    """Return actionable validation errors; an empty list is publishable."""
    errors: list[str] = []
    for field in ("title", "slug", "category", "priority", "difficulty", "explanation"):
        _text(definition.get(field), field, errors)

    if definition.get("priority") not in _PRIORITIES:
        errors.append("priority must be low, medium, high, or critical.")
    if definition.get("difficulty") not in _DIFFICULTIES:
        errors.append("difficulty must be easy, medium, or hard.")
    point_value = definition.get("pointValue")
    if not isinstance(point_value, int) or isinstance(point_value, bool) or point_value <= 0:
        errors.append("pointValue must be a positive whole number.")

    description = _record(definition.get("description"), "description", errors)
    for field in ("issue", "reportedByLine", "businessImpact"):
        _text(description.get(field), f"description.{field}", errors)
    troubleshooting = _list(
        description.get("troubleshooting"), "description.troubleshooting", errors
    )
    if not any(isinstance(step, str) and step.strip() for step in troubleshooting):
        errors.append("description.troubleshooting needs at least one meaningful step.")

    requester = _record(definition.get("requester"), "requester", errors)
    for field in ("name", "department", "email", "contact", "location"):
        _text(requester.get(field), f"requester.{field}", errors)

    device = _record(definition.get("device"), "device", errors)
    for field in ("assetTag", "deviceName", "kind", "operatingSystem", "state"):
        _text(device.get(field), f"device.{field}", errors)

    sla = _record(definition.get("sla"), "sla", errors)
    for field in ("dueAt", "target"):
        _text(sla.get(field), f"sla.{field}", errors)

    world = _record(definition.get("initialWorldState"), "initialWorldState", errors)
    for field in ("directoryOverlaySeeds", "assetOverlaySeeds"):
        _record(world.get(field), f"initialWorldState.{field}", errors)
    _list(world.get("chatMessageSeeds"), "initialWorldState.chatMessageSeeds", errors)

    objectives = _list(definition.get("objectives"), "objectives", errors)
    if not objectives:
        errors.append("At least one grading objective is required.")
    elif not any(isinstance(item, dict) and item.get("required") is True for item in objectives):
        errors.append("At least one grading objective must be required.")

    seen_ids: set[str] = set()
    for index, raw in enumerate(objectives):
        item = _record(raw, f"objectives[{index}]", errors)
        objective_id = item.get("id")
        _text(objective_id, f"objectives[{index}].id", errors)
        if isinstance(objective_id, str):
            if objective_id in seen_ids:
                errors.append(f"objectives[{index}].id must be unique.")
            seen_ids.add(objective_id)
        _text(item.get("description"), f"objectives[{index}].description", errors)
        if item.get("predicateType") not in _PREDICATES:
            errors.append(f"objectives[{index}].predicateType is unsupported.")
        _record(item.get("predicateParams"), f"objectives[{index}].predicateParams", errors)
        points = item.get("pointValue")
        if not isinstance(points, int) or isinstance(points, bool) or points < 0:
            errors.append(f"objectives[{index}].pointValue must be zero or greater.")

    for collection in ("requiredActions", "forbiddenActions"):
        rows = _list(definition.get(collection), collection, errors)
        for index, raw in enumerate(rows):
            item = _record(raw, f"{collection}[{index}]", errors)
            _text(item.get("id"), f"{collection}[{index}].id", errors)
            _text(item.get("actionType"), f"{collection}[{index}].actionType", errors)
            _text(item.get("description"), f"{collection}[{index}].description", errors)
            if "payloadMatch" in item:
                _record(item.get("payloadMatch"), f"{collection}[{index}].payloadMatch", errors)

    hints = _list(definition.get("hints"), "hints", errors)
    if len(hints) < 3:
        errors.append("Add at least three progressive hints before publishing.")
    for index, raw in enumerate(hints):
        item = _record(raw, f"hints[{index}]", errors)
        _text(item.get("id"), f"hints[{index}].id", errors)
        _text(item.get("text"), f"hints[{index}].text", errors)
        penalty = item.get("pointPenalty")
        if not isinstance(penalty, int) or isinstance(penalty, bool) or penalty < 0:
            errors.append(f"hints[{index}].pointPenalty must be zero or greater.")

    return errors
