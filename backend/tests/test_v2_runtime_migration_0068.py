"""Disposable SQLite rehearsals for the additive V2 runtime migration."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "0067_v2_question_objectives"
RUNTIME_REVISION = "0068_v2_runtime_stabilization"
RECONCILED_HEAD = "0069_merge_v2_beginner_heads"


def _alembic(database_url: str, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments], cwd=BACKEND_ROOT,
        env=environment, capture_output=True, check=True, text=True,
    )


def _assert_head(database_path: Path, expected_revision: str) -> None:
    with sqlite3.connect(database_path) as connection:
        revisions = connection.execute("SELECT version_num FROM alembic_version").fetchall()
        assert revisions == [(expected_revision,)]
        attempt_columns = {row[1] for row in connection.execute("PRAGMA table_info(v2_assessment_attempts)")}
        grading_columns = {row[1] for row in connection.execute("PRAGMA table_info(pending_grades)")}
        assert {"student_id", "assessment_id", "attempt_number", "grading_state", "score", "passed"} <= attempt_columns
        assert {"claimed_at", "claim_token"} <= grading_columns
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_fresh_database_upgrades_to_runtime_head(tmp_path):
    database_path = tmp_path / "fresh-v2-runtime.db"
    _alembic(f"sqlite:///{database_path}", "upgrade", "head")
    _assert_head(database_path, RECONCILED_HEAD)


def test_pre_0068_v2_database_upgrades_without_losing_rows(tmp_path):
    database_path = tmp_path / "pre-0068-v2.db"
    database_url = f"sqlite:///{database_path}"
    _alembic(database_url, "upgrade", PREVIOUS)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO students(name, email, is_mentor) VALUES ('Existing V2 Student', 'pre68@test.local', 0)"
        )
        before = connection.execute("SELECT count(*) FROM students").fetchone()[0]
    _alembic(database_url, "upgrade", RUNTIME_REVISION)
    _assert_head(database_path, RUNTIME_REVISION)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT count(*) FROM students").fetchone()[0] == before


def test_live_0064_lineage_reconciles_both_heads_without_losing_students(tmp_path):
    database_path = tmp_path / "pre-reconciliation.db"
    database_url = f"sqlite:///{database_path}"
    _alembic(database_url, "upgrade", "0064_v2_ai_grading_infrastructure")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO students(name, email, is_mentor) "
            "VALUES ('Existing Production Student', 'production@test.local', 0)"
        )
        student_id = connection.execute(
            "SELECT id FROM students WHERE email = 'production@test.local'"
        ).fetchone()[0]

    _alembic(database_url, "upgrade", "head")
    _assert_head(database_path, RECONCILED_HEAD)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT id FROM students WHERE email = 'production@test.local'"
        ).fetchone() == (student_id,)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "v2_module_activity",
            "v2_explain_submissions",
            "question_objectives",
            "v2_assessment_attempts",
            "v2_assessment_attempt_questions",
        } <= tables
