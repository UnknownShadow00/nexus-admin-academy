#!/usr/bin/env python3
"""Validate the grading-worker systemd artifacts before anyone installs them.

Read-only and unprivileged. It **never** copies, installs, enables, starts, or
reloads anything — it only checks that the units under ``deploy/systemd/``
would work on this host, so a failed install is discovered here rather than at
cutover.

    ./.venv/bin/python ../scripts/check_grading_worker_install.py
    ./.venv/bin/python ../scripts/check_grading_worker_install.py --json

The actual install commands are documented in ``docs/DEPLOYMENT.md`` under
"Grading worker installation" and are deliberately not executed here.

Exit status is 1 if any check FAILs. WARNs never fail the run — running
unprivileged legitimately hides some things.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import sys

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
SYSTEMD_DIR = os.path.join(REPO_ROOT, "deploy", "systemd")
SERVICE_UNIT = "nexus-grading-worker.service"
TIMER_UNIT = "nexus-grading-worker.timer"
BACKEND_SERVICE = "nexus-admin-academy.service"

#: A pilot expects the queue drained every couple of minutes.
MAX_REASONABLE_INTERVAL_SECONDS = 15 * 60

_ESCAPE = re.compile(r"\\x([0-9a-fA-F]{2})")
_INTERVAL = re.compile(
    r"(\d+(?:\.\d+)?)\s*(us|ms|s|sec|seconds?|m|min|minutes?|h|hr|hours?|d|days?|w|weeks?)?"
)
_UNIT_SECONDS = {
    None: 1,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1,
    "sec": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "w": 604800,
    "week": 604800,
    "weeks": 604800,
}


def decode_systemd_escapes(value: str) -> str:
    r"""Decode systemd's ``\x20`` style escapes.

    The repository path contains spaces, so every path in these units is
    escaped. A checker that compares the raw string against the filesystem
    would report every path as missing.
    """
    return _ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), value or "")


def parse_unit(path: str) -> configparser.ConfigParser:
    """Parse a systemd unit file.

    systemd permits repeated keys and bare values, neither of which
    ``configparser`` accepts by default.
    """
    parser = configparser.ConfigParser(
        strict=False, allow_no_value=True, interpolation=None
    )
    parser.optionxform = str  # systemd keys are case-sensitive
    with open(path, encoding="utf-8") as handle:
        parser.read_file(handle)
    return parser


def parse_unit_text(value: str) -> configparser.ConfigParser:
    """Parse `systemctl cat` output without writing a temporary file."""
    parser = configparser.ConfigParser(
        strict=False, allow_no_value=True, interpolation=None
    )
    parser.optionxform = str
    parser.read_string(value)
    return parser


def parse_interval_seconds(value: str) -> float | None:
    """Parse a systemd time span such as ``2min`` or ``1h 30s`` into seconds."""
    if not value:
        return None
    total = 0.0
    matched = False
    for amount, unit in _INTERVAL.findall(value.strip()):
        key = (unit or "").lower() or None
        if key not in _UNIT_SECONDS:
            return None
        total += float(amount) * _UNIT_SECONDS[key]
        matched = True
    return total if matched else None


def classify_interval(seconds: float | None) -> tuple[str, str]:
    if seconds is None:
        return WARN, "no OnUnitActiveSec — the timer would fire only at boot"
    if seconds > MAX_REASONABLE_INTERVAL_SECONDS:
        return WARN, f"fires every {seconds:.0f}s — slower than a pilot expects"
    return PASS, f"fires every {seconds:.0f}s"


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.rows.append({"name": name, "status": status, "detail": detail})

    @property
    def failed(self) -> bool:
        return any(row["status"] == FAIL for row in self.rows)

    def summary(self) -> dict:
        return {
            status.lower(): sum(1 for row in self.rows if row["status"] == status)
            for status in (PASS, WARN, FAIL, SKIP)
        }


def run_checks() -> Checks:
    checks = Checks()
    service_path = os.path.join(SYSTEMD_DIR, SERVICE_UNIT)
    timer_path = os.path.join(SYSTEMD_DIR, TIMER_UNIT)

    units = {}
    for label, path in (("service", service_path), ("timer", timer_path)):
        if not os.path.isfile(path):
            checks.add(f"{label} unit exists", FAIL, path)
            continue
        try:
            units[label] = parse_unit(path)
            checks.add(f"{label} unit parses", PASS, os.path.basename(path))
        except Exception as exc:
            checks.add(f"{label} unit parses", FAIL, f"{os.path.basename(path)}: {exc}")

    check_systemd_unit_syntax(checks, [service_path, timer_path])

    service = units.get("service")
    timer = units.get("timer")

    if service is not None:
        _check_service(checks, service)
    if timer is not None:
        _check_timer(checks, timer)
    if service is not None:
        _compare_with_backend_unit(checks, service)
        _check_installed_worker(checks, service)
    _check_installed_timer(checks)
    return checks


def check_systemd_unit_syntax(checks: Checks, unit_paths: list[str]) -> None:
    """Ask systemd itself to validate the units when its tooling is present."""
    if shutil.which("systemd-analyze") is None:
        checks.add("systemd unit syntax", SKIP, "systemd-analyze unavailable")
        return
    try:
        result = subprocess.run(
            ["systemd-analyze", "verify", *unit_paths],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        checks.add("systemd unit syntax", WARN, str(exc))
        return
    output = (result.stderr or result.stdout or "").strip().splitlines()
    detail = output[-1] if output else "systemd-analyze verify"
    status = FAIL if result.returncode else WARN if output else PASS
    checks.add("systemd unit syntax", status, detail)


def _check_service(checks: Checks, service: configparser.ConfigParser) -> None:
    for section in ("Unit", "Service"):
        checks.add(
            f"service has [{section}]",
            PASS if service.has_section(section) else FAIL,
        )
    if not service.has_section("Service"):
        return

    missing = [
        key
        for key in (
            "Type",
            "ExecStart",
            "WorkingDirectory",
            "EnvironmentFile",
            "User",
            "Group",
        )
        if not service.get("Service", key, fallback=None)
    ]
    checks.add(
        "service declares the required keys",
        PASS if not missing else FAIL,
        "all present" if not missing else "missing: " + ", ".join(missing),
    )

    workdir = decode_systemd_escapes(
        service.get("Service", "WorkingDirectory", fallback="")
    )
    checks.add(
        "WorkingDirectory exists",
        PASS if workdir and os.path.isdir(workdir) else FAIL,
        workdir or "(unset)",
    )

    env_file = decode_systemd_escapes(
        service.get("Service", "EnvironmentFile", fallback="")
    )
    if not env_file:
        checks.add("EnvironmentFile is set", FAIL, "(unset)")
    elif not os.path.isfile(env_file):
        checks.add("EnvironmentFile exists", FAIL, env_file)
    elif os.access(env_file, os.R_OK):
        # Never read or print its contents — it holds secrets.
        checks.add("EnvironmentFile is readable", PASS, env_file)
    else:
        checks.add(
            "EnvironmentFile is readable",
            WARN,
            f"{env_file} is not readable as {_whoami()} — expected when the "
            "worker runs as another user",
        )

    for raw in _read_write_paths(service):
        path = decode_systemd_escapes(raw)
        checks.add(
            "ReadWritePaths exists",
            PASS if os.path.isdir(path) else FAIL,
            path,
        )

    exec_start = decode_systemd_escapes(
        service.get("Service", "ExecStart", fallback="")
    )
    script = _script_from_exec_start(exec_start)
    interpreter = os.path.join(workdir, ".venv", "bin", "python") if workdir else ""
    checks.add(
        "worker interpreter is executable",
        PASS if interpreter and os.access(interpreter, os.X_OK) else FAIL,
        interpreter or "(no WorkingDirectory)",
    )
    script_path = os.path.join(workdir, script) if workdir and script else ""
    checks.add(
        "worker script exists",
        PASS if script_path and os.path.isfile(script_path) else FAIL,
        script_path or f"could not read a script from ExecStart: {exec_start!r}",
    )

    if (
        interpreter
        and script_path
        and os.access(interpreter, os.X_OK)
        and os.path.isfile(script_path)
    ):
        _import_check(checks, interpreter, workdir, script)
    else:
        checks.add("worker imports cleanly", SKIP, "interpreter or script unavailable")


def _read_write_paths(service: configparser.ConfigParser) -> list[str]:
    raw = service.get("Service", "ReadWritePaths", fallback="")
    return [part for part in raw.split() if part] if raw else []


def _script_from_exec_start(exec_start: str) -> str:
    match = re.search(r"([\w./-]+\.py)", exec_start or "")
    return os.path.basename(match.group(1)) if match else ""


def _import_check(checks: Checks, interpreter: str, workdir: str, script: str) -> None:
    """Import the worker without running it.

    ``process_pending_grades.py`` guards its entry point with
    ``if __name__ == "__main__"``, so importing exercises the dependency graph
    and configuration without processing a single job.
    """
    module = script[:-3] if script.endswith(".py") else script
    try:
        result = subprocess.run(
            [interpreter, "-c", f"import {module}"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        checks.add("worker imports cleanly", FAIL, "import timed out after 60s")
        return
    except OSError as exc:
        checks.add("worker imports cleanly", FAIL, str(exc))
        return
    if result.returncode == 0:
        checks.add("worker imports cleanly", PASS, f"import {module}")
    else:
        tail = (result.stderr or "").strip().splitlines()
        checks.add(
            "worker imports cleanly", FAIL, tail[-1] if tail else "non-zero exit"
        )


def _check_timer(checks: Checks, timer: configparser.ConfigParser) -> None:
    for section in ("Timer", "Install"):
        checks.add(
            f"timer has [{section}]",
            PASS if timer.has_section(section) else FAIL,
        )
    if not timer.has_section("Timer"):
        return

    unit = timer.get("Timer", "Unit", fallback="")
    checks.add(
        "timer names the shipped service",
        PASS if unit == SERVICE_UNIT else FAIL,
        unit or "(unset)",
    )
    if timer.has_section("Install"):
        wanted = timer.get("Install", "WantedBy", fallback="")
        checks.add(
            "timer is installable",
            PASS if "timers.target" in wanted else FAIL,
            wanted or "(no WantedBy)",
        )
    status, detail = classify_interval(
        parse_interval_seconds(timer.get("Timer", "OnUnitActiveSec", fallback=""))
    )
    checks.add("timer interval is sane", status, detail)


def _compare_with_backend_unit(
    checks: Checks, service: configparser.ConfigParser
) -> None:
    """The worker must run as the same user, in the same place, as the API."""
    if shutil.which("systemctl") is None:
        checks.add("matches the live backend unit", SKIP, "systemctl unavailable")
        return
    try:
        result = subprocess.run(
            ["systemctl", "cat", BACKEND_SERVICE],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        checks.add("matches the live backend unit", SKIP, str(exc))
        return
    if result.returncode != 0:
        checks.add(
            "matches the live backend unit", SKIP, f"{BACKEND_SERVICE} not installed"
        )
        return

    live = {}
    for line in result.stdout.splitlines():
        for key in ("User", "Group", "WorkingDirectory"):
            if line.strip().startswith(f"{key}="):
                live[key] = decode_systemd_escapes(line.split("=", 1)[1].strip())

    mismatches = []
    for key, value in live.items():
        ours = decode_systemd_escapes(service.get("Service", key, fallback=""))
        if ours and ours != value:
            mismatches.append(f"{key}: worker={ours!r} backend={value!r}")
    if not live:
        checks.add("matches the live backend unit", SKIP, "no comparable keys found")
    elif mismatches:
        checks.add("matches the live backend unit", WARN, "; ".join(mismatches))
    else:
        checks.add("matches the live backend unit", PASS, ", ".join(sorted(live)))


def _check_installed_timer(checks: Checks) -> None:
    """Report live installation state without enabling or starting anything."""
    if shutil.which("systemctl") is None:
        checks.add("grading timer is installed and enabled", SKIP, "systemctl unavailable")
        checks.add("grading timer is active", SKIP, "systemctl unavailable")
        return
    probes = (
        ("grading timer is installed and enabled", "is-enabled"),
        ("grading timer is active", "is-active"),
    )
    for label, command in probes:
        try:
            result = subprocess.run(
                ["systemctl", command, TIMER_UNIT],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            checks.add(label, WARN, str(exc))
            continue
        detail = (result.stdout or result.stderr or "not installed").strip()
        checks.add(label, PASS if result.returncode == 0 else WARN, detail)


def _check_installed_worker(
    checks: Checks, expected: configparser.ConfigParser
) -> None:
    """Compare the live oneshot unit and prove it has run successfully once."""
    if shutil.which("systemctl") is None:
        checks.add("installed worker unit matches candidate", SKIP, "systemctl unavailable")
        checks.add("grading worker last run succeeded", SKIP, "systemctl unavailable")
        return
    try:
        cat_result = subprocess.run(
            ["systemctl", "cat", SERVICE_UNIT],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        checks.add("installed worker unit matches candidate", WARN, str(exc))
        checks.add("grading worker last run succeeded", WARN, "unit could not be inspected")
        return
    if cat_result.returncode != 0:
        checks.add("installed worker unit matches candidate", WARN, "unit not installed")
        checks.add("grading worker last run succeeded", WARN, "unit not installed")
        return
    try:
        installed = parse_unit_text(cat_result.stdout)
    except (configparser.Error, ValueError) as exc:
        checks.add("installed worker unit matches candidate", WARN, f"could not parse: {exc}")
        checks.add("grading worker last run succeeded", WARN, "unit could not be inspected")
        return

    compared = (
        "User",
        "Group",
        "WorkingDirectory",
        "EnvironmentFile",
        "ExecStart",
        "ReadWritePaths",
    )
    mismatches = []
    for key in compared:
        wanted = decode_systemd_escapes(expected.get("Service", key, fallback="")).strip()
        actual = decode_systemd_escapes(installed.get("Service", key, fallback="")).strip()
        if wanted != actual:
            mismatches.append(key)
    checks.add(
        "installed worker unit matches candidate",
        PASS if not mismatches else WARN,
        "required execution contract matches"
        if not mismatches
        else "mismatched keys: " + ", ".join(mismatches),
    )

    try:
        show_result = subprocess.run(
            [
                "systemctl",
                "show",
                SERVICE_UNIT,
                "--property=Result,ExecMainStatus,ExecMainStartTimestamp",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        checks.add("grading worker last run succeeded", WARN, str(exc))
        return
    properties = dict(
        line.split("=", 1)
        for line in show_result.stdout.splitlines()
        if "=" in line
    )
    ran = bool(properties.get("ExecMainStartTimestamp", "").strip())
    succeeded = (
        show_result.returncode == 0
        and ran
        and properties.get("Result") == "success"
        and properties.get("ExecMainStatus") == "0"
    )
    checks.add(
        "grading worker last run succeeded",
        PASS if succeeded else WARN,
        "result=success, exit=0"
        if succeeded
        else "no successful installed worker execution is recorded",
    )


def _whoami() -> str:
    try:
        import getpass

        return getpass.getuser()
    except Exception:  # pragma: no cover - defensive
        return "this user"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = run_checks()
    if args.json:
        print(
            json.dumps({"checks": checks.rows, "summary": checks.summary()}, indent=2)
        )
    else:
        for row in checks.rows:
            detail = f" — {row['detail']}" if row["detail"] else ""
            print(f"[{row['status']:<4}] {row['name']}{detail}")
        counts = checks.summary()
        print(
            f"\nsummary: {counts['pass']} pass, {counts['warn']} warn, "
            f"{counts['fail']} fail, {counts['skip']} skip"
        )
        print(
            "GRADING WORKER INSTALL CHECK " + ("FAILED" if checks.failed else "PASSED")
        )
        print(
            "\nThis check installs nothing. See docs/DEPLOYMENT.md for the install steps."
        )
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())
