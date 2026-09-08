"""One V1 credit gate for both question delivery and submission.

Review is intentionally separate. An earned pass remains earned when teaching
requirements change; optional practice is not restricted by this policy.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.student import Student
from app.models.training import TrainingWeekActivity
from app.services.quiz_progression import is_quiz_passed


def prerequisite_error(title: str, missing: str, route: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "success": False,
            "code": "PREREQUISITE_NOT_MET",
            "error": f"Complete {missing} before {title}.",
            "data": {"missing_prerequisite": missing, "next_action_route": route},
        },
    )


def require_quiz_access(db: Session, student: Student, quiz: Quiz) -> None:
    from app.services.progression_service import require_week_reached
    from app.services.training_service import (
        build_training_overview,
        build_training_week,
    )

    mapped = (
        db.query(TrainingWeekActivity)
        .filter_by(activity_type="quiz", content_ref=str(quiz.id), is_required=True)
        .all()
    )
    if not quiz.is_required and not mapped:
        return
    if student.is_mentor or is_quiz_passed(db, student.id, quiz):
        return
    # Evaluate every credit-bearing mapping, so a permissive duplicate cannot
    # provide a route around the actual required module.
    weeks = {item.week.week_number for item in mapped}
    weeks.add(quiz.week_number or 0)
    if quiz.prerequisite_week is not None:
        weeks.add(quiz.prerequisite_week)
    for number in sorted(weeks):
        week = build_training_week(db, student, number)
        if week and week["locked"]:
            overview = build_training_overview(db, student)
            next_item = overview.get("next_activity") or {}
            raise prerequisite_error(
                quiz.title,
                next_item.get("title") or "the current module’s required work",
                next_item.get("destination_route") or "/learning-path",
            )
        require_week_reached(db, student, number)
        for item in (week or {}).get("activities", []):
            if (
                item["activity_type"] == "quiz"
                and item["content_ref"] == str(quiz.id)
                and item["status"] == "locked"
            ):
                raise prerequisite_error(
                    quiz.title,
                    item.get("prerequisite_title") or "the required teaching",
                    item.get("recovery_route") or "/learning-path",
                )
    # Some historical quizzes have a lesson association but no activity row.
    if quiz.lesson_id:
        from app.models.lesson_progress import StudentLessonProgress
        from app.models.learning import Lesson

        completed = (
            db.query(StudentLessonProgress.id)
            .filter_by(student_id=student.id, lesson_id=quiz.lesson_id)
            .filter(StudentLessonProgress.completed_at.isnot(None))
            .first()
        )
        if not completed:
            lesson = db.get(Lesson, quiz.lesson_id)
            raise prerequisite_error(
                quiz.title,
                lesson.title if lesson else "the required lesson",
                f"/lessons/{quiz.lesson_id}",
            )
