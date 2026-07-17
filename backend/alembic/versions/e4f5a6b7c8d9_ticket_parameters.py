"""Per-student ticket parametrization — TB-05.

Adds Ticket.parameters: {"placeholders": {"NAME": ["opt1", ...], ...}}.
Values resolve deterministically per student (student_id % len(options)) and
are substituted server-side into title/description/hints/grading context, so
five students see five different concrete scenarios from one ticket row.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-10
"""
import sqlalchemy as sa
from alembic import op

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("tickets", "parameters")
