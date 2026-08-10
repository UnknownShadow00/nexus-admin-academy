"""Audit imported ExamCompass questions and all quiz connections without writes.

The authoritative authorship boundary is ``Quiz.source_type == 'examcompass'``.
Question-level ``source`` text is provenance metadata only and must not be used
to mix imported and Nexus-authored populations.
"""

from __future__ import annotations

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
from app.models.quiz import (  # noqa: E402
    EDITORIAL_STATUS_ARCHIVED,
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_PURPOSE_CUMULATIVE,
    QUIZ_PURPOSE_REMEDIATION,
    SOURCE_TYPE_EXAMCOMPASS,
    Question,
    Quiz,
)
from app.models.training import TrainingWeekActivity  # noqa: E402
from app.services.question_validation import validate_question_row  # noqa: E402
from app.services.quiz_visibility import student_visible_quiz_filters  # noqa: E402

LETTERS = "ABCDEFGH"


def _options(question: Question) -> dict[str, str]:
    return {
        letter: (getattr(question, f"option_{letter.lower()}") or "").strip()
        for letter in LETTERS
        if (getattr(question, f"option_{letter.lower()}") or "").strip()
    }


def _is_uniquely_longest(question: Question) -> bool:
    if question.is_multi_select:
        return False
    options = _options(question)
    correct = options.get(question.correct_answer)
    return bool(correct) and all(len(correct) > len(value) for key, value in options.items() if key != question.correct_answer)


def _usage_by_quiz(db) -> dict[int, set[str]]:
    usage: dict[int, set[str]] = defaultdict(set)
    for activity in db.query(TrainingWeekActivity).all():
        quiz_id = None
        if activity.activity_type == "quiz" and str(activity.content_ref).isdigit():
            quiz_id = int(activity.content_ref)
        metadata_id = (activity.metadata_json or {}).get("quiz_id")
        if quiz_id is None and str(metadata_id or "").isdigit():
            quiz_id = int(metadata_id)
        if quiz_id is not None:
            usage[quiz_id].add("required weekly curriculum" if activity.is_required else "optional weekly curriculum")
    for quiz in db.query(Quiz).all():
        if quiz.lesson_id:
            usage[quiz.id].add("lesson connection")
        if quiz.assignments:
            usage[quiz.id].add("admin assignment")
        if quiz.show_in_practice_library:
            usage[quiz.id].add("practice library")
        if quiz.quiz_purpose == QUIZ_PURPOSE_REMEDIATION:
            usage[quiz.id].add("remediation")
        if quiz.quiz_purpose == QUIZ_PURPOSE_CUMULATIVE:
            usage[quiz.id].add("cumulative review")
    return usage


def _quiz_classification(quiz: Quiz, usage: set[str], visible: bool) -> tuple[str, str]:
    if not quiz.is_active or quiz.editorial_status == EDITORIAL_STATUS_ARCHIVED:
        return "HIDE / ARCHIVE", "Retain IDs and history; do not surface to students."
    if "required weekly curriculum" in usage:
        return "KEEP REQUIRED", "Required curriculum connection is explicit."
    if quiz.quiz_purpose == QUIZ_PURPOSE_REMEDIATION:
        return "REMEDIATION", "Only present after an assignment or failed required quiz triggers it."
    if quiz.quiz_purpose == QUIZ_PURPOSE_CUMULATIVE:
        return "CUMULATIVE REVIEW", "Purpose is explicit; keep outside the ordinary weekly checklist."
    if visible and "practice library" in usage:
        return "KEEP OPTIONAL", "Validated optional practice is student-visible."
    if quiz.is_active and quiz.editorial_status != EDITORIAL_STATUS_VALIDATED:
        return "HIDE / ARCHIVE", "Unreviewed imported content is blocked by the visibility gate and should not remain active."
    return "KEEP OPTIONAL", "Legitimate non-required connection is documented."


def _subset_stats(questions: list[Question]) -> dict:
    positions = Counter()
    single = multi = explanations = longest = 0
    for question in questions:
        multi += int(question.is_multi_select)
        single += int(not question.is_multi_select)
        explanations += int(bool((question.explanation or "").strip()))
        if not question.is_multi_select:
            positions[question.correct_answer] += 1
            longest += int(_is_uniquely_longest(question))
    return {
        "questions": len(questions),
        "single_answer": single,
        "multi_select": multi,
        "explanations": explanations,
        "missing_explanations": len(questions) - explanations,
        "explanation_percent": round(100 * explanations / len(questions), 1) if questions else 100.0,
        "correct_position_distribution": {letter: positions.get(letter, 0) for letter in "ABCD"},
        "uniquely_longest_correct": longest,
        "uniquely_longest_correct_percent": round(100 * longest / single, 1) if single else 0.0,
    }


