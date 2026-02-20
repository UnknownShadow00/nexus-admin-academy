import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Question, Quiz
from app.schemas.quiz import QuizGenerateRequest
from app.services.admin_auth import verify_admin
from app.services.examcompass_scraper import scrape_examcompass_quiz
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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


@router.post("/quiz/scrape-preview")
async def scrape_quiz_preview(payload: dict):
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        result = await scrape_examcompass_quiz(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("scrape_failed url=%s", url)
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc

    return ok(result)


@router.post("/quiz/scrape-save")
async def scrape_quiz_save(payload: dict, db: Session = Depends(get_db)):
    questions = payload.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="No questions provided")

    quiz = Quiz(
        title=payload.get("title", "Imported Quiz"),
        source_url=payload.get("source_url"),
        week_number=payload.get("week_number", 1),
        question_count=len(questions),
        lesson_id=payload.get("lesson_id"),
        domain_id=payload.get("domain_id", "1.0"),
    )
    db.add(quiz)
    db.flush()

    saved_count = 0
    for question in questions:
        if not question.get("question_text") or not question.get("option_a"):
            continue
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=question["question_text"],
                option_a=question["option_a"],
                option_b=question.get("option_b", ""),
                option_c=question.get("option_c", ""),
                option_d=question.get("option_d", ""),
                correct_answer=question.get("correct_answer", "A"),
                explanation=question.get("explanation", ""),
            )
        )
        saved_count += 1

    db.commit()
    return ok({"quiz_id": quiz.id, "question_count": saved_count, "title": quiz.title})
