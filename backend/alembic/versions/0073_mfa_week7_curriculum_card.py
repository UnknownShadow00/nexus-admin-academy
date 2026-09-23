"""Place the seeded MFA curriculum card in Week 7 without losing history.

Revision ID: 0073_mfa_week7_curriculum_card
Revises: 0072_weeks_3_4_prelaunch_quality
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_mfa_week7_activity


revision = "0073_mfa_week7_curriculum_card"
down_revision = "0072_weeks_3_4_prelaunch_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with Session(bind=op.get_bind()) as session:
        sync_mfa_week7_activity(session)
        session.commit()


def downgrade() -> None:
    # The learner-facing Week 4 defect must not be recreated by a downgrade.
    # Application rollback can retain the corrected curriculum association.
    pass
