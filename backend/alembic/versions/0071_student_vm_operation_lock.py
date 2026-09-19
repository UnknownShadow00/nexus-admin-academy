"""Serialize student deletion with VM assignment creation.

Revision ID: 0071_student_vm_operation_lock
Revises: 0070_vm_singleton_key
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0071_student_vm_operation_lock"
down_revision = "0070_vm_singleton_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "students",
        sa.Column("vm_operation_lock", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "students",
        sa.Column("vm_operation_lock_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("students", "vm_operation_lock_at")
    op.drop_column("students", "vm_operation_lock")
