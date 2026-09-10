from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.flashcard import FlashcardReview
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import Question, QuizAttempt
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.services.fsrs_service import schedule_next
from app.services.quiz_scores import supports_attempt_state
from app.services.review_service import (
    learner_concept_name,
    lesson_review,
    related_practice,
)
from app.utils.responses import ok

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


class FlashcardRatingRequest(BaseModel):
    rating: int = Field(ge=1, le=4)


def _non_blank_options(question: Question) -> dict:
    letters = "ABCDEFGH"
    raw = [
        question.option_a,
        question.option_b,
        question.option_c,
        question.option_d,
        question.option_e,
        question.option_f,
        question.option_g,
        question.option_h,
    ]
    return {
        letter: text.strip()
        for letter, text in zip(letters, raw)
        if text and text.strip()
    }


def _serialize_card(card: FlashcardReview, question: Question | None = None) -> dict:
    question = question or card.question
    quiz = question.quiz if question else None
    return {
        "id": card.id,
        "student_id": card.student_id,
        "question_id": card.question_id,
        "due_date": card.due_date.isoformat() if card.due_date else None,
        "interval_days": card.interval_days,
        "ease_factor": card.ease_factor,
        "review_count": card.review_count,
        "last_rating": card.last_rating,
        "last_wrong_answer": card.last_wrong_answer,
        "question_text": question.question_text if question else None,
        "is_multi_select": question.is_multi_select if question else False,
        "options": _non_blank_options(question) if question else {},
        "correct_answer": question.correct_answer if question else None,
        "correct_answers": question.all_correct_answers if question else [],
        "explanation": (question.explanation or "") if question else "",
        "quiz_id": question.quiz_id if question else None,
        "quiz_title": quiz.title if quiz else None,
    }


@router.get("/due")
def get_due_flashcards(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    rows = (
        db.query(FlashcardReview, Question)
        .join(Question, Question.id == FlashcardReview.question_id)
        .filter(
            FlashcardReview.student_id == current_student.id,
            FlashcardReview.due_date <= date.today(),
        )
        .order_by(FlashcardReview.due_date.asc(), FlashcardReview.id.asc())
        .limit(20)
        .all()
    )
    cards = [_serialize_card(card, question) for card, question in rows]
    prioritized = sorted(
        rows,
        key=lambda pair: (
            0
            if pair[0].review_count == 0
            else 1
            if pair[0].last_rating in {1, 2}
            else 2,
            pair[0].due_date,
            pair[0].id,
        ),
    )
    priorities = []
    included_concepts = set()
    for card, question in prioritized:
        quiz = question.quiz
        concept_name = learner_concept_name(question.question_text, quiz.title)
        if concept_name in included_concepts:
            continue
        review = lesson_review(db, quiz)
        practice = related_practice(db, quiz)
        priorities.append(
            {
                "question_id": question.id,
                "concept_name": concept_name,
                "reason": f"You missed a question about {concept_name}.",
                "review_url": review["url"] if review else f"/quizzes/{quiz.id}/review",
                "review_label": review["label"]
                if review
                else "Review your saved attempt",
                "practice_url": practice["url"] if practice else None,
                "practice_label": practice["label"] if practice else None,
            }
        )
        included_concepts.add(concept_name)
        if len(priorities) == 3:
            break
    lesson_history = (
        db.query(StudentLessonProgress.id)
        .filter(
            StudentLessonProgress.student_id == current_student.id,
            StudentLessonProgress.completed_at.isnot(None),
        )
        .first()
        is not None
    )
    attempt_query = db.query(QuizAttempt.id).filter(
        QuizAttempt.student_id == current_student.id
    )
    if supports_attempt_state(db):
        attempt_query = attempt_query.filter(
            QuizAttempt.status.in_(("submitted", "practice_complete"))
        )
    has_history = bool(rows or lesson_history or attempt_query.first())
    review_state = "due" if rows else "clear" if has_history else "fresh"
    return {
        **ok(cards, total=len(rows), page=1, per_page=20),
        "review_state": review_state,
        "due_count": len(rows),
        "priority_count": len(priorities),
        "priorities": priorities,
    }


@router.post("/{card_id}/rate")
def rate_flashcard(
    card_id: int,
    payload: FlashcardRatingRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    card = (
        db.query(FlashcardReview)
        .filter(
            FlashcardReview.id == card_id,
            FlashcardReview.student_id == current_student.id,
        )
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    interval_days, ease_factor = schedule_next(
        card.interval_days, card.ease_factor, payload.rating
    )
    card.interval_days = interval_days
    card.ease_factor = ease_factor
    card.review_count += 1
    card.last_rating = payload.rating
    card.due_date = date.today() + timedelta(days=interval_days)

    db.commit()
    db.refresh(card)
    return ok(_serialize_card(card))
