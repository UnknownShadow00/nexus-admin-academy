"""Store server-computed feedback for structured lab exercises.

Revision ID: 0049_lab_run_structured_feedback
Revises: 0048_lesson_related_activity
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0049_lab_run_structured_feedback"
down_revision = "0048_lesson_related_activity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lab_runs",
        sa.Column(
            "structured_feedback",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("lab_runs", "structured_feedback")
