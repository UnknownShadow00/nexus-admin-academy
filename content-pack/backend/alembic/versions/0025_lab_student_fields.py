"""add lab student-facing fields

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_templates", sa.Column("week_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("lab_templates", sa.Column("is_published", sa.Boolean(), nullable=False, server_default="1"))
    op.add_column("lab_runs", sa.Column("notes", sa.Text(), nullable=True))
    op.create_index("ix_lab_templates_week_number", "lab_templates", ["week_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lab_templates_week_number", table_name="lab_templates")
    op.drop_column("lab_runs", "notes")
    op.drop_column("lab_templates", "is_published")
    op.drop_column("lab_templates", "week_number")
