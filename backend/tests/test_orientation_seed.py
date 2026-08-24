import json
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

# The merge commit that landed Phase 4B.1 on main, before Phase 4B.2 began.
# Its migration head is 0057 and its OWN seed_curriculum.py only knows about
# 4B.1-era sync functions -- unlike the current tree's seed_curriculum.py,
# which unconditionally runs every sync function whose guard is satisfied
# (including Phase 4B.2's), regardless of which alembic revision a DB was
# migrated to. So "a fresh install as of the 0057 boundary" can only be
# built from this pinned commit's own code, not from the current tree with
# an alembic revision argument -- pinning alembic alone does not isolate
# seed_curriculum.py's unconditional sync calls.
_POST_PHASE_4B1_COMMIT = "58bc50a47dea7b447e62a421417d1d036346655b"


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

    # 1. "Fresh install as of the 0057 boundary": built from _POST_PHASE_4B1_
    # COMMIT's own pinned code (its head is 0057; its seed_curriculum.py has
    # no knowledge of Phase 4B.2 or later), NOT from the current tree. See
    # the comment on _POST_PHASE_4B1_COMMIT above for why pinning an alembic
    # revision on today's code is not sufficient by itself.
    fresh_src = tmp_path / "fresh_src"
    fresh_src.mkdir()
    fresh_archive_path = tmp_path / "fresh_backend.tar"
    with fresh_archive_path.open("wb") as archive_file:
        subprocess.run(
            ["git", "archive", _POST_PHASE_4B1_COMMIT, "backend"],
            cwd=REPO_ROOT,
            stdout=archive_file,
            check=True,
        )
    with tarfile.open(fresh_archive_path) as archive:
        archive.extractall(fresh_src, filter="data")
    fresh_backend_root = fresh_src / "backend"

    fresh_db = tmp_path / "fresh.db"
    fresh_url = f"sqlite:///{fresh_db}"
    fresh_environment = os.environ.copy()
    fresh_environment["DATABASE_URL"] = fresh_url
    subprocess.run(
        [python, "-m", "alembic", "upgrade", "head"],
        cwd=fresh_backend_root,
        env=fresh_environment,
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        [python, "seed.py"], cwd=fresh_backend_root, env=fresh_environment, capture_output=True, check=True, text=True
    )
    subprocess.run(
        [python, "seed_curriculum.py"],
        cwd=fresh_backend_root,
        env=fresh_environment,
        capture_output=True,
        check=True,
        text=True,
    )

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
    # The above "head" is scoped to the legacy_backend_root checkout's OWN
    # migration history (frozen at _PRE_PHASE_4B1_COMMIT), not the current
    # branch's -- so it is already correctly pinned by definition and needs
    # no change here.
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

    # 3. Upgrade the historical DB through migration 0057 (pinned, not
    #    "head"), matching how production is actually upgraded: migration
    #    only, no reseed.
    _run([python, "-m", "alembic", "upgrade", "0057_microsoft_workplace_foundations"], historical_url)

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
    assert first["week_count"] == 35
    # Legacy support_ticket activities are retired; the reviewed Service Desk
    # scenarios replace the required curriculum path instead. The Weeks 3-24
    # quality syncs preserve the historical rows and add deterministic practice
    # activities where the required path previously had no real skill exercise.
    # 320 = 288 (post-Phase-4B.1) + 32 (Phase 4B.2 Intune/endpoint content).
    assert first["activity_count"] == 320
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


# The last commit before Phase 4B.2 (Intune & Windows 11 endpoint management)
# began -- the merge that landed Phase 4B.1 on main. Same rationale as
# _PRE_PHASE_4B1_COMMIT above: intentionally pinned, not derived, to anchor a
# fixed historical baseline this regression test must never silently outrun.
_PRE_PHASE_4B2_COMMIT = "58bc50a47dea7b447e62a421417d1d036346655b"


