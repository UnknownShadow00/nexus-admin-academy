"""Classify all 71 reviewed active-but-unmapped legacy quizzes."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import or_

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.quiz import Question, Quiz  # noqa: E402
from app.services.quiz_editorial_mapping import (  # noqa: E402
    SAFE_OPTIONAL_QUIZ_MAPPINGS,
    apply_safe_optional_quiz_mappings,
)


REVIEWED_IDS = [
    26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
    43, 44, 46, 47, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60, 62,
    63, 64, 65, 66, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 79, 80,
    81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 96, 97,
    98, 99, 100, 101, 102, 103, 104,
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", default="../docs/unmapped_quiz_mapping_report.json")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        decisions = []
        for quiz_id in REVIEWED_IDS:
            quiz = db.get(Quiz, quiz_id)
            if not quiz:
                decisions.append({"quiz_id": quiz_id, "classification": "F", "decision": "missing"})
                continue
            missing = db.query(Question.id).filter(
                Question.quiz_id == quiz_id,
                or_(Question.explanation.is_(None), Question.explanation == ""),
            ).count()
            safe = SAFE_OPTIONAL_QUIZ_MAPPINGS.get(quiz_id)
            target_class = "C" if quiz.quiz_purpose == "remediation" else "B"
            decisions.append({
                "quiz_id": quiz.id,
                "title": quiz.title,
                "classification": target_class if safe else "F",
                "pedagogical_home": safe[0] if safe else quiz.recommended_week or quiz.week_number,
                "intended_role": safe[1] if safe else quiz.quiz_purpose,
                "missing_explanations": missing,
                "decision": "mapped_to_extra_practice" if safe else "intentionally_left_unmapped",
                "reason": (
                    "Complete explanations and a clear week-level practice role; optional and non-blocking."
                    if safe
                    else "Relevant as future optional/remediation material, but not appropriate for active student use until its remaining explanations and answer-key quality receive editorial review."
                ),
            })
        if args.apply:
            apply_safe_optional_quiz_mappings(db)
            db.commit()
        output = (BACKEND_ROOT / args.output).resolve()
        output.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "original_unmapped_count": len(REVIEWED_IDS),
            "mapped_optional_count": sum(item["decision"] == "mapped_to_extra_practice" for item in decisions),
            "intentionally_left_unmapped_count": sum(item["decision"] == "intentionally_left_unmapped" for item in decisions),
            "required_blockers_added": 0,
            "decisions": decisions,
        }, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"reviewed": len(decisions), "mapped": len(SAFE_OPTIONAL_QUIZ_MAPPINGS), "applied": args.apply}))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
