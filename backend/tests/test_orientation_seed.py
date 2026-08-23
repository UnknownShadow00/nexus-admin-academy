import os
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from app.models.learning import Lesson, Module
from seed import ORIENTATION_SUMMARY, seed_module0_and_methodology


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
ORIENTATION_TITLE = "Welcome to Nexus: Your First Week"

# The last commit before Phase 4B.1 (Microsoft Workplace Support Core) began.
# Intentionally pinned, not derived (e.g. via merge-base), because it anchors
# a fixed historical baseline for the regression test below and must never
# silently move forward as later work lands on this branch.
_PRE_PHASE_4B1_COMMIT = "0966389e036ecde65564d508fba1bdebd1c347e5"


def _run(command: list[str], database_url: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
        }
    )
    return subprocess.run(
        command,
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )


def _active_curriculum_identity(database_path: Path) -> set[tuple]:
    """(week_number, activity_type, content title/key, is_required) for every
    active TrainingWeekActivity. Deliberately resolves content_ref to its
    referenced row's title/key rather than comparing raw ids: LabTemplate ids
    (and other content ids) are ordinary auto-increment primary keys with no
    stability guarantee across independently-built installations -- only
    intra-installation stability is guaranteed. Comparing by resolved title
    isolates genuine curriculum-identity drift from harmless id offsets.
    """
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT weeks.week_number, activities.activity_type,
                   CASE activities.activity_type
                       WHEN 'guided_lab' THEN (SELECT title FROM lab_templates WHERE id = activities.content_ref)
                       WHEN 'lesson' THEN (SELECT title FROM lessons WHERE id = activities.content_ref)
                       WHEN 'quiz' THEN (SELECT title FROM quizzes WHERE id = activities.content_ref)
                       WHEN 'capstone' THEN (SELECT title FROM capstone_templates WHERE id = activities.content_ref)
                       ELSE activities.content_ref
                   END,
                   activities.is_required
              FROM training_week_activities AS activities
              JOIN training_weeks AS weeks ON weeks.id = activities.training_week_id
            """
        ).fetchall()
        return {tuple(row) for row in rows}


def test_fresh_seed_matches_upgraded_historical_seed_for_active_curriculum(tmp_path):
    """Phase 4B.1 regression test: a brand-new install and a genuinely
    historical pre-Phase-4B.1 install (built with the actual pre-4B.1 code,
    then upgraded through migration 0057 only -- no reseed, matching how
    production is actually upgraded) must converge on the exact same active
    curriculum identity. Historical completion rows are untouched by this
    test; only the *active curriculum structure* is required to converge.
    """
    git_check = subprocess.run(
        ["git", "cat-file", "-e", f"{_PRE_PHASE_4B1_COMMIT}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if git_check.returncode != 0:
        pytest.skip(
            "pre-Phase-4B.1 commit not reachable (likely a shallow checkout); "
            "run with full git history to exercise this regression test"
        )

    python = sys.executable

    # 1. Fresh install under the CURRENT code: migrate to head, seed.
    fresh_db = tmp_path / "fresh.db"
    _run([python, "-m", "alembic", "upgrade", "head"], f"sqlite:///{fresh_db}")
    _run([python, "seed.py"], f"sqlite:///{fresh_db}")
    _run([python, "seed_curriculum.py"], f"sqlite:///{fresh_db}")

    # 2. A genuinely historical install: extract the actual pre-Phase-4B.1
    #    backend source into a scratch directory and run ITS OWN seed
    #    pipeline there, producing a DB shaped exactly like real production
    #    before this feature existed (273 activities / 25 weeks).
    legacy_src = tmp_path / "legacy_src"
    legacy_src.mkdir()
    archive_path = tmp_path / "legacy_backend.tar"
    with archive_path.open("wb") as archive_file:
        subprocess.run(
            ["git", "archive", _PRE_PHASE_4B1_COMMIT, "backend"],
            cwd=REPO_ROOT,
            stdout=archive_file,
            check=True,
        )
    with tarfile.open(archive_path) as archive:
        archive.extractall(legacy_src, filter="data")
    legacy_backend_root = legacy_src / "backend"

    historical_db = tmp_path / "historical.db"
    historical_url = f"sqlite:///{historical_db}"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = historical_url
    subprocess.run(
        [python, "-m", "alembic", "upgrade", "head"],
        cwd=legacy_backend_root,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        [python, "seed.py"],
        cwd=legacy_backend_root,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        [python, "seed_curriculum.py"],
        cwd=legacy_backend_root,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )
    with sqlite3.connect(historical_db) as connection:
        pre_upgrade_count = connection.execute("SELECT count(*) FROM training_week_activities").fetchone()[0]
    assert pre_upgrade_count == 273, "pre-Phase-4B.1 baseline drifted; update this test's expectations deliberately"

    # 3. Upgrade the historical DB through CURRENT migration head, matching
    #    how production is actually upgraded: migration only, no reseed.
    _run([python, "-m", "alembic", "upgrade", "head"], historical_url)

    fresh_identity = _active_curriculum_identity(fresh_db)
    historical_identity = _active_curriculum_identity(historical_db)

    assert len(fresh_identity) == 288
    assert len(historical_identity) == 288
    assert fresh_identity == historical_identity, (
        "fresh install and upgraded-historical install diverged in active curriculum identity"
    )


def _fresh_seed_snapshot(database_path: Path) -> dict:
    with sqlite3.connect(database_path) as connection:
        module_lessons = connection.execute(
            """
            SELECT lessons.id, lessons.title, lessons.lesson_order
              FROM lessons JOIN modules ON modules.id = lessons.module_id
             WHERE modules.code = 'MOD-000'
             ORDER BY lessons.lesson_order, lessons.id
            """
        ).fetchall()
        orientation_id = next(row[0] for row in module_lessons if row[1] == ORIENTATION_TITLE)
        orientation_activities = connection.execute(
            """
            SELECT activities.stable_id, activities.display_order, activities.is_required
              FROM training_week_activities AS activities
              JOIN training_weeks AS weeks ON weeks.id = activities.training_week_id
             WHERE weeks.week_number = 0
               AND activities.activity_type = 'lesson'
               AND activities.content_ref = ?
            """,
            (str(orientation_id),),
        ).fetchall()
        week_zero_activities = connection.execute(
            """
            SELECT activities.stable_id, activities.activity_type,
                   activities.content_ref, activities.display_order,
                   activities.is_required
              FROM training_week_activities AS activities
              JOIN training_weeks AS weeks ON weeks.id = activities.training_week_id
             WHERE weeks.week_number = 0
             ORDER BY activities.display_order
            """
        ).fetchall()
        mod_001_prerequisite = connection.execute(
            "SELECT prerequisite_module_id FROM modules WHERE code = 'MOD-001'"
        ).fetchone()[0]
        return {
            "lessons": module_lessons,
            "orientation_activities": orientation_activities,
            "week_zero_activities": week_zero_activities,
            "week_count": connection.execute("SELECT count(*) FROM training_weeks").fetchone()[0],
            "activity_count": connection.execute("SELECT count(*) FROM training_week_activities").fetchone()[0],
            "legacy_support_ticket_count": connection.execute("SELECT count(*) FROM training_week_activities WHERE activity_type = 'support_ticket'").fetchone()[0],
            "active_video_count": connection.execute("SELECT count(*) FROM curriculum_videos WHERE active = 1").fetchone()[0],
            "mod_001_prerequisite": mod_001_prerequisite,
        }


def test_completely_fresh_seed_contains_orientation_and_is_idempotent(tmp_path):
    database_path = tmp_path / "fresh-seed.db"
    database_url = f"sqlite:///{database_path}"
    python = sys.executable

    _run([python, "-m", "alembic", "upgrade", "head"], database_url)
    _run([python, "seed.py"], database_url)
    _run([python, "seed_curriculum.py"], database_url)
    first = _fresh_seed_snapshot(database_path)

    _run([python, "seed.py"], database_url)
    _run([python, "seed_curriculum.py"], database_url)
    second = _fresh_seed_snapshot(database_path)
    validation = _run([python, "scripts/validate_training_curriculum.py"], database_url)

    assert [(title, order) for _, title, order in first["lessons"]] == [(ORIENTATION_TITLE, 1)]
    assert first["orientation_activities"] == [(f"week-0-lesson-{first['lessons'][0][0]}", 1, 1)]
    assert first["week_zero_activities"] == [
        ("week-0-lesson-1", "lesson", "1", 1, 1),
        ("week-0-video-182", "video", "182", 2, 0),
        ("week-0-video-166", "video", "166", 3, 0),
        ("week-0-video-168", "video", "168", 4, 0),
        ("week-0-quiz-42", "quiz", "42", 5, 1),
    ]
    assert first["week_count"] == 30
    # Legacy support_ticket activities are retired; the reviewed Service Desk
    # scenarios replace the required curriculum path instead. The Weeks 3-24
    # quality syncs preserve the historical rows and add deterministic practice
    # activities where the required path previously had no real skill exercise.
    assert first["activity_count"] == 288
    assert first["legacy_support_ticket_count"] == 0
    assert first["active_video_count"] == 137
    assert first["mod_001_prerequisite"] is None
    assert second == first
    assert '"valid": true' in validation.stdout
    assert '"mapped_video_count": 137' in validation.stdout


def test_orientation_summary_is_short_and_beginner_friendly():
    assert "Complete these 2 things" in ORIENTATION_SUMMARY
    assert "Week 1 unlocks automatically" in ORIENTATION_SUMMARY
    assert "Service Desk" in ORIENTATION_SUMMARY
    for internal_term in ("remediation", "evidence", "AI grading", "promotion gate", "mentor review"):
        assert internal_term.lower() not in ORIENTATION_SUMMARY.lower()
    assert len(ORIENTATION_SUMMARY.split()) < 120


def test_seed_updates_existing_orientation_in_place_without_replacing_history(db):
    module = Module(
        code="MOD-000",
        title="Troubleshooting Methodology",
        description="Production module description",
        module_order=0,
        active=True,
    )
    db.add(module)
    db.flush()
    orientation = Lesson(
        module_id=module.id,
        title=ORIENTATION_TITLE,
        summary="Existing reviewed orientation content",
        lesson_order=1,
        estimated_minutes=12,
        required_notes_template="Existing reviewed notes prompt",
        status="published",
    )
    db.add(orientation)
    db.commit()
    original_id = orientation.id

    seed_module0_and_methodology(db)
    db.commit()
    updated = db.query(Lesson).filter(Lesson.module_id == module.id, Lesson.title == ORIENTATION_TITLE).one()
    assert updated.id == original_id
    assert updated.summary == ORIENTATION_SUMMARY
    assert updated.lesson_order == 1
    assert updated.estimated_minutes == 3
    assert updated.required_notes_template is None
    assert updated.status == "published"


def test_microsoft_workplace_capstone_is_role_gated(tmp_path):
    """Every seeded capstone requires a role_level (seed.py's seed_capstones
    always sets one); an ungated Microsoft Workplace capstone would surface
    "Capstones" in student nav for every student, including a brand-new
    Trainee, regardless of curriculum position (LabsPage.jsx gates the nav
    entry on has_unlocked_capstones, which is true whenever ANY accessible
    capstone exists for the student's rank)."""
    database_path = tmp_path / "capstone-gate.db"
    database_url = f"sqlite:///{database_path}"
    python = sys.executable
    _run([python, "-m", "alembic", "upgrade", "head"], database_url)
    _run([python, "seed.py"], database_url)
    _run([python, "seed_curriculum.py"], database_url)

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT capstones.role_level, roles.name
              FROM capstone_templates AS capstones
              LEFT JOIN roles ON roles.id = capstones.role_level
             WHERE capstones.title = 'Microsoft Workplace Support Shift'
            """
        ).fetchone()

    assert row is not None, "expected the Microsoft Workplace capstone to exist"
    role_level, role_name = row
    assert role_level is not None, "Microsoft Workplace capstone must require a role, not be visible to every student"
    assert role_name == "Junior Systems Technician"
