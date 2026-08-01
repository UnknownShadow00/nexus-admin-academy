"""Add mentor feedback fields to Service Desk grades.

Revision ID: 0036_service_desk_mentor_feedback
Revises: ba877d258c82
"""

import sqlalchemy as sa
from alembic import op


revision = "0036_service_desk_mentor_feedback"
down_revision = "ba877d258c82"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("service_desk_attempt_grades") as batch:
        batch.add_column(sa.Column("mentor_feedback", sa.Text(), nullable=True))
        batch.add_column(sa.Column("mentor_feedback_by", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("mentor_feedback_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("service_desk_attempt_grades") as batch:
        batch.drop_column("mentor_feedback_at")
        batch.drop_column("mentor_feedback_by")
        batch.drop_column("mentor_feedback")
