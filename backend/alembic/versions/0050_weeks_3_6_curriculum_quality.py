"""Align Weeks 3-6 with the beginner Learn-Quiz-Practice-Apply path.

Revision ID: 0050_weeks_3_6_quality
Revises: 0049_lab_run_structured_feedback
Create Date: 2026-08-20

Requirement flags and activities are updated in place. Existing lesson notes,
quiz attempts, lab runs, and Service Desk history remain intact.
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_3_6_quality


revision = "0050_weeks_3_6_quality"
down_revision = "0049_lab_run_structured_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_weeks_3_6_quality(session)
    finally:
        session.close()


def downgrade() -> None:
    # Curriculum history and completion records are intentionally not reset.
    pass
