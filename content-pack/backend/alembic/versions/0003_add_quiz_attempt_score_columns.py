"""add quiz attempt score columns

Revision ID: 0003_add_quiz_attempt_score_columns
Revises: 0002_phase2_hardening
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_quiz_attempt_score_columns"
down_revision = "0002_phase2_hardening"
branch_labels = None
depends_on = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    cols = _get_columns("quiz_attempts")

    if "best_score" not in cols:
        op.add_column("quiz_attempts", sa.Column("best_score", sa.Integer(), nullable=True))
    if "first_attempt_xp" not in cols:
        op.add_column("quiz_attempts", sa.Column("first_attempt_xp", sa.Integer(), nullable=True))


def downgrade() -> None:
    cols = _get_columns("quiz_attempts")

    if "first_attempt_xp" in cols:
        op.drop_column("quiz_attempts", "first_attempt_xp")
    if "best_score" in cols:
        op.drop_column("quiz_attempts", "best_score")
