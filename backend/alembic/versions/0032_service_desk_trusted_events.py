"""Separate server-verified Service Desk evidence from browser event uploads.

Revision ID: 0032_service_desk_trusted_events
Revises: 0036_service_desk_mentor_feedback
"""

import sqlalchemy as sa
from alembic import op

revision = "0032_service_desk_trusted_events"
down_revision = "0036_service_desk_mentor_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_desk_attempt_events",
        sa.Column("trusted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("service_desk_attempt_events", "trusted")
