"""add lesson video_url

Revision ID: 0012_lesson_video_url
Revises: 0011_quiz_multi_video
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_lesson_video_url"
down_revision = "0011_quiz_multi_video"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("lessons") as batch_op:
        batch_op.add_column(sa.Column("video_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("lessons") as batch_op:
        batch_op.drop_column("video_url")
