import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION_BEFORE = "0070_beginner_content_ux_polish"
REVISION = "0071_forced_first_login_password_change"


def _run_alembic(database_url: str, *args: str) -> None:
    environment = os.environ.copy()
    environment.update({
        "DATABASE_URL": database_url,
        "JWT_SECRET_KEY": "migration-test-secret-at-least-32-bytes",
        "JWT_ALGORITHM": "HS256",
    })
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )


def test_existing_students_are_not_forced_during_upgrade(tmp_path):
    database_path = tmp_path / "existing-student.db"
    database_url = f"sqlite:///{database_path}"
    _run_alembic(database_url, "upgrade", REVISION_BEFORE)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO students (name, email, username, password_hash, is_mentor, total_xp) "
            "VALUES (?, ?, ?, ?, 0, 0)",
            ("Existing Student", "existing@test.local", "existing", "hash-not-used"),
        )
        connection.commit()

    _run_alembic(database_url, "upgrade", REVISION)
    with sqlite3.connect(database_path) as connection:
        existing_state_count = connection.execute(
            "SELECT COUNT(*) FROM student_auth_states"
        ).fetchone()[0]
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]

    # No backfill means existing students retain normal access. A row is only
    # created when an administrator creates or resets a managed credential.
    assert existing_state_count == 0
    assert revision == REVISION

    _run_alembic(database_url, "downgrade", REVISION_BEFORE)
    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "student_auth_states" not in tables
