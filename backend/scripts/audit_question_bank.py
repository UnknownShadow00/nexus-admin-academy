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
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.flashcard import FlashcardReview  # noqa: E402
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz  # noqa: E402
from app.models.training import TrainingWeekActivity  # noqa: E402
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
    malformed_entity_questions = []
    imported_number_prefix_questions = []
    normalized_text_groups = defaultdict(list)
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
        normalized_text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", question.question_text.casefold())).strip()
        if normalized_text:
            normalized_text_groups[normalized_text].append({"question_id": question.id, "quiz_id": quiz.id})
        if re.search(r"&(?:amp|lt|gt|quot|apos|#\d+);", question.question_text, re.IGNORECASE):
            malformed_entity_questions.append(question.id)
        if re.match(r"^\s*(?:question|q)\s*\d+\s*[:.)-]", question.question_text, re.IGNORECASE):
            imported_number_prefix_questions.append(question.id)

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
    duplicate_groups = [group for group in normalized_text_groups.values() if len(group) > 1]
    within_quiz_duplicate_groups = [
        group for group in duplicate_groups if len({entry["quiz_id"] for entry in group}) < len(group)
    ]
    quiz_question_counts = dict(
        db.query(Question.quiz_id, func.count(Question.id)).group_by(Question.quiz_id).all()
    )
    zero_question_quiz_ids = [quiz.id for quiz in quizzes.values() if quiz_question_counts.get(quiz.id, 0) == 0]
    referenced_quiz_ids = set()
    for activity in db.query(TrainingWeekActivity).all():
        if activity.activity_type == "quiz" and str(activity.content_ref).isdigit():
            referenced_quiz_ids.add(int(activity.content_ref))
        mapped_quiz_id = (activity.metadata_json or {}).get("quiz_id")
        if str(mapped_quiz_id or "").isdigit():
            referenced_quiz_ids.add(int(mapped_quiz_id))
    disconnected_quiz_ids = [
        quiz.id for quiz in quizzes.values()
        if quiz.is_active and quiz.id not in referenced_quiz_ids
        and not quiz.show_in_practice_library and not quiz.lesson_id and not quiz.assignments
    ]

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
        "duplicate_question_groups": duplicate_groups,
        "within_quiz_duplicate_question_groups": within_quiz_duplicate_groups,
        "malformed_entity_question_ids": malformed_entity_questions,
        "imported_number_prefix_question_ids": imported_number_prefix_questions,
        "zero_question_quiz_ids": zero_question_quiz_ids,
        "disconnected_quiz_ids": disconnected_quiz_ids,
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
        f"- Exact normalized duplicate question groups: {len(report['duplicate_question_groups'])}",
        f"- Duplicate groups within the same quiz: {len(report['within_quiz_duplicate_question_groups'])}",
        f"- Questions with malformed HTML entities: {len(report['malformed_entity_question_ids'])}",
        f"- Questions with imported numbering prefixes: {len(report['imported_number_prefix_question_ids'])}",
        f"- Quizzes with zero questions: {len(report['zero_question_quiz_ids'])}",
        f"- Active quizzes disconnected from curriculum/practice/assignments: {len(report['disconnected_quiz_ids'])}",
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
