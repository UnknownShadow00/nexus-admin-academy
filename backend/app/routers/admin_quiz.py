import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Question, Quiz
from app.schemas.quiz import QuizGenerateRequest, QuizUpdateRequest
from app.services.admin_auth import verify_admin
from app.services.examcompass_scraper import scrape_examcompass_quiz
from app.services.quiz_generator import generate_quiz_from_videos
from app.utils.responses import ok


def _normalize_examcompass_title(raw: str) -> str:
    import re as _re
    title = _re.sub(r"\s*[|\-]\s*ExamCompass.*$", "", raw, flags=_re.IGNORECASE)
    title = _re.sub(r"\s*\|.*$", "", title)
    title = _re.sub(r"^[^:]+:\s*", "", title)
    title = title.strip()
    return title if len(title) >= 3 else raw.strip()


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
                option_e=q.get("option_e", "") or None,
                option_f=q.get("option_f", "") or None,
                option_g=q.get("option_g", "") or None,
                option_h=q.get("option_h", "") or None,
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
                "status": row.status,
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


@router.patch("/quizzes/{quiz_id}")
def update_quiz(quiz_id: int, payload: QuizUpdateRequest, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    updated = {}
    if payload.title is not None:
        quiz.title = payload.title
        updated["title"] = quiz.title

    if payload.week_number is not None:
        quiz.week_number = payload.week_number
        updated["week_number"] = quiz.week_number

    if payload.domain_id is not None:
        quiz.domain_id = payload.domain_id
        updated["domain_id"] = quiz.domain_id

    if payload.status is not None:
        quiz.status = payload.status
        updated["status"] = quiz.status

    db.commit()
    return ok(
        {
            "id": quiz.id,
            "title": quiz.title,
            "week_number": quiz.week_number,
            "domain_id": quiz.domain_id,
            "status": quiz.status,
            **updated,
        }
    )


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
                option_e=question.get("option_e", "") or None,
                option_f=question.get("option_f", "") or None,
                option_g=question.get("option_g", "") or None,
                option_h=question.get("option_h", "") or None,
                correct_answer=question.get("correct_answer", "A"),
                explanation=question.get("explanation", ""),
            )
        )
        saved_count += 1

    db.commit()
    return ok({"quiz_id": quiz.id, "question_count": saved_count, "title": quiz.title})


@router.post("/quiz/bookmarklet-import")
async def bookmarklet_import(payload: dict, db: Session = Depends(get_db)):
    """
    Receives questions extracted by the bookmarklet running in the user's browser.
    Payload: { title, source_url, week_number, lesson_id, questions: [...] }
    """
    questions = payload.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="No questions received")

    raw_title = (payload.get("title", "") or "").strip()
    title = _normalize_examcompass_title(raw_title) or raw_title or "ExamCompass Import"
    source_url = payload.get("source_url", "")

    quiz = Quiz(
        title=title,
        source_url=source_url,
        source_urls=[source_url] if source_url else [],
        week_number=int(payload.get("week_number", 1)),
        question_count=len(questions),
        lesson_id=payload.get("lesson_id") or None,
        domain_id=payload.get("domain_id", "1.0"),
    )
    db.add(quiz)
    db.flush()

    saved = 0
    for question in questions:
        if not question.get("question_text") or not question.get("option_a"):
            continue
        all_correct = question.get("all_correct_answers", [])
        if isinstance(all_correct, str):
            all_correct = [item.strip() for item in all_correct.split(",") if item.strip()]

        primary_correct = all_correct[0] if all_correct else question.get("correct_answer", "A")
        allowed_answers = ["A", "B", "C", "D", "E", "F", "G", "H"]
        if primary_correct not in allowed_answers:
            primary_correct = "A"
        if primary_correct != "A" and not question.get(f"option_{primary_correct.lower()}"):
            primary_correct = "A"

        correct_answers_str = ",".join(all_correct) if len(all_correct) > 1 else None
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=question["question_text"],
                option_a=question["option_a"],
                option_b=question.get("option_b", ""),
                option_c=question.get("option_c", ""),
                option_d=question.get("option_d", ""),
                option_e=question.get("option_e", "") or None,
                option_f=question.get("option_f", "") or None,
                option_g=question.get("option_g", "") or None,
                option_h=question.get("option_h", "") or None,
                correct_answer=primary_correct,
                correct_answers=correct_answers_str,
                explanation=question.get("explanation", ""),
            )
        )
        saved += 1

    db.commit()
    logger.info("bookmarklet_import quiz_id=%s questions=%s title=%s", quiz.id, saved, title)
    return ok({"quiz_id": quiz.id, "question_count": saved, "title": title})


@router.get("/quizzes/{quiz_id}/questions")
def get_quiz_questions(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = db.query(Question).filter(Question.quiz_id == quiz_id).order_by(Question.id.asc()).all()
    return ok(
        {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "status": quiz.status,
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
                    "correct_answer": question.correct_answer,
                    "correct_answers": question.correct_answers,
                    "explanation": question.explanation or "",
                }
                for question in questions
            ],
        }
    )


@router.put("/questions/{question_id}")
def update_question(question_id: int, payload: dict, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    for field in [
        "correct_answer",
        "correct_answers",
        "explanation",
        "question_text",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "option_e",
        "option_f",
        "option_g",
        "option_h",
    ]:
        if field in payload:
            setattr(question, field, payload[field])
    db.commit()
    return ok({"updated": True})
