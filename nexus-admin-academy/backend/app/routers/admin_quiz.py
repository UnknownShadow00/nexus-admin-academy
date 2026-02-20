import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Question, Quiz
from app.schemas.quiz import QuizGenerateRequest
from app.services.admin_auth import verify_admin
from app.services.quiz_generator import generate_quiz_from_videos
from app.utils.responses import ok

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)


@router.post("/quiz/generate")
async def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db)):
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
    logger.info(
        "admin_quiz_generated quiz_id=%s week=%s title=%s source_count=%s question_count=%s",
        quiz.id,
        payload.week_number,
        payload.title,
        len(urls),
        payload.question_count,
    )
    return ok({"quiz_id": quiz.id, "message": f"Quiz '{payload.title}' created with {payload.question_count} questions"})


@router.get("/quizzes")
def list_quizzes(db: Session = Depends(get_db)):
    rows = db.query(Quiz).order_by(Quiz.created_at.desc()).limit(50).all()
    return ok(
        [
            {
                "id": row.id,
                "title": row.title,
                "week_number": row.week_number,
                "question_count": row.question_count,
                "source_urls": row.source_urls or ([row.source_url] if row.source_url else []),
                "lesson_id": row.lesson_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    )


@router.delete("/quizzes/{quiz_id}")
def delete_quiz(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    db.delete(quiz)
    db.commit()
    return ok({"deleted": True})