def run_audit(db) -> dict:
    quizzes = db.query(Quiz).order_by(Quiz.id).all()
    imported_quizzes = [quiz for quiz in quizzes if quiz.source_type == SOURCE_TYPE_EXAMCOMPASS]
    usage = _usage_by_quiz(db)
    visible_ids = {
        quiz_id for (quiz_id,) in db.query(Quiz.id).filter(*student_visible_quiz_filters()).all()
    }
    questions_by_quiz = {
        quiz_id: rows
        for quiz_id, rows in (
            (quiz.id, sorted(quiz.questions, key=lambda question: question.id)) for quiz in quizzes
        )
    }
    imported_questions = [question for quiz in imported_quizzes for question in questions_by_quiz[quiz.id]]
    required_ids = {
        quiz.id for quiz in imported_quizzes if "required weekly curriculum" in usage.get(quiz.id, set())
    }
    optional_visible_ids = {
        quiz.id for quiz in imported_quizzes if quiz.id in visible_ids and quiz.id not in required_ids
    }
    required_questions = [question for quiz in imported_quizzes if quiz.id in required_ids for question in questions_by_quiz[quiz.id]]
    optional_visible_questions = [question for quiz in imported_quizzes if quiz.id in optional_visible_ids for question in questions_by_quiz[quiz.id]]
    archive_questions = [
        question for quiz in imported_quizzes
        if quiz.id not in required_ids and quiz.id not in optional_visible_ids
        for question in questions_by_quiz[quiz.id]
    ]

    integrity = []
    text_groups: dict[str, list[int]] = defaultdict(list)
    fingerprints: dict[str, list[int]] = defaultdict(list)
    for question in imported_questions:
        result = validate_question_row(question)
        if not result.valid or result.warnings:
            integrity.append({
                "question_id": question.id,
                "quiz_id": question.quiz_id,
                "errors": [issue.message for issue in result.errors],
                "warnings": [issue.message for issue in result.warnings],
            })
        normalized = re.sub(r"\W+", " ", question.question_text.casefold()).strip()
        if normalized:
            text_groups[normalized].append(question.id)
        if question.fingerprint:
            fingerprints[question.fingerprint].append(question.id)

    strict_disconnected = [
        quiz.id for quiz in imported_quizzes
        if quiz.is_active and not usage.get(quiz.id) and not quiz.show_in_practice_library
    ]
    quiz_records = []
    classifications = Counter()
    for quiz in quizzes:
        visible = quiz.id in visible_ids
        classification, action = _quiz_classification(quiz, usage.get(quiz.id, set()), visible)
        classifications[classification] += 1
        quiz_records.append({
            "id": quiz.id,
            "title": quiz.title,
            "source": quiz.source_type,
            "question_count": len(questions_by_quiz[quiz.id]),
            "usage": sorted(usage.get(quiz.id, set())) or ["none"],
            "student_visible": visible,
            "classification": classification,
            "action": action,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authorship_rule": "Imported ExamCompass questions are those whose parent Quiz.source_type == 'examcompass'.",
        "imported": {
            "all": _subset_stats(imported_questions),
            "required_curriculum": _subset_stats(required_questions),
            "optional_visible": _subset_stats(optional_visible_questions),
            "unused_or_archive": _subset_stats(archive_questions),
            "active_quizzes": sum(quiz.is_active for quiz in imported_quizzes),
            "hidden_or_archived_quizzes": sum(not quiz.is_active or quiz.editorial_status == EDITORIAL_STATUS_ARCHIVED for quiz in imported_quizzes),
            "student_visible_quizzes": sum(quiz.id in visible_ids for quiz in imported_quizzes),
            "required_quiz_ids": sorted(required_ids),
            "optional_visible_quiz_ids": sorted(optional_visible_ids),
        },
        "integrity": {
            "invalid_or_duplicate_option_questions": integrity,
            "exact_duplicate_question_groups": [group for group in text_groups.values() if len(group) > 1],
            "duplicate_import_identifier_groups": [group for group in fingerprints.values() if len(group) > 1],
        },
        "quiz_summary": {
            "total": len(quizzes),
            "active": sum(quiz.is_active for quiz in quizzes),
            "classifications": dict(classifications),
            "strict_disconnected_active_imported_quiz_ids": strict_disconnected,
        },
        "quizzes": quiz_records,
    }


def _markdown(report: dict) -> str:
    imported = report["imported"]
    all_questions = imported["all"]
    required = imported["required_curriculum"]
    optional = imported["optional_visible"]
    archive = imported["unused_or_archive"]
    lines = [
        "# Imported Question and Quiz Audit",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Authorship boundary",
        "",
        report["authorship_rule"],
        "Question-level `source` text is not used for population statistics.",
        "",
        "## Imported question inventory",
        "",
        f"- Imported questions: {all_questions['questions']} ({all_questions['single_answer']} single-answer; {all_questions['multi_select']} multi-select)",
        f"- Imported quizzes: {imported['active_quizzes']} active; {imported['hidden_or_archived_quizzes']} hidden/archived; {imported['student_visible_quizzes']} student-visible",
        f"- Required curriculum: {required['questions']} questions in quizzes {imported['required_quiz_ids']}",
        f"- Optional visible: {optional['questions']} questions in quizzes {imported['optional_visible_quiz_ids']}",
        f"- Unused/archive-only: {archive['questions']} questions",
        "",
        "## Required curriculum review",
        "",
        f"- Required imported quizzes: {len(imported['required_quiz_ids'])}; questions reviewed: {required['questions']}",
        f"- Structural integrity findings in required imported questions: {sum(1 for finding in report['integrity']['invalid_or_duplicate_option_questions'] if finding['quiz_id'] in imported['required_quiz_ids'])}",
        f"- Required explanation coverage: {required['explanations']}/{required['questions']} ({required['explanation_percent']}%)",
        "- Required imported questions retain their original IDs and keys; no uncertain answer key was guessed or rewritten.",
        "",
        "## Explanation coverage",
        "",
        "| Population | Present | Missing | Coverage |",
        "|---|---:|---:|---:|",
    ]
    for label, stats in (("All imported", all_questions), ("Required", required), ("Optional visible", optional), ("Unused/archive", archive)):
        lines.append(f"| {label} | {stats['explanations']} | {stats['missing_explanations']} | {stats['explanation_percent']}% |")
    lines += [
        "",
        "## Integrity and risk signals",
        "",
        f"- Invalid structures or duplicate options: {len(report['integrity']['invalid_or_duplicate_option_questions'])}",
        f"- Exact duplicate question groups: {len(report['integrity']['exact_duplicate_question_groups'])}",
        f"- Duplicate import identifier groups: {len(report['integrity']['duplicate_import_identifier_groups'])}",
        f"- Strict active-disconnected imported quizzes: {len(report['quiz_summary']['strict_disconnected_active_imported_quiz_ids'])}",
        "",
        "## Answer-pattern signals",
        "",
        "| Population | A | B | C | D | Uniquely-longest correct |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, stats in (("All imported", all_questions), ("Required", required)):
        positions = stats["correct_position_distribution"]
        lines.append(f"| {label} | {positions['A']} | {positions['B']} | {positions['C']} | {positions['D']} | {stats['uniquely_longest_correct']}/{stats['single_answer']} ({stats['uniquely_longest_correct_percent']}%) |")
    lines += [
        "",
        "## Quiz inventory and decision record",
        "",
        "`HIDE / ARCHIVE` preserves quiz/question IDs and attempts; it does not delete history.",
        "",
        "| ID | Title | Source | Questions | Current usage | Classification | Action |",
        "|---:|---|---|---:|---|---|---|",
    ]
    for quiz in report["quizzes"]:
        usage = ", ".join(quiz["usage"])
        title = quiz["title"].replace("|", "\\|")
        lines.append(
            f"| {quiz['id']} | {title} | {quiz['source']} | {quiz['question_count']} | "
            f"{usage} | {quiz['classification']} | {quiz['action']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True)
    parser.add_argument("--markdown", required=True)
    args = parser.parse_args()
    db = SessionLocal()
    try:
        report = run_audit(db)
    finally:
        db.close()
    Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    Path(args.markdown).write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report["imported"]["all"], sort_keys=True))


if __name__ == "__main__":
    main()
