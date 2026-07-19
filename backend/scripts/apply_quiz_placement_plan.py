#!/usr/bin/env python3
"""Apply the approved quiz placement plan. Dry-run unless --confirm is supplied."""

import argparse
import csv
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.config import load_env  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.quiz import Quiz  # noqa: E402


REQUIRED_BY_WEEK = {
    0: 42, 1: 1, 2: 78, 3: 2, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9,
    9: 10, 10: 12, 11: 13, 12: 14, 13: 15, 14: 16, 15: 17,
    16: 18, 17: 19, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24,
    23: 48, 24: 25,
}
REQUIRED_WEEK_BY_ID = {quiz_id: week for week, quiz_id in REQUIRED_BY_WEEK.items()}
GATE_IDS = {5, 9, 14, 19, 25}
CUMULATIVE_IDS = {18, 22}
ARCHIVED_MERGE_IDS = {45, 55, 61, 67, 95}


def _purpose(row: dict, quiz_id: int) -> str:
    if quiz_id in GATE_IDS:
        return "gate"
    if quiz_id in CUMULATIVE_IDS:
        return "cumulative"
    if quiz_id in REQUIRED_WEEK_BY_ID:
        return "required"
    if row["recommended_week"].strip().upper() == "LIB":
        return "certification"
    if row["classification"] == "REMEDIATION":
        return "remediation"
    return "practice"


def _week(row: dict, quiz: Quiz) -> int:
    if quiz.id in REQUIRED_WEEK_BY_ID:
        return REQUIRED_WEEK_BY_ID[quiz.id]
    value = row["recommended_week"].strip()
    return int(value) if value.isdigit() else quiz.week_number


def _prerequisite(value: str) -> int | None:
    numbers = [int(part) for part in value.replace("-", " ").split() if part.isdigit()]
    return max(numbers) if numbers else None


def build_changes(quiz: Quiz, row: dict) -> dict:
    required = quiz.id in REQUIRED_WEEK_BY_ID
    purpose = _purpose(row, quiz.id)
    is_archived = quiz.id in ARCHIVED_MERGE_IDS
    imported = row["appears_examcompass_import"] == "Yes"
    if required and imported and not quiz.answer_keys_validated:
        raise RuntimeError(
            f"Quiz #{quiz.id} is an imported required assessment but its answer keys are not validated. "
            "Run apply_quiz_answer_corrections.py first."
        )
    editorial_status = "archived" if is_archived else (
        "validated" if not imported or (required and quiz.answer_keys_validated) else
        ("needs_edit" if row["classification"] in {"KEEP_WITH_EDITS", "MERGE"} else "unreviewed")
    )
    return {
        "week_number": _week(row, quiz),
        "recommended_week": None if row["recommended_week"].strip().upper() == "LIB" else _week(row, quiz),
        "prerequisite_week": _prerequisite(row["prerequisite_weeks"]),
        "quiz_purpose": purpose,
        "is_required": required,
        "show_in_weekly_checklist": required,
        "show_in_practice_library": not required and not is_archived,
        "editorial_status": editorial_status,
        "quality_score": int(row["quality_score"]),
        "source_type": "seed" if row["exists_in_current_seed_files"] == "Yes" else "examcompass",
        "is_active": not is_archived,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Commit changes; otherwise roll back after printing")
    args = parser.parse_args()
    load_env()
    inventory = ROOT / "docs" / "QUIZ_COMPLETE_INVENTORY.csv"
    with inventory.open(newline="", encoding="utf-8") as handle:
        rows = {int(row["quiz_id"]): row for row in csv.DictReader(handle)}
    if len(rows) != 104:
        raise RuntimeError(f"Expected 104 inventory rows, found {len(rows)}")

    db = SessionLocal()
    changed = 0
    try:
        quizzes = db.query(Quiz).order_by(Quiz.id).all()
        if len(quizzes) != 104:
            raise RuntimeError(f"Expected 104 live quizzes, found {len(quizzes)}")
        for quiz in quizzes:
            desired = build_changes(quiz, rows[quiz.id])
            differences = {field: (getattr(quiz, field), value) for field, value in desired.items() if getattr(quiz, field) != value}
            if not differences:
                continue
            changed += 1
            print(f"Quiz #{quiz.id} {quiz.title}")
            for field, (old, new) in differences.items():
                print(f"  {field}: {old!r} -> {new!r}")
                setattr(quiz, field, new)

        db.flush()
        required_rows = db.query(Quiz).filter(Quiz.is_required.is_(True), Quiz.show_in_weekly_checklist.is_(True)).all()
        coverage = {week: [] for week in range(25)}
        for quiz in required_rows:
            coverage.setdefault(quiz.week_number, []).append(quiz.id)
        bad = {week: ids for week, ids in coverage.items() if len(ids) != 1}
        if bad:
            raise RuntimeError(f"Required coverage must be exactly one quiz per Week 0-24: {bad}")
        question_count = sum(len(quiz.questions) for quiz in quizzes)
        if question_count != 967:
            raise RuntimeError(f"Question count changed unexpectedly: {question_count}")

        if args.confirm:
            db.commit()
            print(f"COMMITTED: {changed} quizzes changed; counts verified at 104 quizzes / 967 questions")
        else:
            db.rollback()
            print(f"DRY RUN: {changed} quizzes would change; transaction rolled back (use --confirm to apply)")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
