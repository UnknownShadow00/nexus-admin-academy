import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.schemas.quiz import (
    QuizDetailResponse,
    QuizListItem,
    QuizListResponse,
    QuizResultItem,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services.xp_calculator import quiz_xp

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger(__name__)


@router.get("", response_model=QuizListResponse)
def get_quizzes(week_number: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Quiz).options(selectinload(Quiz.questions))
    if week_number is not None:
        query = query.filter(Quiz.week_number == week_number)
    quizzes = query.order_by(Quiz.created_at.desc()).all()
    return QuizListResponse(
        quizzes=[
            QuizListItem(
                id=q.id,
                title=q.title,
                week_number=q.week_number,
                question_count=len(q.questions),
            )
            for q in quizzes
        ]
    )


@router.get("/{quiz_id}", response_model=QuizDetailResponse)
def get_quiz_details(quiz_id: int, db: Session = Depends(get_db)):
    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return QuizDetailResponse(
        id=quiz.id,
        title=quiz.title,
        questions=[
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
    )


@router.post("/{quiz_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db)):
    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    score = 0
    results: list[QuizResultItem] = []
    for question in quiz.questions:
        submitted_answer = payload.answers.get(str(question.id))
        is_correct = submitted_answer == question.correct_answer
        if is_correct:
            score += 1
        results.append(
            QuizResultItem(
                question_id=question.id,
                correct=is_correct,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )
        )

    awarded_xp = quiz_xp(score)
    student.total_xp += awarded_xp

    attempt = QuizAttempt(
        student_id=student.id,
        quiz_id=quiz.id,
        answers=payload.answers,
        score=score,
        xp_awarded=awarded_xp,
    )
    db.add(attempt)
    db.commit()
    logger.info(
        "quiz_submission student_id=%s quiz_id=%s score=%s xp_awarded=%s",
        student.id,
        quiz.id,
        score,
        awarded_xp,
    )

    return QuizSubmitResponse(score=score, total=len(quiz.questions), xp_awarded=awarded_xp, results=results)
