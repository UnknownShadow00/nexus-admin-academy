"""Align beginner Weeks 3-4 learning, practice, and troubleshooting.

Revision ID: 0072_weeks_3_4_prelaunch_quality
Revises: 0071_forced_first_login_password_change
Create Date: 2026-09-22
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_3_4_prelaunch_quality


revision = "0072_weeks_3_4_prelaunch_quality"
down_revision = "0071_forced_first_login_password_change"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    with Session(bind=bind) as session:
        sync_weeks_3_4_prelaunch_quality(session)


def downgrade() -> None:
    # Learner attempts and history are intentionally retained. Reintroducing
    # the mismatched future-topic activities would recreate the launch defect.
    pass
