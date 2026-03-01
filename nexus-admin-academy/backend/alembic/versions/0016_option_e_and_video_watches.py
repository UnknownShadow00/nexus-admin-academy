"""add question option_e and study tracker tables

Revision ID: 0016
Revises: 0015_fix_best_score_constraint
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015_fix_best_score_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("option_e", sa.Text(), nullable=True))

    op.create_table(
        "video_watches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_key", sa.String(200), nullable=False),
        sa.Column("watched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "video_key", name="uq_video_watches"),
    )
    op.create_index("ix_video_watches_student_id", "video_watches", ["student_id"])

    op.create_table(
        "curriculum_videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_key", sa.String(200), unique=True, nullable=False),
        sa.Column("section", sa.String(200), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("duration", sa.String(20), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("quiz_title", sa.String(300), nullable=True),
        sa.Column("video_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_table("curriculum_videos")
    op.drop_index("ix_video_watches_student_id", table_name="video_watches")
    op.drop_table("video_watches")
    op.drop_column("questions", "option_e")
