"""Disposable current-main -> continuation -> current-main schema rehearsal."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = "0075_v2_learning_interactions"
REVISION = "0076_beginner_continuation_grants"


def _alembic(url, *args):
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, check=True, text=True)


def test_upgrade_constraints_and_deterministic_downgrade(tmp_path):
    path = tmp_path / "continuation-rehearsal.db"
    url = f"sqlite:///{path}"
    _alembic(url, "upgrade", PREVIOUS)
    with sqlite3.connect(path) as db:
        student_id = db.execute("INSERT INTO students(name,email,is_mentor) VALUES ('Pilot','pilot-continuation@local.test',0)").lastrowid
        cert_id = db.execute("INSERT INTO certifications(cert_key,name,display_order) VALUES ('continuation-test','Pilot',0)").lastrowid
        version_id = db.execute("INSERT INTO certification_versions(certification_id,version_key,label,exam_codes) VALUES (?,'continuation-v1','Pilot','[]')", (cert_id,)).lastrowid
        module_id = db.execute("INSERT INTO certification_modules(certification_version_id,module_key,title,display_order) VALUES (?,'continuation.module','Pilot module',0)", (version_id,)).lastrowid
        db.commit()
    _alembic(url, "upgrade", REVISION)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
        assert db.execute("SELECT count(*) FROM v2_beginner_continuation_grants").fetchone() == (0,)
        columns = {row[1] for row in db.execute("PRAGMA table_info(v2_beginner_continuation_grants)")}
        assert columns == {"id", "student_id", "certification_module_id", "granted_at", "grant_reason"}
        fks = {(row[2], row[3], row[4], row[6]) for row in db.execute("PRAGMA foreign_key_list(v2_beginner_continuation_grants)")}
        assert fks == {("students", "student_id", "id", "CASCADE"), ("certification_modules", "certification_module_id", "id", "RESTRICT")}
        indexes = list(db.execute("PRAGMA index_list(v2_beginner_continuation_grants)"))
        assert any(row[2] and [col[2] for col in db.execute(f"PRAGMA index_info({row[1]})")] == ["student_id", "certification_module_id"] for row in indexes)
        db.execute("INSERT INTO v2_beginner_continuation_grants(student_id,certification_module_id,grant_reason) VALUES (?,?,'backfill_mastered')", (student_id, module_id))
        try:
            db.execute("INSERT INTO v2_beginner_continuation_grants(student_id,certification_module_id,grant_reason) VALUES (?,?,'requirements_satisfied')", (student_id, module_id))
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("duplicate continuation grant was accepted")
        db.commit()
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    _alembic(url, "downgrade", PREVIOUS)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (PREVIOUS,)
        assert "v2_beginner_continuation_grants" not in {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert db.execute("SELECT id FROM students WHERE id=?", (student_id,)).fetchone() == (student_id,)
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
