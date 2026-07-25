from datetime import date

from sqlalchemy.orm import Session

from app.models.flashcard import FlashcardReview


def schedule_next(interval_days: int, ease_factor: float, rating: int) -> tuple[int, float]:
    if rating == 1:
        return 1, max(1.3, ease_factor - 0.2)
    if rating == 2:
        return max(1, int(interval_days * 1.2)), max(1.3, ease_factor - 0.15)
    if rating == 3:
        return max(1, int(interval_days * ease_factor)), ease_factor
    if rating == 4:
        return max(1, int(interval_days * ease_factor * 1.3)), min(4.0, ease_factor + 0.15)
    raise ValueError("Rating must be between 1 and 4")


def create_cards_for_wrong_answers(db: Session, student_id: int, wrong_answers: dict[int, str | None]) -> None:
    today = date.today()
    for question_id in sorted(wrong_answers):
        student_answer = wrong_answers[question_id]
        card = (
            db.query(FlashcardReview)
            .filter(FlashcardReview.student_id == student_id, FlashcardReview.question_id == question_id)
            .first()
        )
        if card is None:
            db.add(
                FlashcardReview(
                    student_id=student_id,
                    question_id=question_id,
                    due_date=today,
                    last_wrong_answer=student_answer,
                )
            )
        else:
            card.due_date = today
            card.last_wrong_answer = student_answer
