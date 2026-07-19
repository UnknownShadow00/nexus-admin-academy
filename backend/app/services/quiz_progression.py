from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.quiz import (
    EDITORIAL_STATUS_ARCHIVED,
    QUIZ_PURPOSE_REMEDIATION,
    QUIZ_STATUS_PUBLISHED,
    Quiz,
    QuizAssignment,
    QuizAttempt,
)

QUIZ_PASS_PERCENT = 70


def required_quizzes_for_week(db: Session, week: int) -> list[Quiz]:
    """Return only active, published quizzes that intentionally gate this week."""
    return (
        db.query(Quiz)
        .filter(
            Quiz.week_number == week,
            Quiz.status == QUIZ_STATUS_PUBLISHED,
            Quiz.is_active.is_(True),
            Quiz.editorial_status != EDITORIAL_STATUS_ARCHIVED,
            Quiz.is_required.is_(True),
            Quiz.show_in_weekly_checklist.is_(True),
            Quiz.answer_keys_validated.is_(True),
        )
        .order_by(Quiz.id)
        .all()
    )


def best_quiz_score(db: Session, student_id: int, quiz_id: int) -> int:
    return int(
        db.query(func.coalesce(func.max(QuizAttempt.score), 0))
        .filter(QuizAttempt.student_id == student_id, QuizAttempt.quiz_id == quiz_id)
        .scalar()
        or 0
    )


def is_quiz_passed(db: Session, student_id: int, quiz: Quiz) -> bool:
    total = len(quiz.questions) if quiz.questions else int(quiz.question_count or 0)
    if total <= 0:
        return False
    return best_quiz_score(db, student_id, quiz.id) * 100 >= total * QUIZ_PASS_PERCENT


def assigned_remediation_ids(db: Session, student_id: int) -> set[int]:
    return {
        row.quiz_id
        for row in db.query(QuizAssignment.quiz_id).filter(
            QuizAssignment.student_id == student_id,
            QuizAssignment.is_active.is_(True),
        )
    }


def triggered_remediation_ids(db: Session, student_id: int) -> set[int]:
    """Trigger week-scoped remediation after a failed required quiz attempt."""
    failed_weeks = set()
    for quiz in db.query(Quiz).filter(Quiz.is_required.is_(True)).all():
        attempts = db.query(QuizAttempt.id).filter(
            QuizAttempt.student_id == student_id, QuizAttempt.quiz_id == quiz.id
        ).first()
        if attempts and not is_quiz_passed(db, student_id, quiz):
            failed_weeks.add(quiz.week_number)
    if not failed_weeks:
        return set()
    return {
        row.id
        for row in db.query(Quiz.id).filter(
            Quiz.quiz_purpose == QUIZ_PURPOSE_REMEDIATION,
            Quiz.week_number.in_(failed_weeks),
        )
    }
