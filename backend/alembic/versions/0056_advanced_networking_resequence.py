"""Resequence advanced networking after Identity & Access (Phase 4A.1).

Moves TrainingWeek.display_order for weeks 10-12 (Switching & VLANs, Routing
& Network Services, Secure Network Administration) to occur after weeks
13-15 (Active Directory Foundations, Domain Operations & File Services,
Group Policy), reserving the slot in between for the future Microsoft
365/Entra/Endpoint Management stage. week_number is never changed by this
migration -- it is the stable identity key every other progression system
(MODULE_WEEKS, CLI_PACK_WEEKS, SERVICE_DESK_PACKS, Quiz.week_number,
curriculum_structure.py source_week_number, and every activity/progress
record) keys off, so no student completion evidence is moved, duplicated, or
reset by this change. See docs/JOB_READY_CURRICULUM_BLUEPRINT.md section 0
and the Phase 4A.1 report for the full analysis.

Revision ID: 0056_advanced_networking_resequence
Revises: 0055_weeks_23_24_quality
Create Date: 2026-08-23
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_advanced_networking_resequence


revision = "0056_advanced_networking_resequence"
down_revision = "0055_weeks_23_24_quality"
branch_labels = None
depends_on = None

# upgrade() display_order targets, reused by downgrade() to swap back.
_REVERT_TARGETS = {10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15}


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_advanced_networking_resequence(session)
    finally:
        session.close()


def downgrade() -> None:
    from app.models.training import TrainingWeek

    session = Session(bind=op.get_bind())
    try:
        weeks = {
            row.week_number: row
            for row in session.query(TrainingWeek)
            .filter(TrainingWeek.week_number.in_(_REVERT_TARGETS))
            .all()
        }
        for week_number, original_order in _REVERT_TARGETS.items():
            week = weeks.get(week_number)
            if week is not None:
                week.display_order = original_order
        session.commit()
    finally:
        session.close()
