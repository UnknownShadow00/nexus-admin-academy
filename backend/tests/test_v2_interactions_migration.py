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
        db.execute("PRAGMA foreign_keys=ON")
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (REVISION,)
        assert db.execute("SELECT status FROM v2_module_activity WHERE student_id=?", (student_id,)).fetchone() == ("completed",)
        assert db.execute("SELECT count(*) FROM v2_interaction_attempts").fetchone() == (0,)
        cert_id = db.execute("INSERT INTO certifications(cert_key,name,display_order) VALUES ('pilot','Pilot',0)").lastrowid
        version_id = db.execute(
            "INSERT INTO certification_versions(certification_id,version_key,label,exam_codes) VALUES (?,'pilot-v1','Pilot','[]')",
            (cert_id,),
        ).lastrowid
        module_id = db.execute(
            "INSERT INTO certification_modules(certification_version_id,module_key,title,display_order) VALUES (?,'pilot.module','Pilot module',0)",
            (version_id,),
        ).lastrowid
        owned_requirement = db.execute(
            "INSERT INTO v2_evidence_requirements(module_id,evidence_type,ref_key,is_required,active) VALUES (?,'interaction','interaction.pilot.owned',1,1)",
            (module_id,),
        ).lastrowid
        unrelated_requirement = db.execute(
            "INSERT INTO v2_evidence_requirements(module_id,evidence_type,ref_key,is_required,active) VALUES (?,'interaction','interaction.manual',1,1)",
            (module_id,),
        ).lastrowid
        definition_id = db.execute(
            "INSERT INTO v2_interaction_definitions(interaction_key,version,interaction_type,module_id,title,instructions,config,required,status,display_order,pass_percent) "
            "VALUES ('interaction.pilot.owned',1,'typed_answer',?,'Pilot question','Type an answer','{}',1,'published',0,100)",
            (module_id,),
        ).lastrowid
        attempt_id = db.execute(
            "INSERT INTO v2_interaction_attempts(student_id,definition_id,interaction_key,version,attempt_number,definition_snapshot,response_snapshot,result_snapshot,score,passed) "
            "VALUES (?,?,'interaction.pilot.owned',1,1,'{}','{}','{}',100,1)",
            (student_id, definition_id),
        ).lastrowid
        db.execute(
            "INSERT INTO v2_evidence_records(student_id,requirement_id,source_ref) VALUES (?,?,?)",
            (student_id, owned_requirement, f"v2-interaction-attempt:{attempt_id}"),
        )
        db.execute(
            "INSERT INTO v2_evidence_records(student_id,requirement_id,source_ref) VALUES (?,?,'trusted:manual')",
            (student_id, unrelated_requirement),
        )
        db.commit()
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    _alembic(url, "downgrade", PREVIOUS)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == (PREVIOUS,)
        assert db.execute("SELECT status FROM v2_module_activity WHERE student_id=?", (student_id,)).fetchone() == ("completed",)
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "v2_interaction_attempts" not in names
        assert "v2_interaction_definitions" not in names
        assert db.execute("SELECT ref_key FROM v2_evidence_requirements").fetchall() == [("interaction.manual",)]
        assert db.execute("SELECT source_ref FROM v2_evidence_records").fetchall() == [("trusted:manual",)]
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
