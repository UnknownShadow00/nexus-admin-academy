#!/usr/bin/env python3
"""Place unvalidated quizzes in the admin-only editorial-review state.

Dry-run by default.  The script intentionally changes no quiz/question IDs,
status, placement, or student records.
"""

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import load_env  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.quiz import (  # noqa: E402
    EDITORIAL_STATUS_ARCHIVED,
    EDITORIAL_STATUS_NEEDS_EDIT,
    EDITORIAL_STATUS_VALIDATED,
    Question,
    Quiz,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Commit changes; default is dry-run")
    args = parser.parse_args()
    load_env()
    db = SessionLocal()
    try:
        quiz_total = db.query(Quiz).count()
        question_total = db.query(Question).count()
        if (quiz_total, question_total) != (104, 967):
            raise RuntimeError(
                f"Refusing to run against unexpected content counts: {quiz_total} quizzes / {question_total} questions"
            )

        targets = (
            db.query(Quiz)
            .filter(
                Quiz.is_active.is_(True),
                Quiz.editorial_status != EDITORIAL_STATUS_ARCHIVED,
                (Quiz.answer_keys_validated.is_(False) | (Quiz.editorial_status != EDITORIAL_STATUS_VALIDATED)),
            )
            .order_by(Quiz.id)
            .all()
        )
        changes = 0
        for quiz in targets:
            desired = {
                "show_in_practice_library": False,
                "editorial_status": EDITORIAL_STATUS_NEEDS_EDIT,
            }
            differences = {
                field: (getattr(quiz, field), value)
                for field, value in desired.items()
                if getattr(quiz, field) != value
            }
            if not differences:
                continue
            changes += 1
            print(f"Quiz #{quiz.id}: {quiz.title}")
            for field, (old, new) in differences.items():
                print(f"  {field}: {old!r} -> {new!r}")
                setattr(quiz, field, new)

        db.flush()
        if db.query(Quiz).count() != quiz_total or db.query(Question).count() != question_total:
            raise RuntimeError("Content count changed unexpectedly")
        remaining_visible = (
            db.query(Quiz)
            .filter(
                Quiz.is_active.is_(True),
                Quiz.show_in_practice_library.is_(True),
                (Quiz.answer_keys_validated.is_(False) | (Quiz.editorial_status != EDITORIAL_STATUS_VALIDATED)),
            )
            .count()
        )
        if remaining_visible:
            raise RuntimeError(f"{remaining_visible} unvalidated quizzes would still be marked visible")

        if args.confirm:
            db.commit()
            print(f"COMMITTED: {changes} quizzes moved to admin-only editorial review; counts unchanged")
        else:
            db.rollback()
            print(f"DRY RUN: {changes} quizzes would move to admin-only editorial review; transaction rolled back")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
