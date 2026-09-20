"""Unit coverage for the reusable logic inside the operator scripts.

Only the parts with real decisions are tested — systemd escape decoding, unit
parsing, timer intervals, the preflight's report aggregation, and its URL
classifier. Shell formatting is not worth pinning.
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest
import urllib.error
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

SCRIPTS = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
)


def _load(name):
    """Import a script by path — ``scripts/`` is not an importable package."""
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(SCRIPTS, f"{name}.py")
    )
    module = importlib.util.module_from_spec(spec)
    # Register before executing: @dataclass resolves its own module through
    # sys.modules, and fails on a module that is not there yet.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


worker = _load("check_grading_worker_install")
preflight = _load("v2_pilot_preflight")


# --------------------------------------------------------------------------- #
# systemd escape decoding
# --------------------------------------------------------------------------- #


def test_systemd_space_escapes_are_decoded():
    """The repo path has spaces, so every path in the units is escaped."""
    raw = "/opt/apps/IT\\x20TRAINING\\x20PROJECT\\x20CODE/projects/nexus/backend"
    assert worker.decode_systemd_escapes(raw) == (
        "/opt/apps/IT TRAINING PROJECT CODE/projects/nexus/backend"
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", ""),
        (None, ""),
        ("/plain/path", "/plain/path"),
        ("a\\x2Db", "a-b"),
        ("\\x41\\x42", "AB"),
    ],
)
def test_escape_decoding_edge_cases(value, expected):
    assert worker.decode_systemd_escapes(value) == expected


# --------------------------------------------------------------------------- #
# Unit-file parsing
# --------------------------------------------------------------------------- #


def test_unit_parsing_tolerates_duplicate_keys(tmp_path):
    """systemd allows a key to repeat; configparser does not by default."""
    unit = tmp_path / "x.service"
    unit.write_text(
        textwrap.dedent("""
        [Service]
        ExecStart=/bin/true
        ExecStart=/bin/false
        NoNewPrivileges=true
    """).strip(),
        encoding="utf-8",
    )
    parsed = worker.parse_unit(str(unit))
    assert parsed.get("Service", "ExecStart") == "/bin/false"


def test_unit_parsing_keeps_keys_case_sensitive(tmp_path):
    unit = tmp_path / "x.service"
    unit.write_text("[Service]\nWorkingDirectory=/tmp\n", encoding="utf-8")
    parsed = worker.parse_unit(str(unit))
    assert parsed.get("Service", "WorkingDirectory") == "/tmp"
    assert parsed.get("Service", "workingdirectory", fallback=None) is None


def test_the_shipped_units_parse():
    for name in (worker.SERVICE_UNIT, worker.TIMER_UNIT):
        parsed = worker.parse_unit(os.path.join(worker.SYSTEMD_DIR, name))
        assert parsed.sections()


# --------------------------------------------------------------------------- #
# Timer intervals
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value,seconds",
    [
        ("2min", 120),
        ("120", 120),
        ("120s", 120),
        ("1h", 3600),
        ("1h 30s", 3630),
        ("15min", 900),
        ("1d", 86400),
    ],
)
def test_interval_parsing(value, seconds):
    assert worker.parse_interval_seconds(value) == pytest.approx(seconds)


@pytest.mark.parametrize("value", ["", None, "soon", "every tuesday"])
def test_unparseable_intervals_return_none(value):
    assert worker.parse_interval_seconds(value) is None


def test_a_missing_interval_warns_rather_than_failing():
    status, detail = worker.classify_interval(None)
    assert status == worker.WARN
    assert "only at boot" in detail


def test_a_slow_interval_warns():
    status, _ = worker.classify_interval(3600)
    assert status == worker.WARN


def test_a_two_minute_interval_passes():
    status, detail = worker.classify_interval(120)
    assert status == worker.PASS
    assert "120s" in detail


# --------------------------------------------------------------------------- #
# Preflight reporting
# --------------------------------------------------------------------------- #


def test_a_single_fail_fails_the_report():
    report = preflight.Report()
    report.add("S", "ok", preflight.PASS)
    report.add("S", "warned", preflight.WARN)
    assert report.failed is False
    report.add("S", "broken", preflight.FAIL, "why")
    assert report.failed is True
    assert "V2 PILOT PREFLIGHT FAILED" in report.render()


def test_warnings_alone_still_pass():
    report = preflight.Report()
    report.add("S", "warned", preflight.WARN)
    report.add("S", "skipped", preflight.SKIP)
    assert report.failed is False
    assert "V2 PILOT PREFLIGHT PASSED" in report.render()


def test_production_candidate_requires_v1_visibility_baseline(db):
    report = preflight.Report()
    preflight.check_v1_safety(report, db, None, require_baseline=True)
    assert report.failed is True
    assert report.checks[-1]["status"] == preflight.FAIL
    assert "--compare-baseline" in report.checks[-1]["detail"]


def test_report_counts_every_status():
    report = preflight.Report()
    for status in (
        preflight.PASS,
        preflight.PASS,
        preflight.WARN,
        preflight.FAIL,
        preflight.SKIP,
    ):
        report.add("S", "n", status)
    counts = report.counts
    assert (counts[preflight.PASS], counts[preflight.WARN]) == (2, 1)
    assert (counts[preflight.FAIL], counts[preflight.SKIP]) == (1, 1)


def test_database_passwords_are_never_printed():
    redacted = preflight._redact("postgresql://nexus:hunter2@db.internal/nexus")
    assert "hunter2" not in redacted
    assert "***" in redacted


def test_redaction_leaves_a_sqlite_path_alone():
    assert preflight._redact("sqlite:///./nexus.db") == "sqlite:///./nexus.db"


def test_preflight_opens_an_explicit_sqlite_database_read_only(tmp_path):
    path = tmp_path / "pilot-copy.db"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE marker (id INTEGER PRIMARY KEY)"))
    engine.dispose()

    session, _ = preflight.build_session(f"sqlite:///{path}")
    try:
        assert session.execute(text("SELECT COUNT(*) FROM marker")).scalar() == 0
        with pytest.raises(OperationalError):
            session.execute(text("CREATE TABLE forbidden (id INTEGER)"))
    finally:
        session.rollback()
        session.close()


def test_worker_uses_systemd_analyze_when_available(monkeypatch):
    calls = []

    monkeypatch.setattr(worker.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    checks = worker.Checks()
    worker.check_systemd_unit_syntax(
        checks,
        [os.path.join(worker.SYSTEMD_DIR, worker.SERVICE_UNIT)],
    )

    assert calls[0][0][0] == "systemd-analyze"
    assert calls[0][0][1] == "verify"
    assert checks.rows[-1]["status"] == worker.PASS


def test_systemd_analyze_diagnostics_are_not_hidden(monkeypatch):
    monkeypatch.setattr(worker.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        worker.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, "", "dependency unit has a warning"
        ),
    )
    checks = worker.Checks()

    worker.check_systemd_unit_syntax(checks, ["fixture.service"])

    assert checks.rows[-1]["status"] == worker.WARN
    assert "warning" in checks.rows[-1]["detail"]


def test_live_worker_unit_and_last_success_are_verified(monkeypatch):
    expected = worker.parse_unit(
        os.path.join(worker.SYSTEMD_DIR, worker.SERVICE_UNIT)
    )
    with open(
        os.path.join(worker.SYSTEMD_DIR, worker.SERVICE_UNIT), encoding="utf-8"
    ) as handle:
        unit_text = handle.read()
    monkeypatch.setattr(worker.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(command, **kwargs):
        if command[1] == "cat":
            return subprocess.CompletedProcess(command, 0, unit_text, "")
        assert command[1] == "show"
        return subprocess.CompletedProcess(
            command,
            0,
            "Result=success\nExecMainStatus=0\nExecMainStartTimestamp=Sat 2026-09-05 10:00:00 UTC\n",
            "",
        )

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    checks = worker.Checks()
    worker._check_installed_worker(checks, expected)
    assert [row["status"] for row in checks.rows] == [worker.PASS, worker.PASS]


def test_stale_or_never_run_live_worker_warns(monkeypatch):
    expected = worker.parse_unit(
        os.path.join(worker.SYSTEMD_DIR, worker.SERVICE_UNIT)
    )
    stale = "[Service]\nUser=nexus\nExecStart=/bin/false\n"
    monkeypatch.setattr(worker.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(command, **kwargs):
        if command[1] == "cat":
            return subprocess.CompletedProcess(command, 0, stale, "")
        return subprocess.CompletedProcess(
            command, 0, "Result=success\nExecMainStatus=0\nExecMainStartTimestamp=\n", ""
        )

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    checks = worker.Checks()
    worker._check_installed_worker(checks, expected)
    assert [row["status"] for row in checks.rows] == [worker.WARN, worker.WARN]


def test_pilot_status_is_read_only_and_counts_unique_valid_students(tmp_path):
    env_file = tmp_path / "pilot.env"
    env_file.write_text(
        "V2_CURRICULUM_ENABLED=true\nV2_PILOT_STUDENT_IDS=3; 3 7 bad 0 -1\n",
        encoding="utf-8",
    )
    missing_db = tmp_path / "missing.db"
    result = subprocess.run(
        [os.path.join(SCRIPTS, "pilot_status.sh"), "--db", str(missing_db), "--json"],
        env={
            **os.environ,
            "NEXUS_ENV_FILE": str(env_file),
            "NEXUS_BACKEND_URL": "http://127.0.0.1:1",
            "NEXUS_FRONTEND_URL": "http://127.0.0.1:1",
            "NEXUS_SERVICE_DESK_URL": "http://127.0.0.1:1",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    payload = json.loads(result.stdout)
    rows = {row["name"]: row for row in payload["rows"]}
    assert rows["database"]["status"] == "SKIP"
    assert rows["pilot students enrolled"]["detail"] == "2"


def test_pilot_status_warns_for_backend_staging_and_service_desk_wildcards(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_ss = fake_bin / "ss"
    fake_ss.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' "
        "'LISTEN 0 128 0.0.0.0:8000' "
        "'LISTEN 0 128 [::]:18000' "
        "'LISTEN 0 128 *:3000'\n",
        encoding="utf-8",
    )
    fake_ss.chmod(0o755)
    missing_db = tmp_path / "missing.db"
    result = subprocess.run(
        [os.path.join(SCRIPTS, "pilot_status.sh"), "--db", str(missing_db), "--json"],
        env={
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "NEXUS_ENV_FILE": str(tmp_path / "missing.env"),
            "NEXUS_BACKEND_URL": "http://127.0.0.1:1",
            "NEXUS_FRONTEND_URL": "http://127.0.0.1:1",
            "NEXUS_SERVICE_DESK_URL": "http://127.0.0.1:1",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    rows = {row["name"]: row for row in json.loads(result.stdout)["rows"]}
    assert rows["backend network exposure"]["status"] == "WARN"
    assert rows["staging/bypass exposure"]["status"] == "WARN"
    assert "18000" in rows["staging/bypass exposure"]["detail"]
    assert "3000" in rows["staging/bypass exposure"]["detail"]


def test_cutover_snapshot_defaults_to_a_non_retained_dry_run(tmp_path):
    database = tmp_path / "pilot.db"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('0068_test')"))
    engine.dispose()
    destination = tmp_path / "backups"

    result = subprocess.run(
        [
            os.path.join(SCRIPTS, "make_cutover_snapshot.sh"),
            "--db",
            str(database),
            "--dest",
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    assert "v2-cutover-0068_test" in result.stdout
    assert "Nothing was written" in result.stdout
    assert not destination.exists()


def test_cutover_snapshot_rejects_a_path_traversal_label(tmp_path):
    database = tmp_path / "pilot.db"
    database.touch()

    result = subprocess.run(
        [
            os.path.join(SCRIPTS, "make_cutover_snapshot.sh"),
            "--db",
            str(database),
            "--dest",
            str(tmp_path / "backups"),
            "--label",
            "../outside",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "label must contain only" in result.stderr
    assert not (tmp_path / "outside").exists()


def test_preflight_reports_all_ten_current_scenarios_as_evidence_based(db):
    from seed import seed_service_desk_scenarios

    seed_service_desk_scenarios(db)
    db.commit()
    report = preflight.Report()

    preflight.check_service_desk(report, db)

    realism = next(row for row in report.checks if row["name"] == "scenario realism")
    assert realism["status"] == preflight.PASS
    assert "10/10" in realism["detail"]


def test_preflight_fails_when_an_obsolete_scenario_version_is_also_published(db):
    from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
    from seed import seed_service_desk_scenarios

    seed_service_desk_scenarios(db)
    scenario = db.query(ServiceDeskScenario).filter_by(stable_key="inc2501").one()
    current = db.query(ServiceDeskScenarioVersion).filter_by(
        scenario_id=scenario.id, status="published"
    ).one()
    db.add(ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=current.version_number + 1,
        definition_json={"slug": "inc2501", "simulation_fixture": "retired-wizard"},
        definition_hash="f" * 64,
        validation_status="valid",
        status="published",
    ))
    db.commit()
    report = preflight.Report()

    preflight.check_service_desk(report, db)

    check = next(
        row for row in report.checks
        if row["name"] == "curriculum scenarios resolve only to the current realistic version"
    )
    assert check["status"] == preflight.FAIL
    assert "INC2501" in check["detail"]


def test_preflight_fails_when_a_required_realistic_scenario_is_disabled(db):
    from app.models.service_desk import ServiceDeskScenario
    from seed import seed_service_desk_scenarios

    seed_service_desk_scenarios(db)
    scenario = db.query(ServiceDeskScenario).filter_by(stable_key="inc2501").one()
    scenario.status = "disabled"
    db.commit()
    report = preflight.Report()

    preflight.check_service_desk(report, db)

    realism = next(row for row in report.checks if row["name"] == "scenario realism")
    assert realism["status"] == preflight.FAIL
    assert "INC2501" in realism["detail"]


def test_preflight_service_desk_contract_guard_passes_and_fails_closed(monkeypatch):
    report = preflight.Report()
    preflight.check_service_desk_contract(report)
    assert report.checks[-1]["status"] == preflight.PASS

    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: io.StringIO(
        "export const EXPECTED_NEXUS_SERVICE_DESK_CONTRACT = '1.0' as const;"
    ))
    mismatch = preflight.Report()
    preflight.check_service_desk_contract(mismatch)
    assert mismatch.checks[-1]["status"] == preflight.FAIL
    assert mismatch.checks[-1]["detail"] == "version mismatch"


def test_dead_required_link_is_a_failure(monkeypatch):
    class DeadOpener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)

    monkeypatch.setattr("urllib.request.build_opener", lambda *_: DeadOpener())
    status, detail = preflight._probe("https://example.invalid/dead", 0.1)
    assert status == preflight.FAIL
    assert "HTTP 404" in detail


def test_required_link_follows_redirect_and_records_final_destination(monkeypatch):
    class Response:
        status = 200

        def geturl(self):
            return "https://example.invalid/current"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class RedirectingOpener:
        def open(self, request, timeout):
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *_: RedirectingOpener())
    status, detail = preflight._probe("https://example.invalid/old", 0.1)
    assert status == preflight.PASS
    assert "final https://example.invalid/current" in detail


def test_preflight_surfaces_grading_worker_operational_warning():
    report = preflight.Report()
    checks = SimpleNamespace(rows=[{
        "name": "installed timer is enabled",
        "status": worker.WARN,
        "detail": "not installed",
    }])

    preflight.check_grading_worker_artifacts(report, checks=checks)

    assert report.checks[-1]["status"] == preflight.WARN
    assert "installed timer is enabled" in report.checks[-1]["detail"]

    candidate = preflight.Report()
    preflight.check_grading_worker_artifacts(
        candidate, checks=checks, require_installed=True
    )
    assert candidate.checks[-1]["status"] == preflight.FAIL
