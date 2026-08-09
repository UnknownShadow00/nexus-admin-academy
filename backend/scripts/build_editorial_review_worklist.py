"""Build the conservative legacy-question editorial worklist.

The visibility gate already keeps unvalidated legacy banks away from students.
This report makes that queue reviewable without treating a missing explanation
as permission to publish. It is deliberately keyed to question content and
includes the stored key, options, provenance, curriculum location, and an
explicit editorial disposition for every question in the original 397-item
queue.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.quiz import Question, Quiz  # noqa: E402


APPROVED_BACKUP_QUESTION_IDS = {680, 681, 682, 683}
AMBIGUOUS_QUESTION_IDS = {970}

TOPIC_RULES = (
    ("Active Directory", ("active directory",)),
    ("Microsoft 365", ("microsoft 365", "entra", "office")),
    ("Windows", ("windows", "bios", "uefi", "ntfs", "mmc", "task manager")),
    ("Hardware", ("ram", "storage", "cpu", "power", "motherboard", "display", "cabling", "connector", "printer", "mobile device")),
    ("Networking", ("network", "wireless", "ip addressing", "internet connection", "protocol", "cabling")),
    ("Security", ("security", "malware", "physical security", "logical security")),
    ("Troubleshooting", ("troubleshooting", "removal procedures", "boot methods")),
    ("Help Desk", ("communication", "change management", "asset management", "regulated data", "safety", "environmental")),
    ("Linux", ("linux", "filesystem")),
    ("Cloud", ("cloud",)),
    ("Command Line", ("command-line", "scripting", "networking tools")),
    ("Virtualization", ("virtualization",)),
)


def topic_for(title: str) -> str:
    normalized = title.casefold()
    for topic, phrases in TOPIC_RULES:
        if any(phrase in normalized for phrase in phrases):
            return topic
    return "Other"


def options_for(question: Question) -> dict[str, str]:
    return {
        letter: value
        for letter in "ABCDEFGH"
        if (value := getattr(question, f"option_{letter.lower()}"))
    }


def disposition_for(question: Question) -> tuple[str, str]:
    if question.id in APPROVED_BACKUP_QUESTION_IDS:
        return "A", "Verified against standard backup definitions; explanation added and approved only as Week 17 optional practice."
    if question.id in AMBIGUOUS_QUESTION_IDS:
        return "D", "'BIOS password' mixes setup/supervisor and power-on password concepts; no single answer is objectively correct."
    return "H", "Legacy imported content has no item-level authoritative verification record. Keep hidden until its wording, key, and explanation receive an evidence-backed review."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="../docs/question_explanation_review.json")
    parser.add_argument("--output", default="../docs/editorial_review_worklist.json")
    args = parser.parse_args()

    source = (BACKEND_ROOT / args.source).resolve()
    output = (BACKEND_ROOT / args.output).resolve()
    original_queue = json.loads(source.read_text(encoding="utf-8"))["human_review"]
    original_reasons = {item["question_id"]: item["reason"] for item in original_queue}

    db = SessionLocal()
    try:
        questions = (
            db.query(Question)
            .filter(Question.id.in_(original_reasons))
            .order_by(Question.id)
            .all()
        )
        records = []
        topic_counts = Counter()
        classification_counts = Counter()
        for question in questions:
            quiz = question.quiz
            classification, disposition = disposition_for(question)
            topic = topic_for(quiz.title)
            topic_counts[topic] += 1
            classification_counts[classification] += 1
            records.append({
                "question_id": question.id,
                "topic": topic,
                "classification": classification,
                "disposition": disposition,
                "previous_review_reason": original_reasons[question.id],
                "quiz": {
                    "id": quiz.id,
                    "title": quiz.title,
                    "week_number": quiz.week_number,
                    "lesson_id": quiz.lesson_id,
                    "status": quiz.status,
                    "editorial_status": quiz.editorial_status,
                    "source_type": quiz.source_type,
                    "is_student_visible": quiz.status == "published" and quiz.is_active and quiz.editorial_status == "validated" and quiz.answer_keys_validated,
                },
                "question_text": question.question_text,
                "options": options_for(question),
                "stored_correct_answer": question.correct_answer,
                "stored_correct_answers": question.correct_answers,
                "existing_explanation": question.explanation,
                "difficulty": question.difficulty,
                "tags": question.tags,
                "source": question.source,
                "import_filename": question.import_filename,
                "flagged_for_review": question.flagged_for_review,
                "flag_reason": question.flag_reason,
            })

        by_quiz = defaultdict(list)
        for record in records:
            by_quiz[record["quiz"]["id"]].append(record["question_id"])
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Original 397-item human-review queue from question_explanation_review.json",
            "question_count": len(records),
            "topic_counts": dict(sorted(topic_counts.items())),
            "classification_counts": dict(sorted(classification_counts.items())),
            "quiz_count": len(by_quiz),
            "approved_question_ids": sorted(APPROVED_BACKUP_QUESTION_IDS),
            "ambiguous_question_ids": sorted(AMBIGUOUS_QUESTION_IDS),
            "questions": records,
        }
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"questions": len(records), "topics": dict(topic_counts), "classifications": dict(classification_counts)}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
