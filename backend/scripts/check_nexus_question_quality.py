"""Fail data-integrity defects and report editorial-risk signals for authored quizzes.

This intentionally queries only ``Quiz.source_type == 'seed'``.  It is safe to
run in CI after seeding a disposable database; imported ExamCompass content is
outside this quality gate's editorial scope.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.quiz import Question, Quiz, SOURCE_TYPE_SEED  # noqa: E402
from app.services.question_validation import validate_question  # noqa: E402
from scripts.audit_nexus_question_quality import _correct_is_uniquely_longest  # noqa: E402


def check(db) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    rows = (
        db.query(Question, Quiz)
        .join(Quiz, Quiz.id == Question.quiz_id)
        .filter(Quiz.source_type == SOURCE_TYPE_SEED)
        .order_by(Question.id)
        .all()
    )
    positions = {letter: 0 for letter in "ABCD"}
    single_count = 0
    longest = 0
    for question, quiz in rows:
        result = validate_question(
            {
                "question_text": question.question_text,
                **{f"option_{letter.lower()}": getattr(question, f"option_{letter.lower()}") for letter in "ABCDEFGH"},
                "correct_answer": question.correct_answer,
                "correct_answers": question.correct_answers,
                "explanation": question.explanation,
            },
            require_explanation=quiz.is_required,
        )
        for issue in result.errors:
            failures.append(f"{question.seed_key or question.id}: {issue.message}")
        if not question.is_multi_select:
            single_count += 1
            if question.correct_answer in positions:
                positions[question.correct_answer] += 1
            if _correct_is_uniquely_longest(question):
                longest += 1

    if single_count:
        top_letter, top_count = max(positions.items(), key=lambda item: item[1])
        if top_count / single_count >= 0.55:
            warnings.append(
                f"correct-answer concentration: {top_letter} is {top_count}/{single_count} "
                f"({top_count / single_count:.0%}); review editorial ordering"
            )
        if longest / single_count >= 0.25:
            warnings.append(
                f"uniquely-longest correct answers: {longest}/{single_count} "
                f"({longest / single_count:.0%}); review distractor comparability"
            )
    return failures, warnings


def main() -> None:
    db = SessionLocal()
    try:
        failures, warnings = check(db)
    finally:
        db.close()
    for warning in warnings:
        print(f"WARN: {warning}")
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        raise SystemExit(1)
    print("PASS: Nexus-authored question integrity checks passed")


if __name__ == "__main__":
    main()
