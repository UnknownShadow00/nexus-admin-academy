import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.student import Student
from app.schemas.quiz import QuizSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import ensure_student_access, get_current_student
from app.services.fsrs_service import create_cards_for_wrong_answers
from app.services.mastery_service import record_quiz_mastery
from app.services.xp_service import award_xp
from app.utils.responses import ok

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger(__name__)


def _avg_seconds_per_question(time_per_question: dict | None) -> float | None:
    if not time_per_question:
        return None
    values = [value for value in time_per_question.values() if isinstance(value, (int, float))]
    if not values:
        return None
    return sum(values) / len(values)


@router.get("")
def get_quizzes(week_number: int | None = None, student_id: int | None = None, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    scoped_student_id = student_id or current_student.id
    ensure_student_access(current_student, scoped_student_id)
    query = db.query(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.status == QUIZ_STATUS_PUBLISHED)
    if week_number is not None:
        query = query.filter(Quiz.week_number == week_number)
    quizzes = query.order_by(Quiz.created_at.desc()).all()

    attempts_by_quiz = {}
    attempt_counts_by_quiz = {}
    if scoped_student_id is not None:
        attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == scoped_student_id).all()
        attempts_by_quiz = {attempt.quiz_id: attempt for attempt in attempts}
        attempt_counts = (
            db.query(QuizAttempt.quiz_id, func.count(QuizAttempt.id))
            .filter(QuizAttempt.student_id == scoped_student_id)
            .group_by(QuizAttempt.quiz_id)
            .all()
        )
        attempt_counts_by_quiz = {quiz_id: count for quiz_id, count in attempt_counts}

    data = []
    for quiz in quizzes:
        attempt = attempts_by_quiz.get(quiz.id)
        attempt_count = attempt_counts_by_quiz.get(quiz.id, 0) if scoped_student_id else 0
        data.append(
            {
                "id": quiz.id,
                "title": quiz.title,
                "week_number": quiz.week_number,
                "domain_id": quiz.domain_id,
                "lesson_id": quiz.lesson_id,
                "question_count": quiz.question_count or len(quiz.questions),
                "video_count": len(quiz.source_urls or ([quiz.source_url] if quiz.source_url else [])),
                "status": "completed" if attempt else "not_started",
                "best_score": attempt.best_score if attempt else None,
                "first_attempt_xp": attempt.first_attempt_xp if attempt else None,
                "attempt_count": attempt_count,
                "retake_available": attempt is not None,
            }
        )

    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{quiz_id}")
def get_quiz_details(quiz_id: int, student_id: int | None = None, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    scoped_student_id = student_id or current_student.id
    ensure_student_access(current_student, scoped_student_id)
    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, Quiz.status == QUIZ_STATUS_PUBLISHED)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempts = []
    if scoped_student_id:
        rows = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == scoped_student_id)
            .order_by(QuizAttempt.completed_at.asc())
            .all()
        )
        attempts = [
            {
                "attempt_number": i + 1,
                "score": row.score,
                "total": quiz.question_count or len(quiz.questions),
                "xp_awarded": row.xp_awarded or 0,
                "is_first_attempt": i == 0,
                "created_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for i, row in enumerate(rows)
        ]

    return ok(
        {
            "id": quiz.id,
            "title": quiz.title,
            "week_number": quiz.week_number,
            "domain_id": quiz.domain_id,
            "lesson_id": quiz.lesson_id,
            "question_count": quiz.question_count or len(quiz.questions),
            "source_urls": quiz.source_urls or ([quiz.source_url] if quiz.source_url else []),
            "questions": [
                {
                    "id": question.id,
                    "question_text": question.question_text,
                    "option_a": question.option_a,
                    "option_b": question.option_b,
                    "option_c": question.option_c,
                    "option_d": question.option_d,
                    "option_e": question.option_e or "",
                    "option_f": question.option_f or "",
                    "option_g": question.option_g or "",
                    "option_h": question.option_h or "",
                    "is_multi_select": question.is_multi_select,
                }
                for question in quiz.questions
            ],
            "attempts": attempts,
        }
    )


@router.post("/{quiz_id}/submit")
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    student_id = payload.student_id
    ensure_student_access(current_student, student_id)
    answers = payload.answers
    time_per_question = payload.time_per_question
    avg_seconds = _avg_seconds_per_question(time_per_question)

    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, Quiz.status == QUIZ_STATUS_PUBLISHED)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    mark_student_active(db, student_id)

    questions = sorted(quiz.questions, key=lambda q: q.id)
    total_questions = len(questions)
    if total_questions < 1:
        raise HTTPException(status_code=500, detail="Invalid quiz (no questions)")

    results = []
    correct_count = 0
    wrong_question_ids = []

    for i, question in enumerate(questions, start=1):
        raw_answer = answers.get(str(question.id)) or answers.get(str(i))
        correct_letters = question.all_correct_answers
        if question.is_multi_select:
            # TB-06 fix: ALWAYS compare as sets for multi-select. Previously a
            # single-letter answer (no comma) fell through to `in correct_letters`
            # and earned full credit for a partial answer.
            student_letters = sorted(
                letter.strip().upper()
                for letter in str(raw_answer or "").split(",")
                if letter.strip()
            )
            is_correct = bool(student_letters) and student_letters == sorted(
                letter.strip().upper() for letter in correct_letters
            )
            student_answer = raw_answer
        else:
            student_answer = raw_answer
            is_correct = student_answer in correct_letters
        if is_correct:
            correct_count += 1
        else:
            wrong_question_ids.append(question.id)

        results.append(
            {
                "question_id": question.id,
                "question_number": i,
                "question_text": question.question_text,
                "student_answer": student_answer,
                "correct_answer": question.correct_answer,
                "correct_answers": question.all_correct_answers,
                "is_multi_select": question.is_multi_select,
                "is_correct": is_correct,
                "explanation": question.explanation or "",
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d,
                    "E": question.option_e or "",
                    "F": question.option_f or "",
                    "G": question.option_g or "",
                    "H": question.option_h or "",
                },
            }
        )

    score = correct_count
    # TB-06: every attempt is a new row (migration c2d3e4f5a6b7 dropped uq_student_quiz).
    prior_attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == student_id, QuizAttempt.quiz_id == quiz_id)
        .all()
    )
    is_first_attempt = len(prior_attempts) == 0
    prior_best = max((a.score or 0) for a in prior_attempts) if prior_attempts else 0
    # XP policy unchanged: only the first attempt earns quiz XP.
    xp_awarded = round((score / total_questions) * 100) if is_first_attempt else 0

    attempt = QuizAttempt(
        student_id=student_id,
        quiz_id=quiz_id,
        answers=answers,
        results=results,
        score=score,
        xp_awarded=xp_awarded,
        best_score=max(prior_best, score),
        # live DB column is NOT NULL DEFAULT 0 (migration 0002) — 0, not None, on retakes
        first_attempt_xp=xp_awarded if is_first_attempt else 0,
        time_per_question=time_per_question,
    )
    db.add(attempt)
    db.flush()

    if xp_awarded > 0:
        award_xp(
            db,
            student_id=student_id,
            delta=xp_awarded,
            source_type="quiz",
            source_id=attempt.id,
            description=f"Quiz: {quiz.title} (Score: {score}/{total_questions})",
        )
    # Mastery uses best-known score across attempts (documented rule: mastery=best,
    # speed-flags evaluate every attempt individually).
    record_quiz_mastery(db, student_id, quiz.domain_id, max(prior_best, score))
    log_activity(db, student_id, "quiz_passed", quiz.title, f"Score {score}/{total_questions}")
    create_cards_for_wrong_answers(db, student.id, wrong_question_ids)
    db.commit()

    return ok(
        {
            "score": score,
            "total": total_questions,
            "xp_awarded": xp_awarded,
            "is_first_attempt": is_first_attempt,
            "avg_seconds_per_question": round(avg_seconds, 1) if avg_seconds is not None else None,
            "is_speed_flagged": avg_seconds is not None and avg_seconds < 8,
            "results": results,
            "message": "Great work!" if is_first_attempt else "Score updated (no XP for retakes)",
        }
    )


