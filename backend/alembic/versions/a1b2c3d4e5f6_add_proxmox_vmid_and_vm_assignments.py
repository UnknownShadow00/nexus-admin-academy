"""add_proxmox_vmid_and_vm_assignments

Revision ID: a1b2c3d4e5f6
Revises: 0456151c153d
Create Date: 2026-05-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "0456151c153d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lab_templates",
        sa.Column("proxmox_template_vmid", sa.Integer(), nullable=True),
    )

    op.create_table(
        "vm_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("vmid", sa.Integer(), nullable=False, index=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("lab_run_id", sa.Integer(), sa.ForeignKey("lab_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="provisioning"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("guac_conn_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("destroyed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("vm_assignments")
    op.drop_column("lab_templates", "proxmox_template_vmid")
