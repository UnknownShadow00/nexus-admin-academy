"""Preserve stable IDs when Nexus-authored seed content is revised.

Revision ID: 0045_preserve_authored_question_identity
Revises: 0044_lesson_completion_progress
Create Date: 2026-08-10
"""

import re

from alembic import op
import sqlalchemy as sa


revision = "0045_preserve_authored_question_identity"
down_revision = "0044_lesson_completion_progress"
branch_labels = None
depends_on = None


def _seed_key(title: str, ordinal: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    return f"nexus-authored:{slug}:{ordinal:02d}"


def upgrade() -> None:
    op.add_column("questions", sa.Column("seed_key", sa.String(length=160), nullable=True))
    bind = op.get_bind()
    # Use the stable source order within each explicitly Nexus-authored quiz.
    # IDs are never rewritten; this only attaches an identity to existing rows.
    quizzes = bind.execute(sa.text("""
        SELECT id, title FROM quizzes WHERE source_type = 'seed' ORDER BY id
    """)).mappings()
    for quiz in quizzes:
        question_ids = bind.execute(sa.text("""
            SELECT id FROM questions WHERE quiz_id = :quiz_id ORDER BY id
        """), {"quiz_id": quiz["id"]}).scalars()
        for ordinal, question_id in enumerate(question_ids, start=1):
            bind.execute(sa.text("""
                UPDATE questions SET seed_key = :seed_key WHERE id = :question_id
            """), {"seed_key": _seed_key(quiz["title"], ordinal), "question_id": question_id})
    op.create_index("ix_questions_seed_key", "questions", ["seed_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_questions_seed_key", table_name="questions")
    op.drop_column("questions", "seed_key")
