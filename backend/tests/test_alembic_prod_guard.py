"""Production-migration safety guard (added after the 2026-08-29 incident).

A bare `alembic upgrade head` (no explicit scratch DATABASE_URL, no opt-in)
must not be able to migrate the live production database. See
`backend/app/db_guard.py` and `tasks/lessons.md`.

The subprocess cases below are safe: production is already at head, so even a
hypothetical bypass of `upgrade head` would be a no-op, and every case also
asserts the production file's mtime is unchanged.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.db_guard import (
    PROD_OPT_IN_ENV,
    ProductionMigrationBlocked,
    assert_migration_allowed,
    production_sqlite_path,
    resolves_to_production,
    sqlite_path_from_url,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROD_DB = production_sqlite_path()
PROD_URL = f"sqlite:///{PROD_DB}"


# --------------------------------------------------------------------------- #
# URL resolution
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "url,is_prod",
    [
        ("sqlite:///./nexus.db", True),                       # the alembic.ini value
        (f"sqlite:///{PROD_DB}", True),                       # absolute prod path
        ("sqlite:///nexus.db", True),                         # bare relative -> backend/
        ("sqlite:////tmp/nexus-scratch.db", False),           # explicit scratch
        ("sqlite:////home/runner/work/_temp/nexus-ci.db", False),  # CI runner.temp
        ("sqlite:///:memory:", False),
        ("postgresql+psycopg://u:p@localhost/nexus", False),
        ("", False),
        (None, False),
    ],
)
def test_resolves_to_production(url, is_prod):
    assert resolves_to_production(url) is is_prod


def test_sqlite_path_from_url_matches_app_database_resolution():
    # app/database.py turns "sqlite:///./nexus.db" into backend/nexus.db
    assert sqlite_path_from_url("sqlite:///./nexus.db") == PROD_DB
    assert sqlite_path_from_url("sqlite:///:memory:") is None
    assert sqlite_path_from_url("postgresql://x/y") is None


# --------------------------------------------------------------------------- #
# assert_migration_allowed
# --------------------------------------------------------------------------- #

def test_bare_production_resolution_is_blocked():
    with pytest.raises(ProductionMigrationBlocked) as exc:
        assert_migration_allowed(
            effective_url=PROD_URL, database_url_was_set=False, allow_prod=False
        )
    msg = str(exc.value)
    assert "BLOCKED" in msg
    assert PROD_OPT_IN_ENV in msg          # tells the operator how to opt in
    assert "throwaway" in msg              # tells them how to use a scratch DB


def test_explicit_production_without_optin_is_blocked():
    with pytest.raises(ProductionMigrationBlocked):
        assert_migration_allowed(
            effective_url=PROD_URL, database_url_was_set=True, allow_prod=False
        )


def test_explicit_optin_permits_production():
    assert (
        assert_migration_allowed(
            effective_url=PROD_URL, database_url_was_set=True, allow_prod=True
        )
        == PROD_URL
    )


def test_scratch_database_is_always_allowed():
    url = "sqlite:////tmp/nexus-scratch.db"
    assert assert_migration_allowed(
        effective_url=url, database_url_was_set=True, allow_prod=False
    ) == url


@pytest.mark.parametrize("value,allowed", [("1", True), ("true", True), ("on", True),
                                           ("0", False), ("", False), ("no", False)])
def test_optin_env_var_is_read(monkeypatch, value, allowed):
    monkeypatch.setenv(PROD_OPT_IN_ENV, value)
    if allowed:
        assert assert_migration_allowed(effective_url=PROD_URL, database_url_was_set=True) == PROD_URL
    else:
        with pytest.raises(ProductionMigrationBlocked):
            assert_migration_allowed(effective_url=PROD_URL, database_url_was_set=True)


def test_optin_env_var_absent_blocks(monkeypatch):
    monkeypatch.delenv(PROD_OPT_IN_ENV, raising=False)
    with pytest.raises(ProductionMigrationBlocked):
        assert_migration_allowed(effective_url=PROD_URL, database_url_was_set=True)


# --------------------------------------------------------------------------- #
# End-to-end via the real `alembic` CLI (production untouched throughout)
# --------------------------------------------------------------------------- #

def _run_alembic(args, env_overrides, remove=()):
    env = {k: v for k, v in os.environ.items() if k not in remove}
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cli_bare_upgrade_is_refused_and_leaves_production_untouched():
    before = PROD_DB.stat().st_mtime_ns
    proc = _run_alembic(
        ["upgrade", "head"],
        env_overrides={},
        remove=("DATABASE_URL", PROD_OPT_IN_ENV),  # simulate a bare invocation
    )
    assert proc.returncode != 0
    assert "BLOCKED" in (proc.stderr + proc.stdout)
    assert PROD_DB.stat().st_mtime_ns == before      # not written


def test_cli_readonly_current_still_works_without_optin():
    proc = _run_alembic(["current"], env_overrides={}, remove=("DATABASE_URL", PROD_OPT_IN_ENV))
    assert proc.returncode == 0
    assert "0064_v2_ai_grading_infrastructure" in (proc.stdout + proc.stderr)


def test_cli_scratch_database_upgrade_and_downgrade(tmp_path):
    scratch = tmp_path / "ci-like.db"
    url = f"sqlite:///{scratch}"
    before = PROD_DB.stat().st_mtime_ns

    up = _run_alembic(["upgrade", "head"], env_overrides={"DATABASE_URL": url},
                      remove=(PROD_OPT_IN_ENV,))
    assert up.returncode == 0, up.stderr
    assert scratch.exists()

    cur = _run_alembic(["current"], env_overrides={"DATABASE_URL": url})
    heads = _run_alembic(["heads"], env_overrides={"DATABASE_URL": url})
    head_rev = heads.stdout.split()[0]
    assert head_rev and head_rev in cur.stdout  # scratch DB migrated to head

    down = _run_alembic(["downgrade", "0063_v2_content_and_assessment"],
                        env_overrides={"DATABASE_URL": url})
    assert down.returncode == 0, down.stderr
    reup = _run_alembic(["upgrade", "head"], env_overrides={"DATABASE_URL": url})
    assert reup.returncode == 0, reup.stderr

    assert PROD_DB.stat().st_mtime_ns == before       # production never touched