@router.get("/{quiz_id}/review/{student_id}")
def get_quiz_review(quiz_id: int, student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    """Returns the student's last attempt results for review."""
    ensure_student_access(current_student, student_id)
    attempt = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student_id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="No attempt found for this quiz")

    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, Quiz.status == QUIZ_STATUS_PUBLISHED)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    avg_seconds = _avg_seconds_per_question(attempt.time_per_question)

    if attempt.results:
        return ok(
            {
                "quiz_id": quiz_id,
                "title": quiz.title,
                "score": attempt.score,
                "total": len(quiz.questions),
                "xp_awarded": attempt.xp_awarded,
                "is_first_attempt": (attempt.first_attempt_xp or 0) > 0,
                "avg_seconds_per_question": round(avg_seconds, 1) if avg_seconds is not None else None,
                "is_speed_flagged": avg_seconds is not None and avg_seconds < 8,
                "results": attempt.results,
                "questions": [
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "option_a": q.option_a,
                        "option_b": q.option_b,
                        "option_c": q.option_c,
                        "option_d": q.option_d,
                        "option_e": q.option_e or "",
                        "option_f": q.option_f or "",
                        "option_g": q.option_g or "",
                        "option_h": q.option_h or "",
                        "correct_answer": q.correct_answer,
                        "correct_answers": q.all_correct_answers,
                        "explanation": q.explanation or "",
                    }
                    for q in sorted(quiz.questions, key=lambda x: x.id)
                ],
            }
        )

    stored_answers = attempt.answers or {}
    questions = sorted(quiz.questions, key=lambda q: q.id)
    results = []
    for i, question in enumerate(questions, start=1):
        student_answer = stored_answers.get(str(question.id)) or stored_answers.get(str(i))
        results.append(
            {
                "question_id": question.id,
                "question_number": i,
                "question_text": question.question_text,
                "student_answer": student_answer,
                "correct_answer": question.correct_answer,
                "correct_answers": question.all_correct_answers,
                "is_multi_select": question.is_multi_select,
                "is_correct": student_answer in question.all_correct_answers,
                "explanation": question.explanation or "",
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d,
                    "E": question.option_e or "",
                    "F": question.option_f or "",
                    "G": question.option_g or "",
                    "H": question.option_h or "",
                },
            }
        )

    return ok(
        {
            "quiz_id": quiz_id,
            "title": quiz.title,
            "score": attempt.score,
            "total": len(questions),
            "xp_awarded": attempt.xp_awarded,
            "is_first_attempt": False,
            "avg_seconds_per_question": round(avg_seconds, 1) if avg_seconds is not None else None,
            "is_speed_flagged": avg_seconds is not None and avg_seconds < 8,
            "results": results,
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "option_a": q.option_a,
                    "option_b": q.option_b,
                    "option_c": q.option_c,
                    "option_d": q.option_d,
                    "option_e": q.option_e or "",
                    "option_f": q.option_f or "",
                    "option_g": q.option_g or "",
                    "option_h": q.option_h or "",
                    "correct_answer": q.correct_answer,
                    "correct_answers": q.all_correct_answers,
                    "explanation": q.explanation or "",
                }
                for q in questions
            ],
        }
    )
