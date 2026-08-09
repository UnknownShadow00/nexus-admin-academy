"""Apply reviewed, high-confidence quiz explanations.

Revision ID: 0037_curated_question_explanations
Revises: 0032_service_desk_trusted_events
Create Date: 2026-08-08
"""

from alembic import op
import hashlib
import json
from pathlib import Path
import sqlalchemy as sa


revision = "0037_curated_question_explanations"
down_revision = "0032_service_desk_trusted_events"
branch_labels = None
depends_on = None


CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "question_explanations.json"


def load_question_explanations():
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return raw.get("explanations", {})


def question_signature(question_text, options, correct_answers):
    normalized = json.dumps({
        "question": " ".join((question_text or "").split()).casefold(),
        "options": [" ".join((option or "").split()).casefold() for option in options],
        "correct_answers": sorted(answer.strip().upper() for answer in correct_answers),
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _rows(connection):
    return connection.execute(sa.text("""
        SELECT id, question_text, option_a, option_b, option_c, option_d,
               option_e, option_f, option_g, option_h, correct_answer, correct_answers,
               explanation
        FROM questions
    """)).mappings()


def _signature(row) -> str:
    answers = [
        item.strip()
        for item in (row["correct_answers"] or row["correct_answer"] or "").split(",")
        if item.strip()
    ]
    options = [row[f"option_{letter}"] or "" for letter in "abcdefgh"]
    return question_signature(row["question_text"], options, answers)


def upgrade() -> None:
    connection = op.get_bind()
    catalog = load_question_explanations()
    for row in _rows(connection):
        if row["explanation"] and row["explanation"].strip():
            continue
        explanation = catalog.get(_signature(row))
        if explanation:
            connection.execute(
                sa.text("UPDATE questions SET explanation = :explanation WHERE id = :id"),
                {"id": row["id"], "explanation": explanation},
            )


def downgrade() -> None:
    connection = op.get_bind()
    catalog = load_question_explanations()
    for row in _rows(connection):
        explanation = catalog.get(_signature(row))
        if explanation and row["explanation"] == explanation:
            connection.execute(
                sa.text("UPDATE questions SET explanation = NULL WHERE id = :id"),
                {"id": row["id"]},
            )
