from datetime import datetime

import pytest

from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
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
            db.add(StudentLessonNote(student_id=student.id, lesson_id=lesson.id, content="done"))
    db.commit()


@pytest.mark.parametrize("target_week", [1, 2, 5])
def test_stats_uses_existing_progression_week(db, target_week):
    student = make_student(db)
    student.created_at = datetime(2026, 1, 1, 12, 0, 0)  # legacy timezone-naive value
    _seed_progression(db, student, target_week)

    response = client.get(f"/api/students/{student.id}/stats", headers=auth_headers(student))

    assert response.status_code == 200, response.text
    assert response.json()["current_week"] == target_week
