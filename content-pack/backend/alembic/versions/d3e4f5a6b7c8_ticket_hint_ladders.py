"""Ticket hint ladders — TB-04.

Adds Ticket.hints (JSON list, ≤4 progressive hints) and
TicketSubmission.hints_used (int) so hint reveals reduce XP per the
documented penalty ladder (−5/−10/−20/−35%, floor 40%).

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-10
"""
import sqlalchemy as sa
from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("hints", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column(
        "ticket_submissions",
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("ticket_submissions", "hints_used")
    op.drop_column("tickets", "hints")
