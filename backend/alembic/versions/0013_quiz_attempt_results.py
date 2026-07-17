"""add quiz_attempts results

Revision ID: 0013_quiz_attempt_results
Revises: 0012_lesson_video_url
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_quiz_attempt_results"
down_revision = "0012_lesson_video_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.add_column(sa.Column("results", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.drop_column("results")
