import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.models.learning import Lesson, Module
from seed import ORIENTATION_SUMMARY, seed_module0_and_methodology


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ORIENTATION_TITLE = "Welcome to Nexus: Your First Week"
METHODOLOGY_TITLE = "CompTIA 6-Step Process"


def _run(command: list[str], database_url: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "SERVICE_DESK_LAB_ENABLED": "false",
            "SERVICE_DESK_LAB_ADMIN_ENABLED": "false",
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
                   activities.content_ref, activities.display_order
              FROM training_week_activities AS activities
              JOIN training_weeks AS weeks ON weeks.id = activities.training_week_id
             WHERE weeks.week_number = 0
             ORDER BY activities.display_order
            """
        ).fetchall()
        return {
            "lessons": module_lessons,
            "orientation_activities": orientation_activities,
            "week_zero_activities": week_zero_activities,
            "week_count": connection.execute("SELECT count(*) FROM training_weeks").fetchone()[0],
            "activity_count": connection.execute("SELECT count(*) FROM training_week_activities").fetchone()[0],
            "active_video_count": connection.execute("SELECT count(*) FROM curriculum_videos WHERE active = 1").fetchone()[0],
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

    assert [(title, order) for _, title, order in first["lessons"]] == [
        (ORIENTATION_TITLE, 1),
        (METHODOLOGY_TITLE, 2),
    ]
    assert first["orientation_activities"] == [(f"week-0-lesson-{first['lessons'][0][0]}", 1, 1)]
    assert first["week_zero_activities"] == [
        ("week-0-lesson-1", "lesson", "1", 1),
        ("week-0-lesson-2", "lesson", "2", 2),
        ("week-0-video-182", "video", "182", 3),
        ("week-0-video-166", "video", "166", 4),
        ("week-0-video-168", "video", "168", 5),
        ("week-0-quiz-42", "quiz", "42", 6),
    ]
    assert first["week_count"] == 25
    assert first["activity_count"] == 296
    assert first["active_video_count"] == 137
    assert second == first
    assert '"valid": true' in validation.stdout
    assert '"mapped_video_count": 137' in validation.stdout


def test_orientation_summary_describes_the_full_25_week_program():
    assert "24-week" not in ORIENTATION_SUMMARY
    assert "25-week" in ORIENTATION_SUMMARY


def test_seed_does_not_rewrite_existing_production_style_orientation(db):
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
    methodology = Lesson(
        module_id=module.id,
        title=METHODOLOGY_TITLE,
        summary="Existing methodology content",
        lesson_order=2,
        estimated_minutes=45,
        status="published",
    )
    db.add_all([orientation, methodology])
    db.commit()
    before = [
        (row.id, row.title, row.summary, row.lesson_order, row.estimated_minutes, row.required_notes_template, row.status)
        for row in db.query(Lesson).filter(Lesson.module_id == module.id).order_by(Lesson.id)
    ]

    seed_module0_and_methodology(db)
    db.commit()
    after = [
        (row.id, row.title, row.summary, row.lesson_order, row.estimated_minutes, row.required_notes_template, row.status)
        for row in db.query(Lesson).filter(Lesson.module_id == module.id).order_by(Lesson.id)
    ]

    assert after == before
