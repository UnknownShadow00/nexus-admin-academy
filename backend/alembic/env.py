from logging.config import fileConfig
import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Ensure "app" package imports resolve when running Alembic from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import load_env
from app.database import Base, normalize_database_url
from app.models import *  # noqa: F401,F403

config = context.config
load_env()
env_database_url = normalize_database_url(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else None
if env_database_url:
    config.set_main_option("sqlalchemy.url", env_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# Alembic hardcodes alembic_version.version_num as VARCHAR(32)
# (ddl/impl.py version_table_impl) with no supported config knob to widen
# it. Several revision ids in this project's history are longer than that
# (e.g. "0034_service_desk_scenario_foundation" is 37 chars) — SQLite never
# enforces declared column length so this went unnoticed there, but a fresh
# Postgres database rejects the INSERT/UPDATE outright ("value too long for
# type character varying(32)"), which blocks `alembic upgrade head` from
# ever completing against a new Postgres instance. Pre-creating the table
# with a wider column, before Alembic's own lazy CREATE TABLE IF NOT EXISTS
# logic runs, works around this: Alembic only checks that the table exists,
# not its column width. This is a no-op against the existing production
# SQLite database, which already has this table.
def _ensure_wide_version_table(connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    # Run this setup in its own transaction so Alembic starts with a clean
    # connection-level transaction state. In particular, doing this on SQLite
    # caused the fresh-database migration DDL to be rolled back on connection
    # close even though Alembic reported every revision as applied.
    with connection.begin():
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version ("
                "version_num VARCHAR(64) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                ")"
            )
        )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_wide_version_table(connection)
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
