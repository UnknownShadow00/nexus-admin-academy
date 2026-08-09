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
_SUPPORTED_ACTION_TYPES = {
    "asset.assign", "asset.change_status", "asset.unassign",
    "directory.disable_account", "directory.enable_account", "directory.reset_mfa",
    "directory.reset_password", "directory.unlock_account", "directory.update_groups",
    "shipping.create", "ticket.add_note",
    "remote_desktop.add_internal_note", "remote_desktop.explorer_reconnect_drive",
    "remote_desktop.perform_scenario_step", "remote_desktop.restart_service",
    "remote_desktop.run_terminal_command", "remote_desktop.settings_update_dns",
    "remote_desktop.vpn_complete_connection",
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
    server_evidence_objectives = 0
    for index, raw in enumerate(objectives):
        item = _record(raw, f"objectives[{index}]", errors)
        objective_id = item.get("id")
        _text(objective_id, f"objectives[{index}].id", errors)
        if isinstance(objective_id, str):
            if objective_id in seen_ids:
                errors.append(f"objectives[{index}].id must be unique.")
            seen_ids.add(objective_id)
        _text(item.get("description"), f"objectives[{index}].description", errors)
        predicate_type = item.get("predicateType")
        if predicate_type not in _PREDICATES:
            errors.append(f"objectives[{index}].predicateType is unsupported.")
        params = _record(item.get("predicateParams"), f"objectives[{index}].predicateParams", errors)
        if predicate_type == "action_event_occurred":
            action_type = params.get("actionType")
            if action_type not in _SUPPORTED_ACTION_TYPES:
                errors.append(f"objectives[{index}].predicateParams.actionType is not available in the student runtime.")
            payload_match = _record(
                params.get("payloadMatch"),
                f"objectives[{index}].predicateParams.payloadMatch",
                errors,
            )
            identifier = (
                "directoryUserId" if isinstance(action_type, str) and action_type.startswith("directory.")
                else "assetTag" if isinstance(action_type, str) and action_type.startswith(("asset.", "remote_desktop."))
                else "recipientDirectoryUserId" if action_type == "shipping.create"
                else "ticketId" if isinstance(action_type, str) and action_type.startswith("ticket.")
                else None
            )
            if identifier and not isinstance(payload_match.get(identifier), str):
                errors.append(f"objectives[{index}].predicateParams.payloadMatch.{identifier} is required for server verification.")
            if item.get("required") is True and action_type in _SUPPORTED_ACTION_TYPES and identifier and isinstance(payload_match.get(identifier), str):
                server_evidence_objectives += 1
        elif predicate_type == "directory_group_membership":
            if not isinstance(params.get("directoryUserId"), str) or not isinstance(params.get("group"), str) or not isinstance(params.get("includes"), bool):
                errors.append(f"objectives[{index}] needs directoryUserId, group, and a boolean includes value.")
            elif item.get("required") is True:
                server_evidence_objectives += 1
        elif predicate_type == "directory_user_field":
            supported_state = (params.get("field"), params.get("equals")) in {
                ("locked", False), ("disabled", False), ("disabled", True)
            }
            if not isinstance(params.get("directoryUserId"), str) or not supported_state:
                errors.append(f"objectives[{index}] describes a directory state the runtime cannot verify.")
            elif item.get("required") is True:
                server_evidence_objectives += 1
        points = item.get("pointValue")
        if not isinstance(points, int) or isinstance(points, bool) or points < 0:
            errors.append(f"objectives[{index}].pointValue must be zero or greater.")
    if objectives and server_evidence_objectives == 0:
        errors.append("At least one required objective must produce server-verifiable tool evidence.")

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


def validate_runtime_definition(stable_key: str, definition: dict[str, Any]) -> list[str]:
    """Ensure a custom scenario can emit its evidence through the shipped UI."""
    # Seeded scenarios have dedicated, server-owned transition graphs and tool
    # attribution. Custom scenarios currently have generic ticket-note support.
    from app.services.service_desk_objectives import SCENARIO_OBJECTIVES

    if stable_key.lower() in SCENARIO_OBJECTIVES:
        return []
    expected_ticket = stable_key.upper()
    errors: list[str] = []
    for index, objective in enumerate(definition.get("objectives", [])):
        if not isinstance(objective, dict) or objective.get("required") is not True:
            continue
        params = objective.get("predicateParams", {})
        if (
            objective.get("predicateType") != "action_event_occurred"
            or not isinstance(params, dict)
            or params.get("actionType") != "ticket.add_note"
            or not isinstance(params.get("payloadMatch"), dict)
            or params["payloadMatch"].get("ticketId") != expected_ticket
        ):
            errors.append(
                f"objectives[{index}] cannot be attributed by the custom-scenario runtime. "
                f"Use a ticket.add_note objective with payloadMatch.ticketId set to {expected_ticket}."
            )
    return errors