def test_fresh_seed_matches_upgraded_historical_seed_for_phase_4b2(tmp_path):
    """Phase 4B.2 regression test: same convergence proof as Phase 4B.1's
    test_fresh_seed_matches_upgraded_historical_seed_for_active_curriculum,
    one migration later. A fresh install and a genuinely historical
    post-Phase-4B.1 install (built with the actual pre-4B.2 code, then
    upgraded through migration 0058 only -- no reseed) must converge on the
    same active curriculum identity.
    """
    git_check = subprocess.run(
        ["git", "cat-file", "-e", f"{_PRE_PHASE_4B2_COMMIT}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if git_check.returncode != 0:
        pytest.skip(
            "pre-Phase-4B.2 commit not reachable (likely a shallow checkout); "
            "run with full git history to exercise this regression test"
        )

    python = sys.executable

    # Pinned to migration 0058, not "head" -- see the 4B.1 test above for why.
    fresh_db = tmp_path / "fresh_4b2.db"
    _run([python, "-m", "alembic", "upgrade", "0058_intune_endpoint_management"], f"sqlite:///{fresh_db}")
    _run([python, "seed.py"], f"sqlite:///{fresh_db}")
    _run([python, "seed_curriculum.py"], f"sqlite:///{fresh_db}")

    legacy_src = tmp_path / "legacy_src_4b2"
    legacy_src.mkdir()
    archive_path = tmp_path / "legacy_backend_4b2.tar"
    with archive_path.open("wb") as archive_file:
        subprocess.run(
            ["git", "archive", _PRE_PHASE_4B2_COMMIT, "backend"],
            cwd=REPO_ROOT,
            stdout=archive_file,
            check=True,
        )
    with tarfile.open(archive_path) as archive:
        archive.extractall(legacy_src, filter="data")
    legacy_backend_root = legacy_src / "backend"

    historical_db = tmp_path / "historical_4b2.db"
    historical_url = f"sqlite:///{historical_db}"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = historical_url
    subprocess.run([python, "-m", "alembic", "upgrade", "head"], cwd=legacy_backend_root, env=environment, capture_output=True, check=True, text=True)
    subprocess.run([python, "seed.py"], cwd=legacy_backend_root, env=environment, capture_output=True, check=True, text=True)
    subprocess.run([python, "seed_curriculum.py"], cwd=legacy_backend_root, env=environment, capture_output=True, check=True, text=True)
    with sqlite3.connect(historical_db) as connection:
        pre_upgrade_count = connection.execute("SELECT count(*) FROM training_week_activities").fetchone()[0]
    assert pre_upgrade_count == 288, "post-Phase-4B.1 baseline drifted; update this test's expectations deliberately"

    _run([python, "-m", "alembic", "upgrade", "0058_intune_endpoint_management"], historical_url)

    fresh_identity = _active_curriculum_identity(fresh_db)
    historical_identity = _active_curriculum_identity(historical_db)

    assert len(fresh_identity) == 320
    assert len(historical_identity) == 320
    assert fresh_identity == historical_identity, (
        "fresh install and upgraded-historical install diverged in active curriculum identity"
    )


def test_phase_4b2_downgrade_reupgrade_preserves_historical_graduation(tmp_path):
    """A permanent graduating-role award survives the reversible content
    cycle, while only Phase 4B.2 rows/gate additions are removed and restored."""
    database_path = tmp_path / "phase4b2_cycle.db"
    database_url = f"sqlite:///{database_path}"
    python = sys.executable
    _run([python, "-m", "alembic", "upgrade", "0058_intune_endpoint_management"], database_url)
    _run([python, "seed.py"], database_url)
    _run([python, "seed_curriculum.py"], database_url)

    with sqlite3.connect(database_path) as connection:
        role_id = connection.execute(
            "SELECT id FROM roles WHERE name = 'Junior Infrastructure Administrator'"
        ).fetchone()[0]
        cursor = connection.execute(
            "INSERT INTO students (name, email, username, password_hash, current_role_id) VALUES (?, ?, ?, ?, ?)",
            ("Historical Graduate", "graduate@example.test", "historical-graduate", "not-a-real-hash", role_id),
        )
        student_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO student_roles (student_id, role_id, promotion_notes) VALUES (?, ?, ?)",
            (student_id, role_id, "Awarded before the Phase 4B.2 review cycle"),
        )
        endpoint_lesson_id = connection.execute(
            """
            SELECT lessons.id
              FROM lessons
              JOIN modules ON modules.id = lessons.module_id
             WHERE modules.code = 'MOD-030'
             ORDER BY lessons.id
             LIMIT 1
            """
        ).fetchone()[0]
        endpoint_quiz_id = connection.execute(
            "SELECT id FROM quizzes WHERE week_number = 33 ORDER BY id LIMIT 1"
        ).fetchone()[0]
        endpoint_lab_id = connection.execute(
            "SELECT id FROM lab_templates WHERE week_number = 30 ORDER BY id LIMIT 1"
        ).fetchone()[0]
        lesson_progress_cursor = connection.execute(
            "INSERT INTO student_lesson_progress (student_id, lesson_id, completed_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (student_id, endpoint_lesson_id),
        )
        lesson_progress_id = lesson_progress_cursor.lastrowid
        quiz_attempt_cursor = connection.execute(
            """
            INSERT INTO quiz_attempts
                (student_id, quiz_id, answers, score, xp_awarded, best_score, first_attempt_xp)
            VALUES (?, ?, '{}', 0, 0, 0, 0)
            """,
            (student_id, endpoint_quiz_id),
        )
        quiz_attempt_id = quiz_attempt_cursor.lastrowid
        lab_run_cursor = connection.execute(
            """
            INSERT INTO lab_runs
                (lab_template_id, student_id, status, hints_used)
            VALUES (?, ?, 'assigned', 0)
            """,
            (endpoint_lab_id, student_id),
        )
        lab_run_id = lab_run_cursor.lastrowid
        scenario_id, scenario_version_id = connection.execute(
            """
            SELECT scenarios.id, versions.id
              FROM service_desk_scenarios AS scenarios
              JOIN service_desk_scenario_versions AS versions
                ON versions.scenario_id = scenarios.id
             WHERE scenarios.stable_key = 'bitlocker-recovery'
               AND versions.status = 'published'
            """
        ).fetchone()
        connection.execute(
            """
            INSERT INTO service_desk_assignments
                (student_id, scenario_id, mode, is_required, assigned_by)
            VALUES (?, ?, 'simulation', 1, 'migration-regression')
            """,
            (student_id, scenario_id),
        )
        attempt_cursor = connection.execute(
            """
            INSERT INTO service_desk_attempts
                (student_id, scenario_version_id, mode, experience_mode, status,
                 current_state, current_state_hash, state_version, attempt_number)
            VALUES (?, ?, 'simulation', 'assessment', 'completed', '{}', ?, 1, 1)
            """,
            (student_id, scenario_version_id, "0" * 64),
        )
        attempt_id = attempt_cursor.lastrowid
        connection.execute(
            """
            INSERT INTO service_desk_attempt_events
                (attempt_id, sequence_number, idempotency_key, event_type, tool,
                 payload, previous_state_hash, resulting_state_hash, success, trusted)
            VALUES (?, 1, 'migration-regression-event', 'device.inspect_record',
                    'device', '{}', ?, ?, 1, 1)
            """,
            (attempt_id, "0" * 64, "1" * 64),
        )
        connection.execute(
            """
            INSERT INTO service_desk_attempt_grades
                (attempt_id, scenario_version_id, rubric_version,
                 technical_complete, critical_failure, overall_score, passed,
                 feedback_summary, details)
            VALUES (?, ?, 'phase4b2-regression', 1, 0, 100, 1, 'Passed', '{}')
            """,
            (attempt_id, scenario_version_id),
        )

        # Seed a completely unrelated historical attempt and prove downgrade
        # does not use broad Service Desk deletes while removing the two
        # Phase 4B.2 scenarios.
        unrelated_scenario_id, unrelated_version_id = connection.execute(
            """
            SELECT scenarios.id, versions.id
              FROM service_desk_scenarios AS scenarios
              JOIN service_desk_scenario_versions AS versions
                ON versions.scenario_id = scenarios.id
             WHERE scenarios.stable_key = 'locked-user-account'
               AND versions.status = 'published'
            """
        ).fetchone()
        connection.execute(
            """
            INSERT INTO service_desk_assignments
                (student_id, scenario_id, mode, is_required, assigned_by)
            VALUES (?, ?, 'simulation', 1, 'unrelated-history-regression')
            """,
            (student_id, unrelated_scenario_id),
        )
        unrelated_attempt_cursor = connection.execute(
            """
            INSERT INTO service_desk_attempts
                (student_id, scenario_version_id, mode, experience_mode, status,
                 current_state, current_state_hash, state_version, attempt_number)
            VALUES (?, ?, 'simulation', 'assessment', 'completed', '{}', ?, 1, 1)
            """,
            (student_id, unrelated_version_id, "2" * 64),
        )
        unrelated_attempt_id = unrelated_attempt_cursor.lastrowid
        connection.execute(
            """
            INSERT INTO service_desk_attempt_events
                (attempt_id, sequence_number, idempotency_key, event_type, tool,
                 payload, previous_state_hash, resulting_state_hash, success, trusted)
            VALUES (?, 1, 'unrelated-history-event', 'directory.inspect_account',
                    'directory', '{}', ?, ?, 1, 1)
            """,
            (unrelated_attempt_id, "2" * 64, "3" * 64),
        )
        connection.execute(
            """
            INSERT INTO service_desk_attempt_grades
                (attempt_id, scenario_version_id, rubric_version,
                 technical_complete, critical_failure, overall_score, passed,
                 feedback_summary, details)
            VALUES (?, ?, 'unrelated-history-regression', 1, 0, 100, 1, 'Passed', '{}')
            """,
            (unrelated_attempt_id, unrelated_version_id),
        )
        connection.commit()

    _run([python, "-m", "alembic", "downgrade", "0057_microsoft_workplace_foundations"], database_url)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT count(*) FROM training_weeks WHERE week_number BETWEEN 30 AND 34").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM student_roles WHERE student_id = ? AND role_id = ?", (student_id, role_id)).fetchone()[0] == 1
        assert connection.execute("SELECT current_role_id FROM students WHERE id = ?", (student_id,)).fetchone()[0] == role_id
        assert connection.execute("SELECT count(*) FROM service_desk_attempts WHERE id = ?", (attempt_id,)).fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM student_lesson_progress WHERE id = ?", (lesson_progress_id,)).fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM quiz_attempts WHERE id = ?", (quiz_attempt_id,)).fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM lab_runs WHERE id = ?", (lab_run_id,)).fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM service_desk_attempts WHERE id = ?", (unrelated_attempt_id,)).fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM service_desk_attempt_events WHERE attempt_id = ?", (unrelated_attempt_id,)).fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM service_desk_attempt_grades WHERE attempt_id = ?", (unrelated_attempt_id,)).fetchone()[0] == 1

    _run([python, "-m", "alembic", "upgrade", "0058_intune_endpoint_management"], database_url)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT count(*) FROM training_weeks WHERE week_number BETWEEN 30 AND 34").fetchone()[0] == 5
        assert connection.execute("SELECT count(*) FROM training_week_activities").fetchone()[0] == 320
        assert connection.execute("SELECT count(*) FROM student_roles WHERE student_id = ? AND role_id = ?", (student_id, role_id)).fetchone()[0] == 1
        assert connection.execute("SELECT current_role_id FROM students WHERE id = ?", (student_id,)).fetchone()[0] == role_id
        assert connection.execute("SELECT count(*) FROM service_desk_attempts WHERE id = ?", (unrelated_attempt_id,)).fetchone()[0] == 1
        gate_configs = [
            json.loads(row[0])
            for row in connection.execute(
                "SELECT requirement_config FROM promotion_gates WHERE role_id = ?",
                (role_id,),
            )
        ]
        assert sum(config == {"week": 33} for config in gate_configs) == 1
        assert sum(config == {"pack_key": "endpoint-management", "min_passed": 2} for config in gate_configs) == 1
