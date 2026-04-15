"""add is mentor field

Revision ID: 0024
Revises: 0023
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("is_mentor", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("students", "is_mentor")
