"""Disposable production-shaped 0074 -> 0075 -> 0074 SQLite rehearsal."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = "0074_v2_learning_evidence"
REVISION = "0075_v2_learning_interactions"


def _alembic(url, *args):
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, check=True, text=True)


def test_upgrade_downgrade_keeps_existing_student_and_v2_history(tmp_path):
    path = tmp_path / "from-0074.db"
    url = f"sqlite:///{path}"
    _alembic(url, "upgrade", PREVIOUS)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO students(name,email,is_mentor) VALUES ('Pilot','pilot@local.test',0)")
        student_id = db.execute("SELECT id FROM students WHERE email='pilot@local.test'").fetchone()[0]
        db.execute("INSERT INTO v2_module_activity(student_id,module_key,activity_type,ref_key,status,detail) VALUES (?,'old.module','lesson','old.lesson','completed','{}')", (student_id,))
        db.commit()
    _alembic(url, "upgrade", REVISION)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
        assert db.execute("SELECT status FROM v2_module_activity WHERE student_id=?", (student_id,)).fetchone() == ("completed",)
        assert db.execute("SELECT count(*) FROM v2_interaction_attempts").fetchone() == (0,)
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    _alembic(url, "downgrade", PREVIOUS)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (PREVIOUS,)
        assert db.execute("SELECT status FROM v2_module_activity WHERE student_id=?", (student_id,)).fetchone() == ("completed",)
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "v2_interaction_attempts" not in names
        assert "v2_interaction_definitions" not in names
