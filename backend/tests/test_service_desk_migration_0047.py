import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION_0046 = "0046_archive_unreviewed_examcompass"
REVISION_0047 = "0047_student_service_desk_progression"


def _alembic(database_url: str, *arguments: str) -> None:
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


def _insert_historical_attempts(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "INSERT INTO students(name, email, is_mentor) VALUES (?, ?, 0)",
            ("Migration Learner", "migration.learner@nexus.example"),
        )
        student_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO service_desk_scenarios
                (stable_key, title, category, difficulty, status, created_by)
            VALUES ('migration-case', 'Migration case', 'access', 1, 'active', 'test')
            """
        )
        scenario_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            """
            INSERT INTO service_desk_scenario_versions
                (scenario_id, version_number, definition_json, definition_hash,
                 validation_status, status, published_by)
            VALUES (?, 1, '{}', ?, 'valid', 'published', 'test')
            """,
            (scenario_id, "a" * 64),
        )
        scenario_version_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        for attempt_id, legacy_mode in ((9001, "learning"), (9002, "simulation")):
            state = json.dumps({"attempt": attempt_id, "fixture": "historical"})
            state_hash = hashlib.sha256(state.encode()).hexdigest()
            connection.execute(
                """
                INSERT INTO service_desk_attempts
                    (id, student_id, scenario_version_id, mode, status,
                     current_state, current_state_hash, state_version,
                     attempt_number, score, passed)
                VALUES (?, ?, ?, ?, 'completed', ?, ?, 3, ?, 100, 1)
                """,
                (
                    attempt_id,
                    student_id,
                    scenario_version_id,
                    legacy_mode,
                    state,
                    state_hash,
                    attempt_id - 9000,
                ),
            )
            connection.execute(
                """
                INSERT INTO service_desk_attempt_events
                    (attempt_id, sequence_number, idempotency_key, event_type,
                     tool, payload, previous_state_hash, resulting_state_hash,
                     success, trusted)
                VALUES (?, 1, ?, 'ticket.note', 'ticket', '{}', ?, ?, 1, 1)
                """,
                (attempt_id, f"migration-{attempt_id}", state_hash, state_hash),
            )
            connection.execute(
                """
                INSERT INTO service_desk_attempt_grades
                    (attempt_id, scenario_version_id, rubric_version,
                     technical_complete, critical_failure, overall_score,
                     passed, feedback_summary, details)
                VALUES (?, ?, 'migration-v1', 1, 0, 100, 1, 'preserve me', '{}')
                """,
                (attempt_id, scenario_version_id),
            )


def _migration_snapshot(database_path: Path) -> dict[str, object]:
    with sqlite3.connect(database_path) as connection:
        return {
            "attempts": connection.execute(
                "SELECT id, mode, experience_mode, current_state_hash "
                "FROM service_desk_attempts ORDER BY id"
            ).fetchall(),
            "events": connection.execute(
                "SELECT attempt_id, idempotency_key FROM service_desk_attempt_events "
                "ORDER BY attempt_id"
            ).fetchall(),
            "grades": connection.execute(
                "SELECT attempt_id, feedback_summary FROM service_desk_attempt_grades "
                "ORDER BY attempt_id"
            ).fetchall(),
            "duplicate_hashes": connection.execute(
                """
                SELECT count(*) FROM (
                    SELECT scenario_id, definition_hash, count(*) AS copies
                    FROM service_desk_scenario_versions
                    GROUP BY scenario_id, definition_hash HAVING copies > 1
                )
                """
            ).fetchone()[0],
            "duplicate_assignments": connection.execute(
                """
                SELECT count(*) FROM (
                    SELECT student_id, scenario_id, mode, count(*) AS copies
                    FROM service_desk_assignments
                    GROUP BY student_id, scenario_id, mode HAVING copies > 1
                )
                """
            ).fetchone()[0],
            "foreign_key_errors": connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall(),
            "integrity": connection.execute("PRAGMA integrity_check").fetchone()[0],
        }


def test_0047_preserves_historical_rows_and_rehearses_downgrade(tmp_path):
    database_path = tmp_path / "production-like-0046.db"
    database_url = f"sqlite:///{database_path}"
    _alembic(database_url, "upgrade", REVISION_0046)
    _insert_historical_attempts(database_path)

    _alembic(database_url, "upgrade", REVISION_0047)
    upgraded = _migration_snapshot(database_path)
    assert [(row[0], row[1], row[2]) for row in upgraded["attempts"]] == [
        (9001, "learning", "guided"),
        (9002, "simulation", "assessment"),
    ]
    assert len(upgraded["events"]) == 2
    assert len(upgraded["grades"]) == 2
    assert upgraded["duplicate_hashes"] == 0
    assert upgraded["duplicate_assignments"] == 0
    assert upgraded["foreign_key_errors"] == []
    assert upgraded["integrity"] == "ok"

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE service_desk_attempts SET experience_mode='invalid' WHERE id=9001"
            )

    _alembic(database_url, "downgrade", REVISION_0046)
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(service_desk_attempts)")
        }
        assert "experience_mode" not in columns
        assert (
            connection.execute("SELECT count(*) FROM service_desk_attempts").fetchone()[
                0
            ]
            == 2
        )

    _alembic(database_url, "upgrade", REVISION_0047)
    assert _migration_snapshot(database_path) == upgraded
