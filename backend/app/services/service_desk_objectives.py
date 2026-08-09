"""Declarative, server-owned completion rules for seeded Service Desk tickets.

These rules deliberately evaluate the append-only event history, never a client
snapshot or a close payload.  A rule is a small, reusable event predicate;
adding a scenario is data entry rather than a grading branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceRule:
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ScenarioObjectiveDefinition:
    # Each item in required_all must be independently present.  Each tuple in
    # required_any represents one corrective alternative.
    required_all: tuple[EvidenceRule, ...] = ()
    required_any: tuple[EvidenceRule, ...] = ()
    # Every objective action requires a server-authorized ticket assignment.
    # Definitions can add stronger ordered prerequisites as scenarios mature.


def _remote(ticket: str, asset: str, step: str) -> EvidenceRule:
    return EvidenceRule(
        "remote_desktop.perform_scenario_step",
        {"ticketId": ticket, "assetTag": asset, "stepId": step},
    )


SCENARIO_OBJECTIVES: dict[str, ScenarioObjectiveDefinition] = {
    "inc2401": ScenarioObjectiveDefinition(
        required_any=(
            EvidenceRule("directory.unlock_account", {"directoryUserId": "directory-user-avery-brooks"}),
            EvidenceRule("directory.reset_mfa", {"directoryUserId": "directory-user-avery-brooks"}),
        )
    ),
    "inc2402": ScenarioObjectiveDefinition(required_all=(
        _remote("INC2402", "NX-7714", "settings.repair-network"),
        _remote("INC2402", "NX-7714", "system.renew-address"),
    )),
    "inc2403": ScenarioObjectiveDefinition(required_all=(
        _remote("INC2403", "NX-3560", "updates.install"),
        _remote("INC2403", "NX-3560", "system.restart-pdf-helper"),
    )),
    "inc2404": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("asset.change_status", {"assetTag": "NX-9052", "status": "damaged"}),
        EvidenceRule("shipping.create", {
            "recipientDirectoryUserId": "directory-user-elliot-ward",
            "equipment": [{"name": "Headset", "quantity": 1}],
        }),
        EvidenceRule("ticket.add_note", {"ticketId": "INC2404"}),
    )),
    "inc2405": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("directory.update_groups", {
            "directoryUserId": "directory-user-sloane-rivera", "add": ["Facilities Calendar"]
        }),
    )),
    "inc2406": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("remote_desktop.vpn_complete_connection", {"assetTag": "NX-2047"}),
        EvidenceRule("remote_desktop.explorer_reconnect_drive", {"assetTag": "NX-2047", "driveLetter": "Z:"}),
        EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2406", "assetTag": "NX-2047"}),
    )),
    "inc2407": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("remote_desktop.settings_update_dns", {"assetTag": "NX-8892"}),
        EvidenceRule("remote_desktop.run_terminal_command", {"assetTag": "NX-8892", "command": "nslookup intranet.nexus.internal"}),
        EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2407", "assetTag": "NX-8892"}),
    )),
    "inc2408": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("remote_desktop.restart_service", {"assetTag": "NX-4419", "serviceName": "Print Spooler"}),
        _remote("INC2408", "NX-4419", "printer.test-page"),
        EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2408", "assetTag": "NX-4419"}),
    )),
}


def definition_objectives(definition_json: dict[str, Any]) -> ScenarioObjectiveDefinition | None:
    """Translate builder predicates into the same trusted-event rule format."""
    rules: list[EvidenceRule] = []
    for objective in definition_json.get("objectives", []):
        if not isinstance(objective, dict) or objective.get("required") is not True:
            continue
        predicate = objective.get("predicateType")
        params = objective.get("predicateParams")
        if not isinstance(params, dict):
            return None
        if predicate == "action_event_occurred":
            event_type = params.get("actionType")
            payload = params.get("payloadMatch", {})
            if not isinstance(event_type, str) or not isinstance(payload, dict):
                return None
            rules.append(EvidenceRule(event_type, payload))
        elif predicate == "directory_group_membership":
            user_id, group = params.get("directoryUserId"), params.get("group")
            if not isinstance(user_id, str) or not isinstance(group, str):
                return None
            field = "add" if params.get("includes") is True else "remove"
            rules.append(EvidenceRule("directory.update_groups", {
                "directoryUserId": user_id, field: [group],
            }))
        elif predicate == "directory_user_field":
            user_id, field, equals = (
                params.get("directoryUserId"), params.get("field"), params.get("equals")
            )
            event_type = {
                ("locked", False): "directory.unlock_account",
                ("disabled", False): "directory.enable_account",
                ("disabled", True): "directory.disable_account",
            }.get((field, equals))
            if not isinstance(user_id, str) or event_type is None:
                return None
            rules.append(EvidenceRule(event_type, {"directoryUserId": user_id}))
        elif predicate != "ticket_verified_resolved":
            return None
    return ScenarioObjectiveDefinition(required_all=tuple(rules)) if rules else None


def objective_definition(stable_key: str, definition_json: dict[str, Any]) -> ScenarioObjectiveDefinition | None:
    return SCENARIO_OBJECTIVES.get(stable_key.lower()) or definition_objectives(definition_json)


def payload_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Match expected scalar fields and required members without trusting extras."""
    for key, value in expected.items():
        candidate = actual.get(key)
        if isinstance(value, list):
            if not isinstance(candidate, list) or not all(item in candidate for item in value):
                return False
        elif candidate != value:
            return False
    return True


def evaluate_objectives(stable_key: str, events: list[Any], definition_json: dict[str, Any] | None = None) -> tuple[bool, dict[str, bool]]:
    definition = objective_definition(stable_key, definition_json or {})
    if definition is None:
        return False, {"server_verifiable": False}

    def has(rule: EvidenceRule) -> bool:
        return any(
            event.trusted is True
            and
            event.success is True
            and event.event_type == rule.event_type
            and payload_matches(event.payload_json or {}, rule.payload)
            for event in events
        )

    checks = {
        f"{rule.event_type}:{index}": has(rule)
        for index, rule in enumerate(definition.required_all)
    }
    any_passed = not definition.required_any or any(has(rule) for rule in definition.required_any)
    if definition.required_any:
        checks["approved_corrective_action"] = any_passed
    return all(checks.values()) and any_passed, checks | {"server_verifiable": True}
