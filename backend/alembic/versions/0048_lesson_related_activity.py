"""Allow lessons to deep-link to a weekly training activity.

Revision ID: 0048_lesson_related_activity
Revises: 0047_student_service_desk_progression
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0048_lesson_related_activity"
down_revision = "0047_student_service_desk_progression"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "lessons",
        sa.Column("related_activity_stable_id", sa.String(length=160), nullable=True),
    )


def downgrade():
    op.drop_column("lessons", "related_activity_stable_id")
