"""Align Weeks 15-18 and add command practice.

Revision ID: 0053_weeks_15_18_quality
Revises: 0052_weeks_11_14_quality
Create Date: 2026-08-20
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_15_18_quality


revision = "0053_weeks_15_18_quality"
down_revision = "0052_weeks_11_14_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_weeks_15_18_quality(session)
    finally:
        session.close()


def downgrade() -> None:
    pass
