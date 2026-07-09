"""add job relevance tags to curriculum videos

Revision ID: 0017
Revises: 0016
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "curriculum_videos",
        sa.Column("job_relevance", sa.String(length=20), nullable=False, server_default="know_it"),
    )


def downgrade() -> None:
    op.drop_column("curriculum_videos", "job_relevance")
