from sqlalchemy.orm import Session

from app.models.lesson_notes import StudentLessonNote
from app.models.lesson_progress import StudentLessonProgress
from app.models.learning import Lesson, Module
from app.models.quiz import Quiz
from app.models.student import Student
from app.models.ticket import TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.progression_service import derive_current_week
from app.services.quiz_progression import is_quiz_passed

ORIENTATION_LESSON_TITLE = "Welcome to Nexus: Your First Week"
ORIENTATION_QUIZ_TITLE = "Ticketing Systems Quiz"


def get_orientation_lesson(db: Session) -> Lesson | None:
    return (
        db.query(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.code == "MOD-000", Lesson.title == ORIENTATION_LESSON_TITLE)
        .first()
    )


def get_orientation_quiz(db: Session) -> Quiz | None:
    return db.query(Quiz).filter(Quiz.week_number == 0, Quiz.title == ORIENTATION_QUIZ_TITLE).first()


def get_orientation_state(db: Session, student: Student) -> dict:
    """Build server-backed walkthrough state from the real learning primitives."""
    lesson = get_orientation_lesson(db)
    quiz = get_orientation_quiz(db)
    lesson_progress = None
    if lesson:
        lesson_progress = (
            db.query(StudentLessonProgress)
            .filter(
                StudentLessonProgress.student_id == student.id,
                StudentLessonProgress.lesson_id == lesson.id,
                StudentLessonProgress.completed_at.isnot(None),
            )
            .first()
        )
    quiz_passed = bool(quiz and is_quiz_passed(db, student.id, quiz))
    lesson_complete = lesson_progress is not None
    week_one_unlocked = derive_current_week(student.id, db) >= 1
    complete = bool(lesson_complete and quiz_passed)
    remaining_week_zero_lessons = []
    if complete and lesson:
        completed_lesson_ids = {
            row.lesson_id
            for row in db.query(StudentLessonProgress.lesson_id).filter(
                StudentLessonProgress.student_id == student.id,
                StudentLessonProgress.completed_at.isnot(None),
            )
        }
        remaining_week_zero_lessons = [
            {
                "id": row.id,
                "title": row.title,
                "route": f"/lessons/{row.id}",
            }
            for row in (
                db.query(Lesson)
                .join(Module, Module.id == Lesson.module_id)
                .filter(
                    Module.code == "MOD-000",
                    Lesson.status == "published",
                    Lesson.id != lesson.id,
                )
                .order_by(Lesson.lesson_order, Lesson.id)
                .all()
            )
            if row.id not in completed_lesson_ids
        ]
    has_activity = bool(
        db.query(StudentLessonNote.id).filter(StudentLessonNote.student_id == student.id).first()
        or lesson_progress
        or quiz_passed
        or db.query(XPLedger.id).filter(XPLedger.student_id == student.id).first()
        or db.query(TicketSubmission.id).filter(TicketSubmission.student_id == student.id).first()
    )
    return {
        "available": bool(lesson and quiz),
        "is_fresh": bool(student.total_xp == 0 and not has_activity),
        "is_complete": complete,
        "week_one_unlocked": week_one_unlocked,
        "week_one_remaining_lessons": remaining_week_zero_lessons,
        "available_later": bool(lesson),
        "lesson_id": lesson.id if lesson else None,
        "lesson_title": lesson.title if lesson else None,
        "lesson_route": f"/lessons/{lesson.id}" if lesson else "/training",
        "quiz_id": quiz.id if quiz else None,
        "quiz_route": f"/quizzes/{quiz.id}" if quiz else "/quizzes",
        "next_week_plan_url": "/api/students/me/week-plan?week=1",
        "steps": {
            "lesson_completion": lesson_complete,
            "quiz": quiz_passed,
        },
    }
