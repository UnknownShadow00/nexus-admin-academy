"""Restore Study Tracker metadata and extended quiz options.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op


revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("curriculum_videos", sa.Column("exam_code", sa.String(20), nullable=True))
    op.add_column("questions", sa.Column("option_f", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("option_g", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("option_h", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "option_h")
    op.drop_column("questions", "option_g")
    op.drop_column("questions", "option_f")
    op.drop_column("curriculum_videos", "exam_code")
