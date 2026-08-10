"""Identity-preserving synchronization for Nexus-authored seed questions.

Seed content is curriculum content, not disposable fixture data.  A question's
``seed_key`` is stable across reseeds, so correcting wording or option order
updates the existing row instead of invalidating question IDs referenced by
attempts and review history.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.quiz import Question, Quiz


OPTION_FIELDS = tuple(f"option_{letter}" for letter in "abcdefgh")
QUESTION_FIELDS = (
    "question_text",
    *OPTION_FIELDS,
    "correct_answer",
    "correct_answers",
    "explanation",
)


def seed_key_for(quiz_title: str, ordinal: int) -> str:
    """Return the source-stable identity for a Nexus-authored question."""
    slug = re.sub(r"[^a-z0-9]+", "-", quiz_title.casefold()).strip("-")
    return f"nexus-authored:{slug}:{ordinal:02d}"


def sync_seed_questions(db: Session, quiz: Quiz, specs: Iterable[dict]) -> int:
    """Apply authored question specs without deleting historical question rows.

    Existing seed keys are updated in place.  The phase seeders currently keep
    their question count stable; encountering an obsolete key is intentionally
    a hard error rather than silently deleting a row that may be referenced by
    a prior QuizAttempt.
    """
    specs = list(specs)
    existing = {
        question.seed_key: question
        for question in db.query(Question).filter(Question.quiz_id == quiz.id).all()
        if question.seed_key
    }
    expected_keys = {seed_key_for(quiz.title, ordinal) for ordinal in range(1, len(specs) + 1)}
    obsolete = set(existing) - expected_keys
    if obsolete:
        raise RuntimeError(
            f"Refusing to remove historical authored questions from {quiz.title}: "
            f"{', '.join(sorted(obsolete))}"
        )

    for ordinal, spec in enumerate(specs, start=1):
        key = seed_key_for(quiz.title, ordinal)
        question = existing.get(key)
        if question is None:
            question = Question(quiz_id=quiz.id, seed_key=key)
            db.add(question)
        for field in QUESTION_FIELDS:
            setattr(question, field, spec.get(field))
    db.flush()
    return len(specs)
