"""Server-owned Service Desk evidence and process-grading definitions.

The browser can retain a resume snapshot, but it cannot manufacture any of
the evidence below.  Only successful actions accepted by the transition graph
are considered here.  Curated scenarios use the same five process categories
as the simulator; legacy published versions retain their historical catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROCESS_CATALOG_VERSION = "process-v3"
PROCESS_WEIGHTS = {
    "investigation": 15,
    "diagnosis": 25,
    "remediation": 30,
    "verification": 20,
    "documentation": 10,
}


@dataclass(frozen=True)
class EvidenceRule:
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class EvidenceObjective:
    """One fact a learner may establish through any of several safe actions."""

    id: str
    any_of: tuple[EvidenceRule, ...]


@dataclass(frozen=True)
class ProcessCategory:
    name: str
    objectives: tuple[EvidenceObjective, ...]


@dataclass(frozen=True)
class ScenarioObjectiveDefinition:
    """A versioned, declarative server grading profile.

    ``required_*`` are retained for generic Scenario Builder definitions and
    historical scenarios.  Curated process profiles instead expose category
    objectives, which lets a valid repair earn repair credit without awarding
    the investigation and diagnosis points for a guess.
    """

    required_all: tuple[EvidenceRule, ...] = ()
    required_any: tuple[EvidenceRule, ...] = ()
    categories: tuple[ProcessCategory, ...] = ()

    @property
    def is_process_profile(self) -> bool:
        return bool(self.categories)

    @property
    def authorized_rules(self) -> tuple[EvidenceRule, ...]:
        if not self.categories:
            return (*self.required_all, *self.required_any)
        return tuple(
            rule
            for category in self.categories
            for objective in category.objectives
            for rule in objective.any_of
        )


def _remote(ticket: str, asset: str, step: str) -> EvidenceRule:
    return EvidenceRule(
        "remote_desktop.perform_scenario_step",
        {"ticketId": ticket, "assetTag": asset, "stepId": step},
    )


def _terminal(asset: str, *commands: str) -> EvidenceObjective:
    return EvidenceObjective(
        "terminal-evidence",
        tuple(
            EvidenceRule(
                "remote_desktop.run_terminal_command",
                {"assetTag": asset, "command": command},
            )
            for command in commands
        ),
    )


def _objective(identifier: str, *rules: EvidenceRule) -> EvidenceObjective:
    return EvidenceObjective(identifier, rules)


def _process(*categories: ProcessCategory) -> ScenarioObjectiveDefinition:
    return ScenarioObjectiveDefinition(categories=categories)


# This is the catalog assigned to newly published/current Service Desk
# versions.  The values deliberately mirror remote-desktop-fixtures.ts.
SCENARIO_OBJECTIVES: dict[str, ScenarioObjectiveDefinition] = {
    "inc2401": _process(
        ProcessCategory("investigation", (
            _objective("profile-evidence-reviewed", _remote("INC2401", "NX-4831", "mail.review-alert")),
        )),
        ProcessCategory("diagnosis", (
            _objective("sign-in-loop-reproduced", _remote("INC2401", "NX-4831", "browser.retry-sign-in")),
        )),
        ProcessCategory("remediation", (
            _objective("profile-storage-cleared", _remote("INC2401", "NX-4831", "settings.clear-profile-storage")),
        )),
        ProcessCategory("verification", (
            _objective("finance-portal-restored", _remote("INC2401", "NX-4831", "browser.retry-sign-in")),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2401", "assetTag": "NX-4831"})),
        )),
    ),
    "inc2402": _process(
        ProcessCategory("investigation", (_terminal("NX-7714", "ipconfig"),)),
        ProcessCategory("diagnosis", (_terminal("NX-7714", "ping 10.20.0.10"),)),
        ProcessCategory("remediation", (
            _objective("managed-profile-refreshed", _remote("INC2402", "NX-7714", "settings.repair-network")),
            _objective("lease-renewed", _remote("INC2402", "NX-7714", "system.renew-address")),
        )),
        ProcessCategory("verification", (
            _objective("scanner-stable", _remote("INC2402", "NX-7714", "chat.confirm-restored")),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2402", "assetTag": "NX-7714"})),
        )),
    ),
    "inc2403": _process(
        ProcessCategory("investigation", (
            _objective("export-failure-reproduced", _remote("INC2403", "NX-3560", "browser.retry-export")),
        )),
        ProcessCategory("diagnosis", (
            _objective("pending-update-inspected", EvidenceRule("remote_desktop.update_install", {"assetTag": "NX-3560"})),
            _objective("system-scope-checked", EvidenceRule("remote_desktop.explorer_navigate", {"assetTag": "NX-3560", "path": "This PC"})),
        )),
        ProcessCategory("remediation", (
            _objective("reliability-update-applied", EvidenceRule("remote_desktop.update_restart", {"assetTag": "NX-3560"})),
            _objective("pdf-helper-restarted", _remote("INC2403", "NX-3560", "system.restart-pdf-helper")),
        )),
        ProcessCategory("verification", (
            _objective("export-restored", _remote("INC2403", "NX-3560", "browser.retry-export")),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2403", "assetTag": "NX-3560"})),
        )),
    ),
    "inc2404": _process(
        ProcessCategory("investigation", (
            _objective("headset-tested-away", EvidenceRule("asset.record_isolation", {"assetTag": "NX-9052", "test": "affected-headset-known-good-workstation"})),
        )),
        ProcessCategory("diagnosis", (
            _objective(
                "fault-isolated",
                EvidenceRule("asset.record_isolation", {"assetTag": "NX-9052", "test": "affected-headset-known-good-workstation"}),
                EvidenceRule("asset.record_isolation", {"assetTag": "NX-9052", "test": "known-good-headset-affected-workstation"}),
                EvidenceRule("asset.record_isolation", {"assetTag": "NX-9052", "test": "alternate-usb-port"}),
            ),
        )),
        ProcessCategory("remediation", (
            _objective("faulty-headset-recorded", EvidenceRule("asset.change_status", {"assetTag": "NX-9052", "status": "damaged"})),
            _objective("replacement-shipped", EvidenceRule("shipping.create", {"recipientDirectoryUserId": "directory-user-elliot-ward", "equipment": [{"name": "Headset", "quantity": 1}]})),
        )),
        ProcessCategory("verification", (
            _objective("clean-audio-confirmed", EvidenceRule("asset.record_isolation", {"assetTag": "NX-9052", "test": "replacement-clean-audio"})),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("ticket.add_note", {"ticketId": "INC2404"})),
        )),
    ),
    "inc2405": _process(
        ProcessCategory("investigation", (_terminal("NX-6128", "net use"),)),
        ProcessCategory("diagnosis", (_terminal("NX-6128", "net use"),)),
        ProcessCategory("remediation", (
            _objective("calendar-mapping-repaired", _remote("INC2405", "NX-6128", "explorer.repair-mapping")),
        )),
        ProcessCategory("verification", (
            _objective("calendar-workspace-opened", _remote("INC2405", "NX-6128", "explorer.verify-share")),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2405", "assetTag": "NX-6128"})),
        )),
    ),
    "inc2406": _process(
        ProcessCategory("investigation", (
            _objective("partner-share-unreachable", EvidenceRule("remote_desktop.explorer_navigate", {"assetTag": "NX-2047", "path": "Z:"})),
        )),
        ProcessCategory("diagnosis", (
            _objective("vpn-session-inspected", EvidenceRule("remote_desktop.vpn_connect", {"assetTag": "NX-2047"})),
        )),
        ProcessCategory("remediation", (
            _objective("vpn-connected", EvidenceRule("remote_desktop.vpn_complete_connection", {"assetTag": "NX-2047"})),
        )),
        ProcessCategory("verification", (
            _objective("partner-share-restored", EvidenceRule("remote_desktop.explorer_navigate", {"assetTag": "NX-2047", "path": "Z:"})),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2406", "assetTag": "NX-2047"})),
        )),
    ),
    "inc2407": _process(
        ProcessCategory("investigation", (_terminal("NX-8892", "ping 10.20.0.10", "ipconfig", "ipconfig /all"),)),
        ProcessCategory("diagnosis", (
            _terminal("NX-8892", "ipconfig", "ipconfig /all"),
            _objective("ip-connectivity-proved", EvidenceRule("remote_desktop.run_terminal_command", {"assetTag": "NX-8892", "command": "ping 10.20.0.10"})),
            _terminal("NX-8892", "nslookup intranet.nexus.internal", "ping intranet.nexus.internal"),
        )),
        ProcessCategory("remediation", (
            _objective("approved-dns-configured", EvidenceRule("remote_desktop.settings_update_dns", {"assetTag": "NX-8892", "primaryDns": "10.20.0.10", "secondaryDns": "10.20.0.11"})),
        )),
        ProcessCategory("verification", (
            _terminal("NX-8892", "nslookup intranet.nexus.internal", "ping intranet.nexus.internal"),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2407", "assetTag": "NX-8892"})),
        )),
    ),
    "inc2408": _process(
        ProcessCategory("investigation", (
            _objective("failed-print-captured", _remote("INC2408", "NX-4419", "printer.test-page")),
        )),
        ProcessCategory("diagnosis", (
            _terminal("NX-4419", "sc query \"Print Spooler\"", "tasklist"),
        )),
        ProcessCategory("remediation", (
            _objective("spooler-started", EvidenceRule("remote_desktop.start_service", {"assetTag": "NX-4419", "serviceName": "Print Spooler"})),
        )),
        ProcessCategory("verification", (
            _objective("test-page-printed", _remote("INC2408", "NX-4419", "printer.test-page")),
        )),
        ProcessCategory("documentation", (
            _objective("closure-note", EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2408", "assetTag": "NX-4419"})),
        )),
    ),
}


# Kept solely for attempts already pinned to the immutable pre-process
# published versions.  New/current versions select SCENARIO_OBJECTIVES through
# ``objective_catalog_version`` below.
LEGACY_SCENARIO_OBJECTIVES: dict[str, ScenarioObjectiveDefinition] = {
    "inc2401": ScenarioObjectiveDefinition(required_any=(
        EvidenceRule("directory.unlock_account", {"directoryUserId": "directory-user-avery-brooks"}),
        EvidenceRule("directory.reset_mfa", {"directoryUserId": "directory-user-avery-brooks"}),
    )),
    "inc2402": ScenarioObjectiveDefinition(required_all=(
        _remote("INC2402", "NX-7714", "settings.repair-network"), _remote("INC2402", "NX-7714", "system.renew-address"),
    )),
    "inc2403": ScenarioObjectiveDefinition(required_all=(
        _remote("INC2403", "NX-3560", "updates.install"), _remote("INC2403", "NX-3560", "system.restart-pdf-helper"),
    )),
    "inc2404": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("asset.change_status", {"assetTag": "NX-9052", "status": "damaged"}),
        EvidenceRule("shipping.create", {"recipientDirectoryUserId": "directory-user-elliot-ward", "equipment": [{"name": "Headset", "quantity": 1}]}),
        EvidenceRule("ticket.add_note", {"ticketId": "INC2404"}),
    )),
    "inc2405": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("directory.update_groups", {"directoryUserId": "directory-user-sloane-rivera", "add": ["Facilities Calendar"]}),
    )),
    "inc2406": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("remote_desktop.vpn_complete_connection", {"assetTag": "NX-2047"}), EvidenceRule("remote_desktop.explorer_reconnect_drive", {"assetTag": "NX-2047", "driveLetter": "Z:"}), EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2406", "assetTag": "NX-2047"}),
    )),
    "inc2407": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("remote_desktop.settings_update_dns", {"assetTag": "NX-8892"}), EvidenceRule("remote_desktop.run_terminal_command", {"assetTag": "NX-8892", "command": "nslookup intranet.nexus.internal"}), EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2407", "assetTag": "NX-8892"}),
    )),
    "inc2408": ScenarioObjectiveDefinition(required_all=(
        EvidenceRule("remote_desktop.restart_service", {"assetTag": "NX-4419", "serviceName": "Print Spooler"}), _remote("INC2408", "NX-4419", "printer.test-page"), EvidenceRule("remote_desktop.add_internal_note", {"ticketId": "INC2408", "assetTag": "NX-4419"}),
    )),
}


def definition_objectives(definition_json: dict[str, Any]) -> ScenarioObjectiveDefinition | None:
    """Translate Builder predicates into the historical trusted-rule format."""
    rules: list[EvidenceRule] = []
    for objective in definition_json.get("objectives", []):
        if not isinstance(objective, dict) or objective.get("required") is not True:
            continue
        predicate = objective.get("predicateType")
        params = objective.get("predicateParams")
        if not isinstance(params, dict):
            return None
        if predicate == "action_event_occurred":
            event_type, payload = params.get("actionType"), params.get("payloadMatch", {})
            if not isinstance(event_type, str) or not isinstance(payload, dict):
                return None
            rules.append(EvidenceRule(event_type, payload))
        elif predicate == "directory_group_membership":
            user_id, group = params.get("directoryUserId"), params.get("group")
            if not isinstance(user_id, str) or not isinstance(group, str):
                return None
            rules.append(EvidenceRule("directory.update_groups", {"directoryUserId": user_id, "add" if params.get("includes") is True else "remove": [group]}))
        elif predicate == "directory_user_field":
            user_id, field, equals = params.get("directoryUserId"), params.get("field"), params.get("equals")
            event_type = {("locked", False): "directory.unlock_account", ("disabled", False): "directory.enable_account", ("disabled", True): "directory.disable_account"}.get((field, equals))
            if not isinstance(user_id, str) or event_type is None:
                return None
            rules.append(EvidenceRule(event_type, {"directoryUserId": user_id}))
        elif predicate != "ticket_verified_resolved":
            return None
    return ScenarioObjectiveDefinition(required_all=tuple(rules)) if rules else None


def objective_definition(stable_key: str, definition_json: dict[str, Any]) -> ScenarioObjectiveDefinition | None:
    key = stable_key.lower()
    if definition_json.get("objective_catalog_version") == PROCESS_CATALOG_VERSION:
        return SCENARIO_OBJECTIVES.get(key)
    return LEGACY_SCENARIO_OBJECTIVES.get(key) or definition_objectives(definition_json)


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


def _matching_positions(events: list[Any], objective: EvidenceObjective) -> list[int]:
    return [
        index
        for index, event in enumerate(events)
        if event.trusted is True
        and event.success is True
        and any(event.event_type == rule.event_type and payload_matches(event.payload_json or {}, rule.payload) for rule in objective.any_of)
    ]


def evaluate_objectives(stable_key: str, events: list[Any], definition_json: dict[str, Any] | None = None) -> tuple[bool, dict[str, bool]]:
    definition = objective_definition(stable_key, definition_json or {})
    if definition is None:
        return False, {"server_verifiable": False}

    if not definition.is_process_profile:
        def has(rule: EvidenceRule) -> bool:
            return any(event.trusted is True and event.success is True and event.event_type == rule.event_type and payload_matches(event.payload_json or {}, rule.payload) for event in events)
        checks = {f"{rule.event_type}:{index}": has(rule) for index, rule in enumerate(definition.required_all)}
        any_passed = not definition.required_any or any(has(rule) for rule in definition.required_any)
        if definition.required_any:
            checks["approved_corrective_action"] = any_passed
        return all(checks.values()) and any_passed, checks | {"server_verifiable": True}

    positions = {
        category.name: [position for objective in category.objectives for position in _matching_positions(events, objective)]
        for category in definition.categories
    }
    remediation = next(category for category in definition.categories if category.name == "remediation")
    remediation_positions = [_matching_positions(events, objective) for objective in remediation.objectives]
    remediation_met = all(matches for matches in remediation_positions)
    first_repair = min((position for matches in remediation_positions for position in matches), default=None)
    last_repair = max((position for matches in remediation_positions for position in matches), default=None)

    checks: dict[str, bool] = {"server_verifiable": True}
    for category in definition.categories:
        objective_positions = [_matching_positions(events, objective) for objective in category.objectives]
        met = all(matches for matches in objective_positions)
        if category.name in {"investigation", "diagnosis"} and first_repair is not None:
            met = met and all(any(position < first_repair for position in matches) for matches in objective_positions)
        if category.name == "verification":
            met = met and last_repair is not None and all(any(position > last_repair for position in matches) for matches in objective_positions)
        checks[category.name] = met
    checks["technical_complete"] = remediation_met and checks.get("verification", False) and checks.get("documentation", False)
    return checks["technical_complete"], checks
