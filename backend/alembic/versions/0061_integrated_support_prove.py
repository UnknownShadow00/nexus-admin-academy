"""Phase 4C.3 integrated support prove: Final Support Shift.

Converts two existing Week 23/24 LabTemplate rows (21 and 22) and their
TrainingWeekActivity role metadata in place, and adds one new PromotionGate
row for the graduating role ("Junior Infrastructure Administrator") pinning
graduation to a passing score on the new Week 24 Final Support Shift.

Schema-free and reversible. No activity, LabRun, CLI attempt, or video-watch
row is created or deleted. Historical LabRuns against the old Week 24 content
are preserved untouched — they simply do not satisfy the new gate, since
only a LabRun graded under the versioned final-shift rubric counts (see
app/services/progression_service.py::_check_required_lab_pass).

Revision ID: 0061_integrated_support_prove
Revises: 0060_network_linux_cloud_practical_upgrade
Create Date: 2026-08-25
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.integrated_support_final_shift import (
    restore_pre_4c3_final_shift,
    sync_integrated_support_final_shift_upgrade,
)


revision = "0061_integrated_support_prove"
down_revision = "0060_network_linux_cloud_practical_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_integrated_support_final_shift_upgrade(session)
    finally:
        session.close()


def downgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        restore_pre_4c3_final_shift(session)
    finally:
        session.close()
