"""add commands_used to ticket submissions

Revision ID: 0009_ticket_commands_used
Revises: 0008_competency_engine_foundation
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_ticket_commands_used"
down_revision = "0008_competency_engine_foundation"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    cols = _columns("ticket_submissions")
    if "commands_used" not in cols:
        op.add_column("ticket_submissions", sa.Column("commands_used", sa.Text(), nullable=True))


def downgrade() -> None:
    cols = _columns("ticket_submissions")
    if "commands_used" in cols:
        op.drop_column("ticket_submissions", "commands_used")

