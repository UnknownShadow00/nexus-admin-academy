"""Disposable SQLite rehearsal for Wave 4 legacy assessment state."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "0068_v2_runtime_stabilization"
HEAD = "0069_legacy_assessment_attempts"


def alembic(database_url: str, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )


def test_0069_adds_attempt_resume_columns_without_changing_v2_state(tmp_path):
    database_path = tmp_path / "wave4-migration.db"
    database_url = f"sqlite:///{database_path}"
    alembic(database_url, "upgrade", PREVIOUS)
    alembic(database_url, "upgrade", HEAD)

    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            == HEAD
        )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(quiz_attempts)")
        }
        assert {
            "status",
            "question_snapshot",
            "current_position",
            "revision",
            "submitted_at",
        } <= columns
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
