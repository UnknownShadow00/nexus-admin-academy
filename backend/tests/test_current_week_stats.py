from datetime import datetime, timezone

import pytest

from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import Quiz
from app.routers.students import router as students_router
from conftest import auth_headers, make_client, make_student


client = make_client(students_router)


def _seed_progression(db, student, target_week):
    for week in range(1, target_week + 1):
        module = Module(code=f"MOD-{week:03d}", title=f"Week {week}", module_order=week)
        db.add(module)
        db.flush()
        lesson = Lesson(
            module_id=module.id,
            title=f"Week {week} lesson",
            lesson_order=1,
            status="published",
        )
        db.add(lesson)
        db.flush()
        if week < target_week:
            db.add(StudentLessonProgress(student_id=student.id, lesson_id=lesson.id, completed_at=datetime.now(timezone.utc)))
    db.commit()


@pytest.mark.parametrize("target_week", [1, 2, 5])
def test_stats_uses_existing_progression_week(db, target_week):
    student = make_student(db)
    student.created_at = datetime(2026, 1, 1, 12, 0, 0)  # legacy timezone-naive value
    _seed_progression(db, student, target_week)

    response = client.get(f"/api/students/{student.id}/stats", headers=auth_headers(student))

    assert response.status_code == 200, response.text
    assert response.json()["current_week"] == target_week


def test_stats_counts_required_quizzes_across_the_full_curriculum(db):
    student = make_student(db, username="full-curriculum-stats")
    db.add(
        Quiz(
            title="Endpoint lifecycle check",
            question_count=1,
            week_number=34,
            status="published",
            quiz_purpose="required",
            is_required=True,
            show_in_weekly_checklist=True,
            answer_keys_validated=True,
            is_active=True,
        )
    )
    db.commit()

    response = client.get(f"/api/students/{student.id}/stats", headers=auth_headers(student))

    assert response.status_code == 200, response.text
    assert response.json()["total_quizzes"] == 1
