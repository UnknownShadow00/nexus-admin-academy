"""Upgrade network, Linux, and cloud practicals in place.

Revision ID: 0060_network_linux_cloud_practical_upgrade
Revises: 0059_windows_ad_server_practical_upgrade
Create Date: 2026-08-24

Schema-free and reversible. Seven existing LabTemplate rows and their
TrainingWeekActivity role metadata are updated without replacing identities,
and three existing Week 21 videos become optional. No activity, completion,
LabRun, CLI attempt, or video-watch row is created or deleted.
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.network_linux_cloud_practical import (
    restore_pre_4c2_practical_labs,
    sync_network_linux_cloud_practical_upgrade,
)


revision = "0060_network_linux_cloud_practical_upgrade"
down_revision = "0059_windows_ad_server_practical_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_network_linux_cloud_practical_upgrade(session)
    finally:
        session.close()


def downgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        restore_pre_4c2_practical_labs(session)
    finally:
        session.close()
