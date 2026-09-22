"""The MFA curriculum card belongs to Week 7, with learner history intact."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION_0072 = "0072_weeks_3_4_prelaunch_quality"
REVISION_0073 = "0073_mfa_week7_curriculum_card"
MFA_STABLE_ID = "week-7-service_desk_scenario-mfa-reset"
LEGACY_STABLE_ID = "week-4-service_desk_scenario-inc2509"


def _run(database_url: str, *args: str) -> None:
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": database_url,
        "JWT_SECRET_KEY": "isolated-mfa-card-test-secret-at-least-32-bytes",
        "JWT_ALGORITHM": "HS256",
        "COOKIE_SECURE": "false",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    subprocess.run(
        [sys.executable, *args], cwd=BACKEND_ROOT, env=env,
        capture_output=True, check=True, text=True,
    )


def _activity_rows(connection: sqlite3.Connection, scenario: str) -> list[tuple]:
    return connection.execute(
        "SELECT a.id, w.week_number, a.stable_id, a.is_required, a.display_order "
        "FROM training_week_activities a JOIN training_weeks w ON w.id = a.training_week_id "
        "WHERE a.activity_type = 'service_desk_scenario' AND a.content_ref = ? "
        "ORDER BY a.id",
        (scenario,),
    ).fetchall()


def test_fresh_seed_puts_mfa_only_in_week_7(tmp_path):
    db_path = tmp_path / "fresh.db"
    url = f"sqlite:///{db_path}"
    _run(url, "-m", "alembic", "upgrade", "head")
    _run(url, "seed.py")
    _run(url, "seed_curriculum.py")

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == REVISION_0073
        assert [(week, stable, required) for _, week, stable, required, _ in _activity_rows(connection, "mfa-reset")] == [
            (7, MFA_STABLE_ID, 0),
        ]
        assert [(week, required) for _, week, _, required, _ in _activity_rows(connection, "password-reset")] == [(6, 1)]
        assert _activity_rows(connection, "inc2504") == []
        assert connection.execute(
            "SELECT COUNT(*) FROM training_week_activities a JOIN training_weeks w "
            "ON w.id = a.training_week_id WHERE w.week_number = 4 "
            "AND a.activity_type = 'service_desk_scenario'"
        ).fetchone()[0] == 0
        assert {row[0] for row in connection.execute(
            "SELECT l.title FROM training_week_activities a JOIN training_weeks w "
            "ON w.id = a.training_week_id JOIN lab_templates l "
            "ON a.content_ref = CAST(l.id AS TEXT) WHERE w.week_number = 4 "
            "AND a.activity_type = 'guided_lab' AND a.is_required = 1"
        )} == {"Prioritize the Queue", "Work the Queue: Three Tickets"}
        assert connection.execute("SELECT MIN(week_number) FROM quizzes WHERE title LIKE 'IPv4 Addressing%'").fetchone()[0] >= 9
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("old_stable_id", [
    LEGACY_STABLE_ID,
    "week-4-service_desk_scenario-mfa-reset",
])
def test_upgrade_moves_only_legacy_card_and_preserves_history_and_custom_work(tmp_path, old_stable_id):
    db_path = tmp_path / "upgrade.db"
    url = f"sqlite:///{db_path}"
    _run(url, "-m", "alembic", "upgrade", REVISION_0072)
    _run(url, "seed.py")
    _run(url, "seed_curriculum.py")

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        week4 = connection.execute("SELECT id FROM training_weeks WHERE week_number = 4").fetchone()[0]
        week7 = connection.execute("SELECT id FROM training_weeks WHERE week_number = 7").fetchone()[0]
        # Include the production legacy identity and the alternate seeded ID.
        connection.execute(
            "DELETE FROM training_week_activities WHERE stable_id IN (?, ?)",
            (MFA_STABLE_ID, "week-4-service_desk_scenario-mfa-reset"),
        )
        order = connection.execute(
            "SELECT COALESCE(MAX(display_order), 0) + 1 FROM training_week_activities WHERE training_week_id = ?",
            (week4,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO training_week_activities "
            "(stable_id, training_week_id, activity_type, content_ref, display_order, "
            "is_required, estimated_minutes, prerequisite_mode, metadata_json) "
            "VALUES (?, ?, 'service_desk_scenario', 'mfa-reset', ?, 0, 30, 'soft', '{}')",
            (old_stable_id, week4, order),
        )
        legacy_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO students (name, email, username, password_hash, total_xp) "
            "VALUES ('Historical learner', 'mfa-history@example.invalid', 'mfa-history', 'preserved-hash', 200)"
        )
        student_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        lesson_id = connection.execute("SELECT MIN(id) FROM lessons").fetchone()[0]
        connection.execute(
            "INSERT INTO student_lesson_progress (student_id, lesson_id, completed_at) "
            "VALUES (?, ?, '2026-09-21 12:00:00')", (student_id, lesson_id),
        )
        scenario_id = connection.execute(
            "SELECT id FROM service_desk_scenarios WHERE stable_key = 'mfa-reset'"
        ).fetchone()[0]
        version_id = connection.execute(
            "SELECT id FROM service_desk_scenario_versions WHERE scenario_id = ? "
            "AND status = 'published' ORDER BY version_number DESC LIMIT 1", (scenario_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO service_desk_assignments "
            "(student_id, scenario_id, mode, is_required, assigned_by) "
            "VALUES (?, ?, 'simulation', 0, 'instructor-custom')", (student_id, scenario_id),
        )
        assignment_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO service_desk_attempts "
            "(student_id, scenario_version_id, mode, status, current_state, current_state_hash, "
            "state_version, attempt_number, score, passed, experience_mode) "
            "VALUES (?, ?, 'simulation', 'completed', '{}', ?, 1, 1, 91, 1, 'assessment')",
            (student_id, version_id, "a" * 64),
        )
        attempt_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        custom_order = order + 1
        connection.execute(
            "INSERT INTO training_week_activities "
            "(stable_id, training_week_id, activity_type, content_ref, display_order, "
            "is_required, estimated_minutes, prerequisite_mode, metadata_json) "
            "VALUES ('instructor-week4-case', ?, 'service_desk_scenario', 'inc2502', ?, 0, 77, 'soft', '{}')",
            (week4, custom_order),
        )
        connection.commit()
        before = {
            "student": connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone(),
            "lesson": connection.execute("SELECT * FROM student_lesson_progress WHERE student_id = ?", (student_id,)).fetchall(),
            "assignment": connection.execute("SELECT * FROM service_desk_assignments WHERE id = ?", (assignment_id,)).fetchone(),
            "attempt": connection.execute("SELECT * FROM service_desk_attempts WHERE id = ?", (attempt_id,)).fetchone(),
            "scenario": connection.execute("SELECT * FROM service_desk_scenarios WHERE id = ?", (scenario_id,)).fetchone(),
            "version": connection.execute("SELECT * FROM service_desk_scenario_versions WHERE id = ?", (version_id,)).fetchone(),
            "custom": connection.execute("SELECT * FROM training_week_activities WHERE stable_id = 'instructor-week4-case'").fetchone(),
        }

    _run(url, "-m", "alembic", "upgrade", REVISION_0073)
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == REVISION_0073
        assert _activity_rows(connection, "mfa-reset") == [
            (legacy_id, 7, MFA_STABLE_ID, 0, connection.execute(
                "SELECT display_order FROM training_week_activities WHERE id = ?", (legacy_id,)
            ).fetchone()[0]),
        ]
        assert connection.execute("SELECT training_week_id FROM training_week_activities WHERE id = ?", (legacy_id,)).fetchone()[0] == week7
        after = {
            "student": connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone(),
            "lesson": connection.execute("SELECT * FROM student_lesson_progress WHERE student_id = ?", (student_id,)).fetchall(),
            "assignment": connection.execute("SELECT * FROM service_desk_assignments WHERE id = ?", (assignment_id,)).fetchone(),
            "attempt": connection.execute("SELECT * FROM service_desk_attempts WHERE id = ?", (attempt_id,)).fetchone(),
            "scenario": connection.execute("SELECT * FROM service_desk_scenarios WHERE id = ?", (scenario_id,)).fetchone(),
            "version": connection.execute("SELECT * FROM service_desk_scenario_versions WHERE id = ?", (version_id,)).fetchone(),
            "custom": connection.execute("SELECT * FROM training_week_activities WHERE stable_id = 'instructor-week4-case'").fetchone(),
        }
        assert after == before
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    # Seed replay must not recreate the Week 4 card or duplicate Week 7 MFA.
    _run(url, "seed_curriculum.py")
    with sqlite3.connect(db_path) as connection:
        assert len(_activity_rows(connection, "mfa-reset")) == 1
        assert _activity_rows(connection, "mfa-reset")[0][:4] == (legacy_id, 7, MFA_STABLE_ID, 0)
        assert connection.execute(
            "SELECT id, stable_id, content_ref, is_required, estimated_minutes "
            "FROM training_week_activities WHERE stable_id = 'instructor-week4-case'"
        ).fetchone() == (before["custom"][0], "instructor-week4-case", "inc2502", 0, 77)


def test_upgrade_fails_closed_when_instructor_week7_mfa_would_duplicate_seeded_card(tmp_path):
    db_path = tmp_path / "custom-week7.db"
    url = f"sqlite:///{db_path}"
    _run(url, "-m", "alembic", "upgrade", REVISION_0072)
    _run(url, "seed.py")
    _run(url, "seed_curriculum.py")
    with sqlite3.connect(db_path) as connection:
        week7 = connection.execute(
            "SELECT id FROM training_weeks WHERE week_number = 7"
        ).fetchone()[0]
        order = connection.execute(
            "SELECT COALESCE(MAX(display_order), 0) + 1 FROM training_week_activities "
            "WHERE training_week_id = ?", (week7,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO training_week_activities "
            "(stable_id, training_week_id, activity_type, content_ref, display_order, "
            "is_required, estimated_minutes, prerequisite_mode, metadata_json) "
            "VALUES ('instructor-week7-mfa', ?, 'service_desk_scenario', 'mfa-reset', "
            "?, 0, 45, 'soft', '{}')", (week7, order),
        )
        connection.commit()
        before = connection.execute(
            "SELECT * FROM training_week_activities WHERE content_ref = 'mfa-reset' "
            "AND activity_type = 'service_desk_scenario' ORDER BY id"
        ).fetchall()

    with pytest.raises(subprocess.CalledProcessError):
        _run(url, "-m", "alembic", "upgrade", REVISION_0073)
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == REVISION_0072
        assert connection.execute(
            "SELECT * FROM training_week_activities WHERE content_ref = 'mfa-reset' "
            "AND activity_type = 'service_desk_scenario' ORDER BY id"
        ).fetchall() == before
