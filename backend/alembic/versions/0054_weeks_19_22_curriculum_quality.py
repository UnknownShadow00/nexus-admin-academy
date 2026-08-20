"""Align Weeks 19-22 and add production-support practice.

Revision ID: 0054_weeks_19_22_quality
Revises: 0053_weeks_15_18_quality
Create Date: 2026-08-20
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_19_22_quality


revision = "0054_weeks_19_22_quality"
down_revision = "0053_weeks_15_18_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_weeks_19_22_quality(session)
    finally:
        session.close()


def downgrade() -> None:
    pass
