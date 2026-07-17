"""add student auth fields

Revision ID: 0023
Revises: 0022
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("username", sa.String(length=100), nullable=True))
    op.add_column("students", sa.Column("password_hash", sa.String(length=200), nullable=True))
    op.create_index("ix_students_username", "students", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_students_username", table_name="students")
    op.drop_column("students", "password_hash")
    op.drop_column("students", "username")
