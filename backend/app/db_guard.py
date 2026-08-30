"""Production-migration safety guard for Alembic.

Incident (2026-08-29): a bare ``alembic upgrade head`` with ``DATABASE_URL``
unset fell back to ``alembic.ini`` (``sqlite:///./nexus.db``) and migrated the
live production database. This module makes that impossible without a
deliberate, explicit opt-in.

``alembic/env.py`` calls :func:`assert_migration_allowed` before running any
migration. Read-only inspection commands (``alembic current`` / ``heads`` /
``history``) do not run migrations and are unaffected.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine import make_url

# Set this to a truthy value ("1", "true", "yes", "on") ONLY when you
# genuinely intend the command to migrate the live production database.
PROD_OPT_IN_ENV = "NEXUS_ALLOW_PROD_MIGRATION"

_TRUTHY = {"1", "true", "yes", "on"}


class ProductionMigrationBlocked(RuntimeError):
    """Raised when an Alembic migration would touch production without opt-in."""


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUTHY


def backend_root() -> Path:
    # app/db_guard.py -> backend/
    return Path(__file__).resolve().parents[1]


def production_sqlite_path(root: Path | None = None) -> Path:
    """The one SQLite file the live systemd service uses."""
    return ((root or backend_root()) / "nexus.db").resolve()


def sqlite_path_from_url(url: str | None, root: Path | None = None) -> Path | None:
    """Filesystem path a sqlite URL points at, or None for non-sqlite / memory
    URLs.

    Mirrors the ``sqlite:///./name`` -> ``backend/name`` resolution in
    ``app/database.py`` so the comparison uses the same absolute path.
    """
    if not url:
        return None
    try:
        parsed = make_url(url)
    except Exception:  # noqa: BLE001 - a URL we can't parse can't be production
        return None
    if not parsed.drivername.startswith("sqlite"):
        return None
    database = parsed.database  # e.g. "./nexus.db", "/abs/path.db", ":memory:", None
    if not database or database == ":memory:" or "mode=memory" in url:
        return None
    root = root or backend_root()
    candidate = Path(database)
    if not candidate.is_absolute():
        # app/database.py resolves "./name" (and bare "name") against backend/.
        candidate = root / (database[2:] if database.startswith("./") else database)
    return candidate.resolve()


def resolves_to_production(effective_url: str | None, root: Path | None = None) -> bool:
    path = sqlite_path_from_url(effective_url, root)
    return path is not None and path == production_sqlite_path(root)


def assert_migration_allowed(
    *,
    effective_url: str | None,
    database_url_was_set: bool,
    allow_prod: bool | None = None,
    root: Path | None = None,
) -> str | None:
    """Raise :class:`ProductionMigrationBlocked` if this migration would run
    against the live production database without an explicit opt-in.

    * ``effective_url`` — the URL Alembic actually resolved (post-``env.py``).
    * ``database_url_was_set`` — whether ``DATABASE_URL`` was in the environment
      (used only to make the error message accurate).
    * ``allow_prod`` — opt-in; defaults to reading ``NEXUS_ALLOW_PROD_MIGRATION``.

    Returns ``effective_url`` unchanged when the command is allowed.
    """
    if allow_prod is None:
        allow_prod = _truthy(os.getenv(PROD_OPT_IN_ENV))

    if not resolves_to_production(effective_url, root):
        return effective_url  # scratch / CI / Postgres-dev — always fine
    if allow_prod:
        return effective_url  # deliberate, explicit production migration

    prod_path = production_sqlite_path(root)
    source = (
        "DATABASE_URL in the environment"
        if database_url_was_set
        else "alembic.ini (DATABASE_URL was not set)"
    )
    raise ProductionMigrationBlocked(
        "\n".join(
            [
                "",
                "  ┌─ BLOCKED: Alembic migration would run against PRODUCTION ─┐",
                f"  Resolved database : {effective_url}",
                f"  Production file   : {prod_path}",
                f"  Resolved from     : {source}",
                "",
                "  This command was refused to prevent an accidental production",
                "  schema change (see the 2026-08-29 incident in tasks/lessons.md).",
                "",
                "  • For development / verification, point at a throwaway copy:",
                "      DATABASE_URL='sqlite:////tmp/nexus-scratch.db' \\",
                "        ./.venv/bin/python -m alembic upgrade head",
                "",
                f"  • To migrate PRODUCTION on purpose, set {PROD_OPT_IN_ENV}=1:",
                f"      {PROD_OPT_IN_ENV}=1 DATABASE_URL='sqlite:///{prod_path}' \\",
                "        ./.venv/bin/python -m alembic upgrade head",
                "    (the deploy script does this for you.)",
                "  └──────────────────────────────────────────────────────────┘",
                "",
            ]
        )
    )
