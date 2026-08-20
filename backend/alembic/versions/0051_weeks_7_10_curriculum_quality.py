"""Align Weeks 7-10 and rebuild networking practice.

Revision ID: 0051_weeks_7_10_quality
Revises: 0050_weeks_3_6_quality
Create Date: 2026-08-20
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_7_10_quality


revision = "0051_weeks_7_10_quality"
down_revision = "0050_weeks_3_6_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_weeks_7_10_quality(session)
    finally:
        session.close()


def downgrade() -> None:
    pass
