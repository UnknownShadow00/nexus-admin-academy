"""Persist asynchronous VM and scoped Guacamole state.

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-19
"""

import sqlalchemy as sa
from alembic import op


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("vm_assignments") as batch_op:
        batch_op.drop_index("ix_vm_assignments_lab_run_id")
        batch_op.alter_column("vmid", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("status", existing_type=sa.String(length=20), type_=sa.String(length=32))
        batch_op.add_column(sa.Column("guac_username", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("provisioning_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("provisioning_started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        batch_op.create_index("ix_vm_assignments_expires_at", ["expires_at"], unique=False)
        batch_op.create_index("ix_vm_assignments_lab_run_id", ["lab_run_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("vm_assignments") as batch_op:
        batch_op.drop_index("ix_vm_assignments_lab_run_id")
        batch_op.create_index("ix_vm_assignments_lab_run_id", ["lab_run_id"], unique=False)
        batch_op.drop_index("ix_vm_assignments_expires_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("provisioning_started_at")
        batch_op.drop_column("retry_count")
        batch_op.drop_column("provisioning_error")
        batch_op.drop_column("guac_username")
        batch_op.alter_column("status", existing_type=sa.String(length=32), type_=sa.String(length=20))
        batch_op.alter_column("vmid", existing_type=sa.Integer(), nullable=False)
