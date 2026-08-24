"""Convert Windows, Active Directory, and server labs into evidence cases.

Revision ID: 0059_windows_ad_server_practical_upgrade
Revises: 0058_intune_endpoint_management
Create Date: 2026-08-24

Schema-free and identity-preserving: the migration updates nine existing
LabTemplate rows and their existing TrainingWeekActivity role metadata. It
does not create or delete curriculum activities or LabRun rows.
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.windows_ad_server_practical import (
    restore_pre_4c1_practical_labs,
    sync_windows_ad_server_practical_upgrade,
)


revision = "0059_windows_ad_server_practical_upgrade"
down_revision = "0058_intune_endpoint_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_windows_ad_server_practical_upgrade(session)
    finally:
        session.close()


def downgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        restore_pre_4c1_practical_labs(session)
    finally:
        session.close()
