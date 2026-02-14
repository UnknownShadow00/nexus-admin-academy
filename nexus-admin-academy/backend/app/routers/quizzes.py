import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.schemas.quiz import QuizSubmitRequest
from app.services.xp_service import award_xp

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger(__name__)


def _ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None):
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload


@router.get("")
def get_quizzes(week_number: int | None = None, student_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Quiz).options(selectinload(Quiz.questions))
    if week_number is not None:
        query = query.filter(Quiz.week_number == week_number)
    quizzes = query.order_by(Quiz.created_at.desc()).all()

    attempts_by_quiz = {}
    if student_id is not None:
        attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).all()
        attempts_by_quiz = {attempt.quiz_id: attempt for attempt in attempts}

    data = []
    for quiz in quizzes:
        attempt = attempts_by_quiz.get(quiz.id)
        if attempt:
            status = "completed"
            best_score = attempt.best_score
            first_attempt_xp = attempt.first_attempt_xp
        else:
            status = "not_started"
            best_score = None
            first_attempt_xp = None

        data.append(
            {
                "id": quiz.id,
                "title": quiz.title,
                "week_number": quiz.week_number,
                "question_count": len(quiz.questions),
                "status": status,
                "best_score": best_score,
                "first_attempt_xp": first_attempt_xp,
                "retake_available": attempt is not None,
            }
        )

    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{quiz_id}")
def get_quiz_details(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return _ok(
        {
            "id": quiz.id,
            "title": quiz.title,
            "questions": [
                {
                    "id": question.id,
                    "question_text": question.question_text,
                    "option_a": question.option_a,
                    "option_b": question.option_b,
                    "option_c": question.option_c,
                    "option_d": question.option_d,
                }
                for question in quiz.questions
            ],
        }
    )


@router.post("/{quiz_id}/submit")
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    score = 0
    results = []
    for question in quiz.questions:
        submitted_answer = payload.answers.get(str(question.id))
        is_correct = submitted_answer == question.correct_answer
        if is_correct:
            score += 1
        results.append(
            {
                "question_id": question.id,
                "correct": is_correct,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
            }
        )

    existing = db.query(QuizAttempt).filter(QuizAttempt.student_id == student.id, QuizAttempt.quiz_id == quiz.id).first()

    if existing:
        existing.answers = payload.answers
        existing.score = score
        existing.best_score = max(existing.best_score or 0, score)
        existing.xp_awarded = existing.first_attempt_xp or existing.xp_awarded
        db.commit()
        logger.info("quiz_retake student_id=%s quiz_id=%s score=%s", student.id, quiz.id, score)
        return _ok(
            {
                "score": score,
                "total": len(quiz.questions),
                "xp_awarded": 0,
                "is_first_attempt": False,
                "best_score": existing.best_score,
                "first_attempt_xp": existing.first_attempt_xp or 0,
                "message": "Score updated (no XP for retakes)",
                "results": results,
            }
        )

    awarded_xp = score * 10
    attempt = QuizAttempt(
        student_id=student.id,
        quiz_id=quiz.id,
        answers=payload.answers,
        score=score,
        xp_awarded=awarded_xp,
        best_score=score,
        first_attempt_xp=awarded_xp,
    )
    db.add(attempt)
    db.flush()

    award_xp(
        db,
        student_id=student.id,
        delta=awarded_xp,
        source_type="quiz",
        source_id=attempt.id,
        description=f"Quiz: {quiz.title} (Score: {score}/10)",
    )

    db.commit()
    logger.info("quiz_first_attempt student_id=%s quiz_id=%s score=%s xp_awarded=%s", student.id, quiz.id, score, awarded_xp)

    return _ok(
        {
            "score": score,
            "total": len(quiz.questions),
            "xp_awarded": awarded_xp,
            "is_first_attempt": True,
            "best_score": score,
            "first_attempt_xp": awarded_xp,
            "message": "Great work!",
            "results": results,
        }
    )
