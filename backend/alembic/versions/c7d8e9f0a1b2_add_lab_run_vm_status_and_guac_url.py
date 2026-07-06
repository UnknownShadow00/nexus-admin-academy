"""add_lab_run_vm_status_and_guac_url

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-07-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_runs", sa.Column("vm_status", sa.String(20), nullable=True))
    op.add_column("lab_runs", sa.Column("guac_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("lab_runs", "guac_url")
    op.drop_column("lab_runs", "vm_status")
