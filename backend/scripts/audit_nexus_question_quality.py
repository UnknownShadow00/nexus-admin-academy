"""Audit the Nexus-authored quiz bank without touching imported questions.

Usage (against an isolated/fresh database):
  DATABASE_URL=sqlite:////tmp/nexus.db .venv/bin/python \
    scripts/audit_nexus_question_quality.py --json ../docs/nexus_question_quality.json \
    --markdown ../docs/NEXUS_QUESTION_QUALITY_AUDIT.md
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
from app.models.quiz import Question, Quiz, SOURCE_TYPE_SEED  # noqa: E402
from app.services.question_validation import validate_question_row  # noqa: E402


LETTERS = "ABCDEFGH"
DECISION_WORDS = re.compile(r"\b(first|best|next|most likely|most appropriate|should|primary)\b", re.I)


def _options(question: Question) -> dict[str, str]:
    return {
        letter: (getattr(question, f"option_{letter.lower()}") or "").strip()
        for letter in LETTERS
        if (getattr(question, f"option_{letter.lower()}") or "").strip()
    }


def _correct_is_uniquely_longest(question: Question) -> bool:
    if question.is_multi_select:
        return False
    options = _options(question)
    correct = options.get(question.correct_answer)
    if not correct:
        return False
    return all(len(correct) > len(option) for letter, option in options.items() if letter != question.correct_answer)


def _classification(question: Question, quiz: Quiz) -> tuple[str, str, str]:
    """Return a maintainable, conservative editorial worklist classification."""
    required = bool(quiz.is_required)
    if "internet is down" in question.question_text.casefold():
        return "REWRITE STEM", "P0", "Original scope was unstated, so screenshot and scope questions were both defensible."
    validation = validate_question_row(question)
    if not validation.valid:
        return "FACT/CORRECTNESS REVIEW", "P0", "; ".join(issue.message for issue in validation.errors)
    if question.is_multi_select:
        return "KEEP", "P1" if required else "P2", "Multi-select reviewed for explicit selection count and exact-set mapping."
    if DECISION_WORDS.search(question.question_text):
        return "REWRITE STEM", "P1" if required else "P2", "Decision wording needs sufficient scenario context."
    if _correct_is_uniquely_longest(question):
        return "REWRITE DISTRACTORS", "P1" if required else "P2", "Correct option is uniquely longest; make options naturally comparable."
    return "KEEP", "P3", "No mechanical clue detected; retain under normal editorial review."


def run_audit(db) -> dict:
    rows = (
        db.query(Question, Quiz)
        .join(Quiz, Quiz.id == Question.quiz_id)
        .filter(Quiz.source_type == SOURCE_TYPE_SEED)
        .order_by(Quiz.id, Question.id)
        .all()
    )
    records = []
    positions = Counter()
    classifications = Counter()
    priorities = Counter()
    quiz_counts = defaultdict(int)
    duplicate_groups = defaultdict(list)
    unique_longest = 0
    explanations = 0
    single = multi = required = active = 0

    for ordinal, (question, quiz) in enumerate(rows, start=1):
        is_multi = question.is_multi_select
        multi += int(is_multi)
        single += int(not is_multi)
        required += int(quiz.is_required)
        active += int(quiz.is_active)
        explanations += int(bool((question.explanation or "").strip()))
        quiz_counts[f"{quiz.id}: {quiz.title}"] += 1
        if not is_multi:
            positions[question.correct_answer] += 1
        longest = _correct_is_uniquely_longest(question)
        unique_longest += int(longest)
        classification, priority, rationale = _classification(question, quiz)
        classifications[classification] += 1
        priorities[priority] += 1
        normalized = re.sub(r"\W+", " ", question.question_text.casefold()).strip()
        duplicate_groups[normalized].append(question.seed_key or f"question:{question.id}")
        records.append({
            "seed_key": question.seed_key,
            "question_id": question.id,
            "quiz": quiz.title,
            "required": bool(quiz.is_required),
            "active": bool(quiz.is_active),
            "multi_select": is_multi,
            "correct_positions": question.all_correct_answers,
            "has_explanation": bool((question.explanation or "").strip()),
            "correct_uniquely_longest": longest,
            "classification": classification,
            "priority": priority,
            "rationale": rationale,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authorship_rule": "Quiz.source_type == 'seed'. Imported ExamCompass questions use source_type == 'examcompass' and are excluded.",
        "totals": {
            "questions": len(rows), "single_answer": single, "multi_select": multi,
            "required": required, "optional": len(rows) - required,
            "active": active, "inactive": len(rows) - active,
            "explanations": explanations, "missing_explanations": len(rows) - explanations,
            "uniquely_longest_correct": unique_longest,
            "uniquely_longest_correct_percent": round(100 * unique_longest / single, 1) if single else 0,
        },
        "quizzes": dict(quiz_counts),
        "single_answer_position_distribution": {letter: positions.get(letter, 0) for letter in "ABCD"},
        "classifications": dict(classifications),
        "priorities": dict(priorities),
        "exact_normalized_duplicate_groups": [group for group in duplicate_groups.values() if len(group) > 1],
        "records": records,
    }


def _markdown(report: dict) -> str:
    total = report["totals"]
    lines = [
        "# Nexus-Authored Question Quality Audit",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Scope and authorship rule",
        "",
        report["authorship_rule"],
        "This audit deliberately excludes the imported ExamCompass bank.",
        "",
        "## Summary",
        "",
        f"- Questions: {total['questions']} ({total['single_answer']} single-answer; {total['multi_select']} multi-select)",
        f"- Curriculum use: {total['required']} required; {total['optional']} optional",
        f"- Status: {total['active']} active; {total['inactive']} inactive",
        f"- Explanations: {total['explanations']} present; {total['missing_explanations']} missing",
        f"- Correct answer uniquely longest: {total['uniquely_longest_correct']}/{total['single_answer']} ({total['uniquely_longest_correct_percent']}%)",
        "",
        "## Single-answer key positions",
        "",
        "| A | B | C | D |",
        "|---:|---:|---:|---:|",
        "| {A} | {B} | {C} | {D} |".format(**report["single_answer_position_distribution"]),
        "",
        "## Classification counts",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for classification, count in sorted(report["classifications"].items()):
        lines.append(f"| {classification} | {count} |")
    lines += ["", "## Maintainable per-question worklist", "", "The JSON companion contains one non-sensitive record per authored question. This table uses stable `seed_key` identities rather than volatile database IDs.", "", "| Key | Quiz | Required | Class | Priority | Longest clue | Rationale |", "|---|---|---:|---|---|---:|---|"]
    for record in report["records"]:
        lines.append(
            "| {seed_key} | {quiz} | {required} | {classification} | {priority} | {correct_uniquely_longest} | {rationale} |".format(
                **{key: str(value).replace("|", "\\|") for key, value in record.items()}
            )
        )
    lines += ["", "## Duplicate detection", "", f"- Exact normalized duplicate groups: {len(report['exact_normalized_duplicate_groups'])}", "", "Near-duplicate semantic detection remains a human editorial task; this guard reports exact normalized duplicates without making subjective CI decisions.", ""]
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
    print(json.dumps(report["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
