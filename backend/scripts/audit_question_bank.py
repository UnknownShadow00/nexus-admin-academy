"""Read-only audit of the question bank, run through the shared question
validation service. Writes a machine-readable JSON file and a human-readable
Markdown summary. Never writes to the database.

Usage:
    ./.venv/bin/python scripts/audit_question_bank.py \
        --json ../docs/question_bank_audit.json \
        --markdown ../docs/QUESTION_BANK_AUDIT.md
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.flashcard import FlashcardReview  # noqa: E402
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz  # noqa: E402
from app.services.question_validation import validate_question_row  # noqa: E402

CLASS_SAFE_AUTO = "safe_automatic_cleanup"
CLASS_HUMAN_REVIEW = "requires_human_answer_key_review"
CLASS_ALREADY_VALID = "already_valid"
CLASS_UNPUBLISH = "should_be_unpublished_temporarily"

# Error message substrings that mean the answer key itself is in question
# (as opposed to a purely cosmetic option-list problem).
_ANSWER_KEY_ERROR_MARKERS = (
    "correct answer",
    "Select ",
    "single-choice",
    "multi-select",
)


def _classify(question: Question, quiz: Quiz, result) -> str:
    if result.valid and not result.warnings and not result.info:
        return CLASS_ALREADY_VALID

    touches_answer_key = any(
        any(marker in issue.message for marker in _ANSWER_KEY_ERROR_MARKERS) for issue in result.errors
    )

    if not result.valid:
        if touches_answer_key:
            return CLASS_HUMAN_REVIEW
        if quiz.status == QUIZ_STATUS_PUBLISHED:
            return CLASS_UNPUBLISH
        return CLASS_HUMAN_REVIEW

    # Valid, but has warnings/info (blank options to drop, duplicate option text).
    if result.warnings:
        return CLASS_HUMAN_REVIEW  # duplicate option text needs a human call
    return CLASS_SAFE_AUTO  # only blank-option info notes — safe to trim


def run_audit(db) -> dict:
    quizzes = {q.id: q for q in db.query(Quiz).all()}
    questions = db.query(Question).order_by(Question.id.asc()).all()

    totals = Counter()
    by_classification = Counter()
    by_source_type = Counter()
    required_vs_optional = Counter()
    select_n_mismatches = []
    blank_option_questions = []
    duplicate_option_questions = []
    invalid_reference_questions = []
    missing_explanation_questions = []
    findings = []

    for question in questions:
        quiz = quizzes.get(question.quiz_id)
        if quiz is None:
            continue  # orphaned row; shouldn't happen with FK cascade, skip defensively
        result = validate_question_row(question)
        classification = _classify(question, quiz, result)

        totals["total_questions"] += 1
        totals["multi_select" if question.is_multi_select else "single_choice"] += 1
        by_classification[classification] += 1
        by_source_type[quiz.source_type] += 1
        required_vs_optional["required" if quiz.is_required else "optional"] += 1

        if not question.explanation or not question.explanation.strip():
            missing_explanation_questions.append(question.id)

        for issue in result.errors:
            if "Select " in issue.message:
                select_n_mismatches.append(question.id)
            if "does not match a valid option" in issue.message:
                invalid_reference_questions.append(question.id)
        if result.info:
            blank_option_questions.append(question.id)
        if result.warnings:
            duplicate_option_questions.append(question.id)

        if classification != CLASS_ALREADY_VALID:
            findings.append(
                {
                    "question_id": question.id,
                    "quiz_id": quiz.id,
                    "quiz_title": quiz.title,
                    "quiz_status": quiz.status,
                    "quiz_source_type": quiz.source_type,
                    "quiz_is_required": quiz.is_required,
                    "classification": classification,
                    "question_type": result.question_type,
                    "errors": [i.message for i in result.errors],
                    "warnings": [i.message for i in result.warnings],
                    "info": [i.message for i in result.info],
                }
            )

    # Flashcards that reference multi-select questions — these were affected by
    # the pre-fix serialization bug (rendering, not storage; underlying answer
    # data was never corrupted, but worth surfacing so admins know which
    # students should be spot-checked / told to re-review).
    multi_select_question_ids = {q.id for q in questions if q.is_multi_select}
    affected_flashcards = (
        db.query(FlashcardReview)
        .filter(FlashcardReview.question_id.in_(multi_select_question_ids))
        .count()
        if multi_select_question_ids
        else 0
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": dict(totals),
        "by_classification": dict(by_classification),
        "by_source_type": dict(by_source_type),
        "by_required_vs_optional": dict(required_vs_optional),
        "select_n_mismatch_question_ids": select_n_mismatches,
        "blank_option_question_ids": blank_option_questions,
        "duplicate_option_question_ids": duplicate_option_questions,
        "invalid_answer_reference_question_ids": invalid_reference_questions,
        "missing_explanation_question_ids": missing_explanation_questions,
        "multi_select_flashcards_affected_by_prior_render_bug": affected_flashcards,
        "findings": findings,
    }


def _markdown_report(report: dict) -> str:
    t = report["totals"]
    lines = [
        "# Question Bank Audit",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "Read-only audit run through the shared question validation service "
        "(`backend/app/services/question_validation.py`). No question data was "
        "modified. No student names, attempts, or other private data are included.",
        "",
        "## Totals",
        "",
        f"- Total questions: {t.get('total_questions', 0)}",
        f"- Single-choice: {t.get('single_choice', 0)}",
        f"- Multi-select: {t.get('multi_select', 0)}",
        "",
        "## Classification",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    labels = {
        CLASS_ALREADY_VALID: "Already valid",
        CLASS_SAFE_AUTO: "Safe automatic cleanup",
        CLASS_HUMAN_REVIEW: "Requires human answer-key review",
        CLASS_UNPUBLISH: "Should be unpublished temporarily",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {report['by_classification'].get(key, 0)} |")

    lines += [
        "",
        "## By source type",
        "",
        "| Source | Count |",
        "|---|---:|",
    ]
    for source, count in sorted(report["by_source_type"].items()):
        lines.append(f"| {source} | {count} |")

    lines += [
        "",
        "## Required vs optional content",
        "",
        f"- Required quizzes: {report['by_required_vs_optional'].get('required', 0)} questions",
        f"- Optional/practice quizzes: {report['by_required_vs_optional'].get('optional', 0)} questions",
        "",
        "## Specific issue counts",
        "",
        f"- Select-N text/answer-count mismatches: {len(report['select_n_mismatch_question_ids'])}",
        f"- Questions with blank options: {len(report['blank_option_question_ids'])}",
        f"- Questions with duplicate option text: {len(report['duplicate_option_question_ids'])}",
        f"- Questions with invalid answer references: {len(report['invalid_answer_reference_question_ids'])}",
        f"- Questions missing an explanation: {len(report['missing_explanation_question_ids'])}",
        f"- Flashcards pointing at multi-select questions (pre-fix render bug exposure): "
        f"{report['multi_select_flashcards_affected_by_prior_render_bug']}",
        "",
        "## Findings requiring attention",
        "",
        "| Question ID | Quiz | Status | Source | Classification | Issues |",
        "|---:|---|---|---|---|---|",
    ]
    for f in report["findings"]:
        issues = "; ".join([*f["errors"], *f["warnings"]]) or "; ".join(f["info"])
        issues = issues.replace("|", "\\|")
        quiz_title = f["quiz_title"].replace("|", "\\|")
        lines.append(
            f"| {f['question_id']} | {quiz_title} (#{f['quiz_id']}) | {f['quiz_status']} | "
            f"{f['quiz_source_type']} | {labels.get(f['classification'], f['classification'])} | {issues} |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="Path to write the JSON audit report")
    parser.add_argument("--markdown", default=None, help="Path to write the Markdown audit summary")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = run_audit(db)
    finally:
        db.close()  # read-only session; nothing was ever added/committed

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"Wrote {args.json}")
    if args.markdown:
        Path(args.markdown).write_text(_markdown_report(report))
        print(f"Wrote {args.markdown}")
    if not args.json and not args.markdown:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
