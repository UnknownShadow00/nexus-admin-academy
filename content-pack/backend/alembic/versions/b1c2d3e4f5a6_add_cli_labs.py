"""add cli labs

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "cli_lab",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("compartment_id", sa.String(length=100), nullable=False),
        sa.Column("vendor_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False, server_default="Beginner"),
        sa.Column("est_minutes", sa.Integer(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cli_lab_id", "cli_lab", ["id"], unique=False)
    op.create_index("ix_cli_lab_compartment_id", "cli_lab", ["compartment_id"], unique=False)
    op.create_index("ix_cli_lab_vendor_id", "cli_lab", ["vendor_id"], unique=False)
    op.create_index("ix_cli_lab_order_index", "cli_lab", ["order_index"], unique=False)

    op.create_table(
        "cli_lab_attempt",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("lab_id", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("command_log", json_type, nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["cli_lab.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cli_lab_attempt_student_id", "cli_lab_attempt", ["student_id"], unique=False)
    op.create_index("ix_cli_lab_attempt_lab_id", "cli_lab_attempt", ["lab_id"], unique=False)
    op.create_index("ix_cli_lab_attempt_completed_at", "cli_lab_attempt", ["completed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cli_lab_attempt_completed_at", table_name="cli_lab_attempt")
    op.drop_index("ix_cli_lab_attempt_lab_id", table_name="cli_lab_attempt")
    op.drop_index("ix_cli_lab_attempt_student_id", table_name="cli_lab_attempt")
    op.drop_table("cli_lab_attempt")
    op.drop_index("ix_cli_lab_order_index", table_name="cli_lab")
    op.drop_index("ix_cli_lab_vendor_id", table_name="cli_lab")
    op.drop_index("ix_cli_lab_compartment_id", table_name="cli_lab")
    op.drop_index("ix_cli_lab_id", table_name="cli_lab")
    op.drop_table("cli_lab")
