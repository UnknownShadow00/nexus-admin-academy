"""Disposable 0073 -> 0074 rehearsal; historical V2 self reports stay intact."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = "0073_mfa_week7_curriculum_card"
REVISION = "0074_v2_learning_evidence"


def _alembic(url, *args):
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND_ROOT,
        env=env, capture_output=True, check=True, text=True,
    )


def test_upgrade_and_downgrade_preserve_old_v2_activity(tmp_path):
    path = tmp_path / "pre-v2-evidence.db"
    url = f"sqlite:///{path}"
    _alembic(url, "upgrade", PREVIOUS)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO students(name, email, is_mentor) VALUES ('Pilot', 'pilot@test.local', 0)")
        student_id = connection.execute("SELECT id FROM students WHERE email='pilot@test.local'").fetchone()[0]
        connection.execute(
            "INSERT INTO v2_resources(resource_key, title, resource_type, active) VALUES ('old.video', 'Old video', 'video', 1)"
        )
        resource_id = connection.execute("SELECT id FROM v2_resources WHERE resource_key='old.video'").fetchone()[0]
        connection.execute(
            "INSERT INTO v2_student_resource_activity(student_id, resource_id, completed, completed_at) "
            "VALUES (?, ?, 1, '2026-08-01 12:00:00')", (student_id, resource_id),
        )
        connection.execute(
            "INSERT INTO v2_module_activity(student_id, module_key, activity_type, ref_key, status, detail) "
            "VALUES (?, 'old.module', 'resource', 'old.video', 'completed', '{}')", (student_id,),
        )
        connection.commit()

    _alembic(url, "upgrade", REVISION)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
        assert connection.execute(
            "SELECT completed, completed_at, watched_at FROM v2_student_resource_activity "
            "WHERE student_id=? AND resource_id=?", (student_id, resource_id),
        ).fetchone() == (1, "2026-08-01 12:00:00", None)
        assert connection.execute("SELECT status FROM v2_module_activity WHERE student_id=?", (student_id,)).fetchone() == ("completed",)
        assert connection.execute("SELECT count(*) FROM v2_evidence_records").fetchone() == (0,)
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    _alembic(url, "downgrade", PREVIOUS)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (PREVIOUS,)
        assert connection.execute("SELECT completed FROM v2_student_resource_activity WHERE student_id=?", (student_id,)).fetchone() == (1,)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(v2_student_resource_activity)")}
        assert "watched_at" not in columns
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "v2_evidence_records" not in tables
        assert "v2_evidence_requirements" not in tables
