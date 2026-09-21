"""Require password rotation for newly administered student credentials.

Revision ID: 0071_forced_first_login_password_change
Revises: 0070_beginner_content_ux_polish
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = "0071_forced_first_login_password_change"
down_revision = "0070_beginner_content_ux_polish"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_auth_states",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_id"),
    )


def downgrade() -> None:
    op.drop_table("student_auth_states")
