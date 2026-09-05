"""Replay immutable, bounded workstation operations from the trusted ledger.

The TypeScript renderer interprets the same fixture. Neither snapshots nor
browser-provided evidence fields participate in this replay.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re

CATALOG_VERSION = "realism-v1"
CATALOG_PATH = Path(__file__).resolve().parents[1] / "data/service-desk-realism-v1.json"


def fixture_catalog():
    return json.loads(CATALOG_PATH.read_text())


def read_path(state, path):
    value = state
    for key in path.split("/"):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def write_path(state, path, value):
    keys = path.split("/")
    for key in keys[:-1]:
        state = state.setdefault(key, {})
    state[keys[-1]] = deepcopy(value)


def run_command(state, fixture, command):
    state = deepcopy(state)
    state["realism"]["lastEvidence"] = None
    branches = next(
        (
            rules
            for name, rules in fixture["commands"].items()
            if name.lower() == command.strip().lower()
        ),
        [],
    )
    rule = next(
        (
            candidate
            for candidate in branches
            if all(
                read_path(state, path) == expected
                for path, expected in candidate["when"].items()
            )
        ),
        None,
    )
    if not rule or rule["effect"] == "rejected":
        return state, [], False
    changed_before = state["realism"]["changed"]
    for path, value in rule["set"].items():
        write_path(state, path, value)
    storage = state.get("storage", {})
    if "usageNodeIds" in storage:
        used = storage["fixedUsedBytes"] + sum(
            state["filesystem"]["nodes"][node]["sizeBytes"]
            for node in storage["usageNodeIds"]
        )
        storage["freeBytes"] = storage["capacityBytes"] - used
    if rule["effect"] == "repair":
        state["realism"].update(changed=True, repaired=True)
    if rule["effect"] == "harmful":
        state["realism"]["harmful"] = True
    evidence = rule.get("evidence")
    pre_change = (
        fixture["categories"]["investigation"] + fixture["categories"]["diagnosis"]
    )
    if evidence and not (changed_before and evidence in pre_change):
        state["realism"]["observed"][evidence] = True
        state["realism"]["lastEvidence"] = evidence

    def render(match):
        value = read_path(state, match[1])
        return (
            ", ".join(value)
            if isinstance(value, list)
            else str(value).lower()
            if isinstance(value, bool)
            else str(value)
        )

    return (
        state,
        [re.sub(r"\{([^}]+)\}", render, line) for line in rule["output"]],
        True,
    )


def action_command(fixture, event_type, payload):
    if payload.get("assetTag") != fixture["assetTag"]:
        return None
    if event_type == "remote_desktop.run_terminal_command":
        return (
            payload.get("command") if isinstance(payload.get("command"), str) else None
        )
    if (
        event_type == "remote_desktop.restart_service"
        and payload.get("serviceName") == "Print Spooler"
    ):
        return "Restart-Service -Name Spooler"
    if (
        event_type in {"remote_desktop.start_service", "remote_desktop.stop_service"}
        and payload.get("serviceName") == "Print Spooler"
    ):
        return (
            "Start-Service -Name Spooler"
            if event_type.endswith(".start_service")
            else "Stop-Service -Name Spooler"
        )
    if (
        event_type == "remote_desktop.open_app"
        and payload.get("appId") == "services"
        and fixture["assetTag"] == "NX-2504"
    ):
        return 'sc query "Print Spooler"'
    if event_type == "remote_desktop.explorer_navigate":
        path = payload.get("path", "")
        if not isinstance(path, str):
            return None
        return f"Test-Path {path}" if path.startswith("\\\\") else f"dir {path}"
    return None


def replay(fixture, events):
    state = deepcopy(fixture["initial"])
    for event in events:
        if event.trusted is not True or event.success is not True:
            continue
        command = action_command(fixture, event.event_type, event.payload_json or {})
        if command is not None:
            state, _, _ = run_command(state, fixture, command)
    return state


def transition(fixture, events, event_type, payload):
    command = action_command(fixture, event_type, payload)
    if command is None:
        return None
    state, output, success = run_command(replay(fixture, events), fixture, command)
    return {
        "state": state,
        "output": output,
        "success": success,
        "evidence": state["realism"]["lastEvidence"],
    }
