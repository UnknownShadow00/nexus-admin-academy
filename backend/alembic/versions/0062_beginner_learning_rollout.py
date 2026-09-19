"""Align the first curriculum stages to A+ then Network+.

This migration changes presentation order and optionality only. Stable week,
module, activity, lesson, quiz, ticket, and attempt identities are preserved.

Revision ID: 0062_beginner_learning_rollout
Revises: 0061_integrated_support_prove
Create Date: 2026-09-19
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import (
    BEGINNER_ROLLOUT_DISPLAY_ORDER,
    sync_beginner_learning_rollout,
)
from app.models.training import TrainingWeek, TrainingWeekActivity


revision = "0062_beginner_learning_rollout"
down_revision = "0061_integrated_support_prove"
branch_labels = None
depends_on = None


_PREVIOUS_DISPLAY_ORDER = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9,
    13: 10, 14: 11, 15: 12,
    25: 13, 26: 14, 27: 15, 28: 16, 29: 17,
    30: 18, 31: 19, 32: 20, 33: 21, 34: 22,
    10: 23, 11: 24, 12: 25,
    16: 26, 17: 27, 18: 28, 19: 29, 20: 30,
    21: 31, 22: 32, 23: 33, 24: 34,
}


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_beginner_learning_rollout(session)
    finally:
        session.close()


def downgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        for week in session.query(TrainingWeek).filter(
            TrainingWeek.week_number.in_(set(BEGINNER_ROLLOUT_DISPLAY_ORDER))
        ):
            if week.week_number in _PREVIOUS_DISPLAY_ORDER:
                week.display_order = _PREVIOUS_DISPLAY_ORDER[week.week_number]
        week_10 = session.query(TrainingWeek).filter_by(week_number=10).first()
        if week_10 is not None:
            for activity in session.query(TrainingWeekActivity).filter(
                TrainingWeekActivity.training_week_id == week_10.id,
                TrainingWeekActivity.activity_type == "networking_lab",
                TrainingWeekActivity.content_ref.in_({"dev-sw-act-04", "dev-sw-act-18"}),
            ):
                activity.is_required = True
        session.commit()
    finally:
        session.close()
