"""add_quiz_attempt_timing

Revision ID: 0456151c153d
Revises: 17dcbbab1af8
Create Date: 2026-05-17 19:42:16.498071
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0456151c153d"
down_revision = "17dcbbab1af8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quiz_attempts",
        sa.Column("time_per_question", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_attempts", "time_per_question")
