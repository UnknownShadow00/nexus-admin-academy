import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import (
    EDITORIAL_STATUS_ARCHIVED,
    EDITORIAL_STATUS_NEEDS_EDIT,
    EDITORIAL_STATUS_UNREVIEWED,
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_PURPOSE_CERTIFICATION,
    SOURCE_TYPE_AI_GENERATED,
    SOURCE_TYPE_EXAMCOMPASS,
    SOURCE_TYPE_MANUAL,
    Question,
    Quiz,
)
from app.schemas.quiz import QuizGenerateRequest, QuizUpdateRequest
from app.schemas.admin_content import QuestionUpdate, QuizImportRequest, ScrapePreviewRequest
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
        quiz_purpose="practice",
        is_required=False,
        show_in_weekly_checklist=False,
        show_in_practice_library=False,
        editorial_status=EDITORIAL_STATUS_UNREVIEWED,
        source_type=SOURCE_TYPE_AI_GENERATED,
        answer_keys_validated=False,
        explanations_complete=all(bool(q.get("explanation", "").strip()) for q in questions),
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
def list_quizzes(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    week: int | None = Query(default=None, ge=0, le=24),
    purpose: str | None = None,
    source: str | None = None,
    editorial_status: str | None = None,
    required: bool | None = None,
    answer_keys_validated: bool | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Quiz)
    if search:
        query = query.filter(func.lower(Quiz.title).like(f"%{search.strip().lower()}%"))
    if week is not None:
        query = query.filter(Quiz.week_number == week)
    if purpose:
        query = query.filter(Quiz.quiz_purpose == purpose)
    if source:
        query = query.filter(Quiz.source_type == source)
    if editorial_status:
        query = query.filter(Quiz.editorial_status == editorial_status)
    if required is not None:
        query = query.filter(Quiz.is_required.is_(required))
    if answer_keys_validated is not None:
        query = query.filter(Quiz.answer_keys_validated.is_(answer_keys_validated))
    total = query.count()
    rows = query.order_by(Quiz.created_at.desc(), Quiz.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
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
                "quiz_purpose": row.quiz_purpose,
                "is_required": row.is_required,
                "show_in_weekly_checklist": row.show_in_weekly_checklist,
                "show_in_practice_library": row.show_in_practice_library,
                "editorial_status": row.editorial_status,
                "recommended_week": row.recommended_week,
                "prerequisite_week": row.prerequisite_week,
                "quality_score": row.quality_score,
                "source_type": row.source_type,
                "answer_keys_validated": row.answer_keys_validated,
                "explanations_complete": row.explanations_complete,
                "is_active": row.is_active,
            }
            for row in rows
        ], total=total, page=page, per_page=per_page
    )


