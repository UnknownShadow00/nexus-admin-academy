"""Restore reviewed training references needed by a brand-new seeded database.

Production already contains these records. The seed is intentionally
idempotent and preserves their stable IDs because weekly activity metadata
references those IDs directly.
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.curriculum_video import CurriculumVideo
from app.models.quiz import Question, Quiz


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "training_reference_content.json"


def _load() -> dict:
    with DATA_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def ensure_training_reference_content(db: Session) -> dict:
    data = _load()
    created_videos = 0
    created_quizzes = 0

    for payload in data["videos"]:
        expected_id = int(payload["id"])
        existing = db.query(CurriculumVideo).filter(CurriculumVideo.id == expected_id).first()
        if existing:
            if existing.video_key != payload["video_key"]:
                raise RuntimeError(f"Video ID {expected_id} is occupied by unexpected content")
            continue
        duplicate_key = db.query(CurriculumVideo).filter(CurriculumVideo.video_key == payload["video_key"]).first()
        if duplicate_key:
            raise RuntimeError(f"Video key {payload['video_key']} exists with unexpected ID {duplicate_key.id}")
        db.add(CurriculumVideo(**payload))
        created_videos += 1

    db.flush()
    for payload in data["quizzes"]:
        questions = payload.pop("questions")
        expected_id = int(payload["id"])
        existing = db.query(Quiz).filter(Quiz.id == expected_id).first()
        if existing:
            if existing.title != payload["title"]:
                raise RuntimeError(f"Quiz ID {expected_id} is occupied by unexpected content")
            continue
        duplicate_title = db.query(Quiz).filter(Quiz.title == payload["title"]).first()
        if duplicate_title:
            raise RuntimeError(f"Quiz {payload['title']} exists with unexpected ID {duplicate_title.id}")
        quiz = Quiz(**payload)
        db.add(quiz)
        db.flush()
        for question in questions:
            db.add(Question(quiz_id=quiz.id, **question))
        created_quizzes += 1

    return {"videos": created_videos, "quizzes": created_quizzes}
