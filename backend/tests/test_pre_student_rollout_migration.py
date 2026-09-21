import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_REVISION = "0069_merge_v2_beginner_heads"
CANDIDATE_REVISION = "0071_forced_first_login_password_change"


def _environment(database_url: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "JWT_SECRET_KEY": "isolated-0069-upgrade-secret-at-least-32-bytes",
            "JWT_ALGORITHM": "HS256",
            "COOKIE_SECURE": "false",
            "SEED_PASSWORD_MENTOR": "MigrationMentor!2026",
            "SEED_PASSWORD_SHAK": "MigrationShak!2026",
            "SEED_PASSWORD_RAKIB": "MigrationRakib!2026",
            "SEED_PASSWORD_AHMED": "MigrationAhmed!2026",
            "SEED_PASSWORD_EMRAN": "MigrationEmran!2026",
            "SEED_PASSWORD_WALO": "MigrationWalo!2026",
            "SEED_PASSWORD_HUDAYFA": "MigrationHudayfa!2026",
        }
    )
    return environment


def _run(database_url: str, *command: str) -> None:
    subprocess.run(
        [sys.executable, *command],
        cwd=BACKEND_ROOT,
        env=_environment(database_url),
        capture_output=True,
        check=True,
        text=True,
    )


def _history_snapshot(connection: sqlite3.Connection, student_id: int) -> dict[str, list[tuple]]:
    return {
        "lesson": connection.execute(
            "SELECT lesson_id, completed_at FROM student_lesson_progress WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall(),
        "quiz": connection.execute(
            "SELECT quiz_id, answers, score, xp_awarded FROM quiz_attempts WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall(),
        "cli": connection.execute(
            "SELECT lab_id, completed_at, xp_awarded, command_log FROM cli_lab_attempt WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall(),
        "lab": connection.execute(
            "SELECT lab_template_id, status, final_score, xp_awarded FROM lab_runs WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall(),
        "ticket": connection.execute(
            "SELECT ticket_id, writeup, ai_score, xp_awarded FROM ticket_submissions WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall(),
        "service_desk": connection.execute(
            "SELECT scenario_version_id, status, score, passed FROM service_desk_attempts WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall(),
        "service_desk_events": connection.execute(
            "SELECT event_type, tool, payload, success, trusted FROM service_desk_attempt_events "
            "WHERE attempt_id IN (SELECT id FROM service_desk_attempts WHERE student_id = ?) ORDER BY id",
            (student_id,),
        ).fetchall(),
    }


def test_0069_snapshot_upgrades_reconciles_and_preserves_student_history(tmp_path):
    database_path = tmp_path / "production-0069-snapshot.db"
    database_url = f"sqlite:///{database_path}"

    _run(database_url, "-m", "alembic", "upgrade", PRODUCTION_REVISION)
    _run(database_url, "seed.py")
    _run(database_url, "seed_curriculum.py")

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        lesson_id = connection.execute("SELECT MIN(id) FROM lessons").fetchone()[0]
        quiz_id = connection.execute("SELECT MIN(id) FROM quizzes").fetchone()[0]
        cli_lab_id = connection.execute("SELECT MIN(id) FROM cli_lab").fetchone()[0]
        lab_template_id = connection.execute("SELECT MIN(id) FROM lab_templates").fetchone()[0]
        ticket_id = connection.execute("SELECT MIN(id) FROM tickets").fetchone()[0]
        scenario_version_id = connection.execute(
            "SELECT MIN(id) FROM service_desk_scenario_versions"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO students (name, email, username, password_hash, is_mentor, total_xp) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            ("Existing Production Student", "existing-0069@example.test", "existing-0069", "preserved-hash", 375),
        )
        student_id = connection.execute(
            "SELECT id FROM students WHERE username = 'existing-0069'"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO student_lesson_progress (student_id, lesson_id, completed_at) VALUES (?, ?, ?)",
            (student_id, lesson_id, "2026-09-20 10:00:00"),
        )
        connection.execute(
            "INSERT INTO quiz_attempts "
            "(student_id, quiz_id, answers, score, xp_awarded, best_score, first_attempt_xp, results) "
            "VALUES (?, ?, ?, 88, 25, 88, 25, ?)",
            (student_id, quiz_id, json.dumps({"1": "A"}), json.dumps({"passed": True})),
        )
        connection.execute(
            "INSERT INTO cli_lab_attempt "
            "(id, student_id, lab_id, completed_at, xp_awarded, command_log) VALUES (?, ?, ?, ?, 30, ?)",
            ("preserved-cli-attempt", student_id, cli_lab_id, "2026-09-20 10:10:00", json.dumps(["hostname"])),
        )
        connection.execute(
            "INSERT INTO lab_runs "
            "(lab_template_id, student_id, status, final_score, xp_awarded) VALUES (?, ?, 'verified', 92, 40)",
            (lab_template_id, student_id),
        )
        connection.execute(
            "INSERT INTO ticket_submissions "
            "(student_id, ticket_id, writeup, ai_score, ai_feedback, xp_awarded, collaborator_ids, methodology_steps_mentioned) "
            "VALUES (?, ?, 'Preserved ticket history', 9, ?, 35, ?, ?)",
            (student_id, ticket_id, json.dumps({"summary": "preserved"}), json.dumps([]), json.dumps({})),
        )
        connection.execute(
            "INSERT INTO service_desk_attempts "
            "(student_id, scenario_version_id, mode, status, current_state, current_state_hash, state_version, "
            "attempt_number, score, passed, experience_mode) "
            "VALUES (?, ?, 'simulation', 'completed', ?, ?, 1, 1, 94, 1, 'assessment')",
            (student_id, scenario_version_id, json.dumps({"preserved": True}), "a" * 64),
        )
        attempt_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        connection.execute(
            "INSERT INTO service_desk_attempt_events "
            "(attempt_id, sequence_number, idempotency_key, event_type, tool, payload, previous_state_hash, "
            "resulting_state_hash, success, trusted) VALUES (?, 1, ?, 'ticket.close', 'ticket', ?, ?, ?, 1, 1)",
            (attempt_id, "preserved-event", json.dumps({"resolution": "preserved"}), "0" * 64, "a" * 64),
        )
        connection.commit()
        before = _history_snapshot(connection, student_id)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == PRODUCTION_REVISION

    _run(database_url, "-m", "alembic", "upgrade", CANDIDATE_REVISION)
    _run(database_url, "scripts/seed_users.py")
    _run(database_url, "seed.py")
    _run(database_url, "seed_curriculum.py")

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == CANDIDATE_REVISION
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        student = connection.execute(
            "SELECT id, name, email, username, password_hash, total_xp FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
        assert student == (
            student_id,
            "Existing Production Student",
            "existing-0069@example.test",
            "existing-0069",
            "preserved-hash",
            375,
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM student_auth_states WHERE student_id = ?", (student_id,)
        ).fetchone()[0] == 0
        assert _history_snapshot(connection, student_id) == before

        # Week 1–2 polish reconciled on upgrade without changing history IDs.
        polished = dict(
            connection.execute(
                "SELECT title, estimated_minutes FROM lessons WHERE title IN "
                "('Anatomy of a Good Ticket', 'Meet the Command Line', 'Storage: Symptoms Before Specs', "
                "'RAM, CPU, Power, and POST', 'BIOS/UEFI and Boot Order')"
            ).fetchall()
        )
        assert polished == {
            "Anatomy of a Good Ticket": 25,
            "Meet the Command Line": 10,
            "Storage: Symptoms Before Specs": 45,
            "RAM, CPU, Power, and POST": 45,
            "BIOS/UEFI and Boot Order": 30,
        }
