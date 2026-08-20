"""Align Weeks 11-14 and add deterministic practice.

Revision ID: 0052_weeks_11_14_quality
Revises: 0051_weeks_7_10_quality
Create Date: 2026-08-20
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_11_14_quality


revision = "0052_weeks_11_14_quality"
down_revision = "0051_weeks_7_10_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_weeks_11_14_quality(session)
    finally:
        session.close()


def downgrade() -> None:
    pass
