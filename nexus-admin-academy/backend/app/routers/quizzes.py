import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.student import Student
from app.schemas.quiz import QuizGenerateRequest, QuizSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.mastery_service import record_quiz_mastery
from app.services.quiz_generator import generate_quiz_from_videos
from app.services.xp_service import award_xp
from app.utils.responses import ok

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger(__name__)


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
                "attempt_count": 1 if attempt else 0,
                "retake_available": attempt is not None,
            }
        )

    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{quiz_id}")
def get_quiz_details(quiz_id: int, student_id: int | None = None, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempts = []
    if student_id:
        rows = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student_id)
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
                }
                for question in quiz.questions
            ],
            "attempts": attempts,
        }
    )


@router.post("/admin/generate")
async def admin_generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db)):
    urls = [str(url) for url in payload.source_urls]
    try:
        questions = await generate_quiz_from_videos(
            video_urls=urls,
            title=payload.title,
            week_number=payload.week_number,
            question_count=payload.question_count,
            db=db,
            admin_id=0,
            domain_id=payload.domain_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Quiz generation failed: {exc}") from exc

    quiz = Quiz(
        title=payload.title,
        source_url=urls[0],
        source_urls=urls,
        week_number=payload.week_number,
        question_count=payload.question_count,
        domain_id=payload.domain_id,
        lesson_id=payload.lesson_id,
    )
    db.add(quiz)
    db.flush()

    for q in questions:
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
            )
        )

    db.commit()
    return ok({"quiz_id": quiz.id, "message": f"Quiz '{payload.title}' created with {payload.question_count} questions"})


@router.post("/{quiz_id}/submit")
def submit_quiz(quiz_id: int, payload: QuizSubmitRequest, db: Session = Depends(get_db)):
    student_id = payload.student_id
    answers = payload.answers

    quiz = db.query(Quiz).options(selectinload(Quiz.questions)).filter(Quiz.id == quiz_id).first()
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

    for i, question in enumerate(questions, start=1):
        student_answer = answers.get(str(i)) or answers.get(str(question.id))
        correct_answer = question.correct_answer
        is_correct = student_answer == correct_answer
        if is_correct:
            correct_count += 1

        results.append(
            {
                "question_id": question.id,
                "question_number": i,
                "question_text": question.question_text,
                "student_answer": student_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": question.explanation,
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d,
                },
            }
        )

    score = correct_count
    existing = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id, QuizAttempt.quiz_id == quiz_id).first()

    is_first_attempt = existing is None
    xp_awarded = score * 10 if is_first_attempt else 0

    if is_first_attempt:
        attempt = QuizAttempt(
            student_id=student_id,
            quiz_id=quiz_id,
            answers=answers,
            score=score,
            xp_awarded=xp_awarded,
            best_score=score,
            first_attempt_xp=xp_awarded,
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
        record_quiz_mastery(db, student_id, quiz.domain_id, score)
        log_activity(db, student_id, "quiz_passed", quiz.title, f"Score {score}/{total_questions}")
    else:
        existing.answers = answers
        existing.score = score
        existing.best_score = max(existing.best_score or 0, score)
        db.commit()

    if is_first_attempt:
        db.commit()

    return ok(
        {
            "score": score,
            "total": total_questions,
            "xp_awarded": xp_awarded,
            "is_first_attempt": is_first_attempt,
            "results": results,
            "message": "Great work!" if is_first_attempt else "Score updated (no XP for retakes)",
        }
    )
