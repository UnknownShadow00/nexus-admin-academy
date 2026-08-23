"""Phase 4B.1 verification: a student who completed Lesson 58 / the Entra
guided lab BEFORE migration 0057 keeps that completion after the lesson/lab
are relocated into the new Microsoft Workplace stage (week 26), with no
duplicate rows and a working next_activity calculation afterward.

Builds a genuinely historical DB using the actual pre-Phase-4B.1 backend
source (via git archive of the commit immediately before this feature
began), matching test_orientation_seed.py's convergence-proof technique.
"""
import os
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
_PRE_PHASE_4B1_COMMIT = "0966389e036ecde65564d508fba1bdebd1c347e5"
_MOVED_LESSON_ID = 58
_MOVED_LAB_ORIGINAL_TITLE = "Route the Cloud Identity Ticket"
_MOVED_LAB_NEW_TITLE = "Investigate the Entra Identity Ticket"


def _run(command, database_url, cwd):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    return subprocess.run(command, cwd=cwd, env=environment, capture_output=True, check=True, text=True)


def test_historical_lesson_and_lab_completion_survives_relocation(tmp_path):
    git_check = subprocess.run(
        ["git", "cat-file", "-e", f"{_PRE_PHASE_4B1_COMMIT}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if git_check.returncode != 0:
        pytest.skip("pre-Phase-4B.1 commit not reachable (likely a shallow checkout)")

    python = sys.executable

    legacy_src = tmp_path / "legacy_src"
    legacy_src.mkdir()
    archive_path = tmp_path / "legacy_backend.tar"
    with archive_path.open("wb") as archive_file:
        subprocess.run(["git", "archive", _PRE_PHASE_4B1_COMMIT, "backend"], cwd=REPO_ROOT, stdout=archive_file, check=True)
    with tarfile.open(archive_path) as archive:
        archive.extractall(legacy_src, filter="data")
    legacy_backend_root = legacy_src / "backend"

    db_path = tmp_path / "historical.db"
    db_url = f"sqlite:///{db_path}"
    _run([python, "-m", "alembic", "upgrade", "head"], db_url, legacy_backend_root)
    _run([python, "seed.py"], db_url, legacy_backend_root)
    _run([python, "seed_curriculum.py"], db_url, legacy_backend_root)

    # Enroll a scratch historical student and mark Lesson 58 and the
    # (pre-move) Entra lab complete, using this checkout's current models --
    # they describe the same tables the legacy code just populated.
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        from app.models.lab import LabRun, LabTemplate
        from app.models.learning import Lesson
        from app.models.lesson_progress import StudentLessonProgress
        from app.models.student import Student

        lesson = session.get(Lesson, _MOVED_LESSON_ID)
        assert lesson is not None, "expected Lesson 58 to exist in the historical seed"
        lab = session.query(LabTemplate).filter_by(title=_MOVED_LAB_ORIGINAL_TITLE).first()
        assert lab is not None, "expected the pre-move Entra lab title to exist in the historical seed"

        student = Student(
            name="Historical M365 Student",
            username="historical-m365-student",
            email="historical-m365-student@example.com",
            password_hash="x",
            total_xp=0,
        )
        session.add(student)
        session.flush()

        completed_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
        session.add(StudentLessonProgress(student_id=student.id, lesson_id=lesson.id, completed_at=completed_at))
        session.add(
            LabRun(
                lab_template_id=lab.id,
                student_id=student.id,
                status="verified",
                started_at=completed_at,
                submitted_at=completed_at,
                verified_at=completed_at,
                final_score=95,
                xp_awarded=50,
            )
        )
        session.commit()
        student_id, lesson_id, lab_id = student.id, lesson.id, lab.id
    finally:
        session.close()
        engine.dispose()

    # Upgrade through the CURRENT migration head -- migration only, no reseed
    # -- matching how production is actually upgraded.
    _run([python, "-m", "alembic", "upgrade", "head"], db_url, BACKEND_ROOT)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        from app.models.lab import LabRun, LabTemplate
        from app.models.learning import Lesson, Module
        from app.models.lesson_progress import StudentLessonProgress
        from app.models.student import Student
        from app.services.training_service import build_training_overview

        # Completion rows are untouched: same ids, same timestamp.
        lesson_progress_rows = (
            session.query(StudentLessonProgress)
            .filter_by(student_id=student_id, lesson_id=lesson_id)
            .all()
        )
        assert len(lesson_progress_rows) == 1, "lesson completion must not be duplicated by the relocation"
        assert lesson_progress_rows[0].completed_at.replace(tzinfo=timezone.utc) == datetime(2026, 6, 1, tzinfo=timezone.utc)

        lab_run_rows = session.query(LabRun).filter_by(student_id=student_id, lab_template_id=lab_id).all()
        assert len(lab_run_rows) == 1, "lab completion must not be duplicated by the relocation"
        assert lab_run_rows[0].status == "verified"

        # The relocation actually happened: same row, new identity.
        moved_lab = session.get(LabTemplate, lab_id)
        assert moved_lab.title == _MOVED_LAB_NEW_TITLE
        assert moved_lab.week_number == 26

        moved_lesson = session.get(Lesson, lesson_id)
        module = session.get(Module, moved_lesson.module_id)
        assert module.code == "MOD-026"

        # next_activity still computes without error for this student.
        student = session.get(Student, student_id)
        overview = build_training_overview(session, student)
        assert overview is not None
        assert "next_activity" in overview
    finally:
        session.close()
        engine.dispose()
