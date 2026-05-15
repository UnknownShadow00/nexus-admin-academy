"""add capstone student-facing fields

Revision ID: 0026
Revises: 0025
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("capstone_templates", sa.Column("week_number", sa.Integer(), nullable=True))
    op.add_column("capstone_templates", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("capstone_runs", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("capstone_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("capstone_runs", sa.Column("feedback", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("capstone_runs", "feedback")
    op.drop_column("capstone_runs", "started_at")
    op.drop_column("capstone_runs", "notes")
    op.drop_column("capstone_templates", "is_published")
    op.drop_column("capstone_templates", "week_number")