@router.get("/quizzes/editorial-queue")
def editorial_review_queue(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    purpose: str | None = None,
    source: str | None = None,
    editorial_status: str | None = None,
    db: Session = Depends(get_db),
):
    """Admin-only queue of quizzes that cannot be shown to students yet."""
    missing_explanation = case(
        (func.trim(func.coalesce(Question.explanation, "")) == "", 1),
        else_=0,
    )
    query = (
        db.query(
            Quiz,
            func.count(Question.id).label("actual_question_count"),
            func.coalesce(func.sum(missing_explanation), 0).label("missing_explanations"),
        )
        .outerjoin(Question, Question.quiz_id == Quiz.id)
        .filter(
            or_(
                Quiz.answer_keys_validated.is_(False),
                Quiz.editorial_status != EDITORIAL_STATUS_VALIDATED,
            )
        )
    )
    if purpose:
        query = query.filter(Quiz.quiz_purpose == purpose)
    if source:
        query = query.filter(Quiz.source_type == source)
    if editorial_status:
        query = query.filter(Quiz.editorial_status == editorial_status)
    query = query.group_by(Quiz.id)
    total = query.count()
    priority = case(
        (Quiz.editorial_status == EDITORIAL_STATUS_ARCHIVED, 5),
        (Quiz.quiz_purpose == "practice", 1),
        (Quiz.quiz_purpose == "remediation", 2),
        (Quiz.quiz_purpose.in_(["cumulative", "gate"]), 3),
        (Quiz.quiz_purpose == QUIZ_PURPOSE_CERTIFICATION, 4),
        else_=4,
    )
    rows = (
        query.order_by(priority, Quiz.recommended_week.is_(None), Quiz.recommended_week, Quiz.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return ok(
        [
            {
                "id": quiz.id,
                "title": quiz.title,
                "quiz_purpose": quiz.quiz_purpose,
                "recommended_week": quiz.recommended_week,
                "week_number": quiz.week_number,
                "question_count": actual_question_count,
                "missing_explanations": missing_explanations,
                "answer_keys_validated": quiz.answer_keys_validated,
                "quality_score": quiz.quality_score,
                "source_type": quiz.source_type,
                "editorial_status": quiz.editorial_status,
                "is_active": quiz.is_active,
            }
            for quiz, actual_question_count, missing_explanations in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
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

    changes = payload.model_dump(exclude_unset=True)
    resulting_required = changes.get("is_required", quiz.is_required)
    resulting_checklist = changes.get("show_in_weekly_checklist", quiz.show_in_weekly_checklist)
    resulting_validated = changes.get("answer_keys_validated", quiz.answer_keys_validated)
    resulting_editorial_status = changes.get("editorial_status", quiz.editorial_status)
    resulting_practice_library = changes.get("show_in_practice_library", quiz.show_in_practice_library)
    if (resulting_required or resulting_checklist or resulting_practice_library) and (
        not resulting_validated or resulting_editorial_status != EDITORIAL_STATUS_VALIDATED
    ):
        raise HTTPException(
            status_code=409,
            detail="A quiz must have independently validated answer keys and editorial status 'validated' before student visibility can be enabled.",
        )
    if resulting_checklist and not resulting_required:
        raise HTTPException(status_code=409, detail="A weekly checklist quiz must also be required.")

    updated = {}
    for field, value in changes.items():
        setattr(quiz, field, value)
        updated[field] = value

    db.commit()
    return ok(
        {
            "id": quiz.id,
            "title": quiz.title,
            "week_number": quiz.week_number,
            "domain_id": quiz.domain_id,
            "status": quiz.status,
            "quiz_purpose": quiz.quiz_purpose,
            "is_required": quiz.is_required,
            "show_in_weekly_checklist": quiz.show_in_weekly_checklist,
            "show_in_practice_library": quiz.show_in_practice_library,
            "editorial_status": quiz.editorial_status,
            "recommended_week": quiz.recommended_week,
            "prerequisite_week": quiz.prerequisite_week,
            "quality_score": quiz.quality_score,
            "source_type": quiz.source_type,
            "answer_keys_validated": quiz.answer_keys_validated,
            "explanations_complete": quiz.explanations_complete,
            "is_active": quiz.is_active,
            **updated,
        }
    )


@router.post("/quiz/scrape-preview")
async def scrape_quiz_preview(payload: ScrapePreviewRequest):
    url = str(payload.url)

    try:
        result = await scrape_examcompass_quiz(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("scrape_failed url=%s", url)
        raise HTTPException(status_code=500, detail=f"Scrape failed: {exc}") from exc

    return ok(result)


@router.post("/quiz/scrape-save")
async def scrape_quiz_save(payload: QuizImportRequest, db: Session = Depends(get_db)):
    questions = payload.questions

    quiz = Quiz(
        title=payload.title,
        source_url=payload.source_url,
        week_number=payload.week_number,
        question_count=len(questions),
        lesson_id=payload.lesson_id,
        domain_id=payload.domain_id,
        quiz_purpose=QUIZ_PURPOSE_CERTIFICATION,
        is_required=False,
        show_in_weekly_checklist=False,
        show_in_practice_library=False,
        editorial_status=EDITORIAL_STATUS_UNREVIEWED,
        source_type=SOURCE_TYPE_EXAMCOMPASS if "examcompass" in str(payload.source_url or "").lower() else SOURCE_TYPE_MANUAL,
        answer_keys_validated=False,
        explanations_complete=False,
    )
    db.add(quiz)
    db.flush()

    saved_count = 0
    for question in questions:
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=question.question_text,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d,
                option_e=question.option_e or None,
                option_f=question.option_f or None,
                option_g=question.option_g or None,
                option_h=question.option_h or None,
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )
        )
        saved_count += 1

    db.commit()
    return ok({"quiz_id": quiz.id, "question_count": saved_count, "title": quiz.title})


@router.post("/quiz/bookmarklet-import")
async def bookmarklet_import(payload: QuizImportRequest, db: Session = Depends(get_db)):
    """
    Receives questions extracted by the bookmarklet running in the user's browser.
    Payload: { title, source_url, week_number, lesson_id, questions: [...] }
    """
    questions = payload.questions

    raw_title = payload.title.strip()
    title = _normalize_examcompass_title(raw_title) or raw_title or "ExamCompass Import"
    source_url = payload.source_url or ""

    quiz = Quiz(
        title=title,
        source_url=source_url,
        source_urls=[source_url] if source_url else [],
        week_number=payload.week_number,
        question_count=len(questions),
        lesson_id=payload.lesson_id,
        domain_id=payload.domain_id,
        quiz_purpose=QUIZ_PURPOSE_CERTIFICATION,
        is_required=False,
        show_in_weekly_checklist=False,
        show_in_practice_library=False,
        editorial_status=EDITORIAL_STATUS_UNREVIEWED,
        source_type=SOURCE_TYPE_EXAMCOMPASS,
        answer_keys_validated=False,
        explanations_complete=False,
    )
    db.add(quiz)
    db.flush()

    saved = 0
    for question in questions:
        all_correct = question.all_correct_answers

        primary_correct = all_correct[0] if all_correct else question.correct_answer
        allowed_answers = ["A", "B", "C", "D", "E", "F", "G", "H"]
        if primary_correct not in allowed_answers:
            primary_correct = "A"
        if primary_correct != "A" and not getattr(question, f"option_{primary_correct.lower()}"):
            primary_correct = "A"

        correct_answers_str = ",".join(all_correct) if len(all_correct) > 1 else None
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=question.question_text,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d,
                option_e=question.option_e or None,
                option_f=question.option_f or None,
                option_g=question.option_g or None,
                option_h=question.option_h or None,
                correct_answer=primary_correct,
                correct_answers=correct_answers_str,
                explanation=question.explanation,
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
            "week_number": quiz.week_number,
            "quiz_purpose": quiz.quiz_purpose,
            "is_required": quiz.is_required,
            "show_in_weekly_checklist": quiz.show_in_weekly_checklist,
            "show_in_practice_library": quiz.show_in_practice_library,
            "editorial_status": quiz.editorial_status,
            "recommended_week": quiz.recommended_week,
            "prerequisite_week": quiz.prerequisite_week,
            "quality_score": quiz.quality_score,
            "source_type": quiz.source_type,
            "answer_keys_validated": quiz.answer_keys_validated,
            "explanations_complete": quiz.explanations_complete,
            "is_active": quiz.is_active,
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
def update_question(question_id: int, payload: QuestionUpdate, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    db.commit()
    return ok({"updated": True})
