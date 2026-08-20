"""Align the final numbered curriculum weeks.

Revision ID: 0055_weeks_23_24_quality
Revises: 0054_weeks_19_22_quality
Create Date: 2026-08-20
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_weeks_23_24_quality


revision = "0055_weeks_23_24_quality"
down_revision = "0054_weeks_19_22_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_weeks_23_24_quality(session)
    finally:
        session.close()


def downgrade() -> None:
    pass
