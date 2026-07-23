from sqlalchemy.orm import Session

from app.models.evidence import EvidenceArtifact
from app.models.lesson_notes import StudentLessonNote
from app.models.learning import Lesson, Module
from app.models.onboarding import StudentOnboardingPractice
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.models.ticket import TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.progression_service import derive_current_week

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
    lesson_note = None
    if lesson:
        lesson_note = (
            db.query(StudentLessonNote)
            .filter(StudentLessonNote.student_id == student.id, StudentLessonNote.lesson_id == lesson.id)
            .first()
        )
    quiz_taken = bool(
        quiz
        and db.query(QuizAttempt.id)
        .filter(QuizAttempt.student_id == student.id, QuizAttempt.quiz_id == quiz.id)
        .first()
    )
    practice = (
        db.query(StudentOnboardingPractice)
        .filter(StudentOnboardingPractice.student_id == student.id)
        .first()
    )
    evidence_uploaded = bool(
        lesson
        and db.query(EvidenceArtifact.id)
        .filter(
            EvidenceArtifact.student_id == student.id,
            EvidenceArtifact.submission_type == "orientation",
            EvidenceArtifact.submission_id == lesson.id,
        )
        .first()
    )
    lesson_complete = bool(lesson_note and (lesson_note.content or "").strip())
    practice_complete = bool(practice and (practice.response or "").strip())
    week_one_unlocked = derive_current_week(student.id, db) >= 1
    complete = bool(lesson_complete and quiz_taken and practice_complete)
    remaining_week_zero_lessons = []
    if complete and lesson:
        completed_lesson_ids = {
            row.lesson_id
            for row in db.query(StudentLessonNote.lesson_id).filter(
                StudentLessonNote.student_id == student.id
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
        lesson_note
        or quiz_taken
        or practice
        or evidence_uploaded
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
            "lesson_note": lesson_complete,
            "quiz": quiz_taken,
            "practice_response": practice_complete,
            "optional_evidence": evidence_uploaded,
        },
    }
