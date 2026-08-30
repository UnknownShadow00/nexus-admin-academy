"""Nexus V2 Phase 2A: per-student module activity (additive).

Revision ID: 0065_v2_module_activity
Revises: 0064_v2_ai_grading_infrastructure
Create Date: 2026-08-29

ADDITIVE ONLY. Creates one new table, ``v2_module_activity``, and touches
nothing else — no legacy progression table, no training_weeks, no XP ledger,
no 40% A+ gate, no students schema change. This table is a development-flow
progress record for the first end-to-end V2 module; nothing authoritative
reads it. ``downgrade`` drops the table.
"""

from alembic import op
import sqlalchemy as sa

revision = "0065_v2_module_activity"
down_revision = "0064_v2_ai_grading_infrastructure"
branch_labels = None
depends_on = None

_JSON = sa.JSON()
_NOW = sa.text("CURRENT_TIMESTAMP")

_ACTIVITY_TYPE_SQL = (
    "activity_type IN "
    "('lesson','resource','quick_check','module_quiz','practical','service_desk','explain')"
)


def upgrade() -> None:
    op.create_table(
        "v2_module_activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("module_key", sa.String(length=160), nullable=False),
        sa.Column("activity_type", sa.String(length=24), nullable=False),
        sa.Column("ref_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("detail", _JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "activity_type", "ref_key", name="uq_v2_module_activity"
        ),
        sa.CheckConstraint(_ACTIVITY_TYPE_SQL, name="ck_v2_module_activity_type"),
    )
    op.create_index("ix_v2_module_activity_id", "v2_module_activity", ["id"])
    op.create_index("ix_v2_module_activity_student_id", "v2_module_activity", ["student_id"])
    op.create_index("ix_v2_module_activity_module_key", "v2_module_activity", ["module_key"])
    op.create_index("ix_v2_module_activity_activity_type", "v2_module_activity", ["activity_type"])
    op.create_index("ix_v2_module_activity_ref_key", "v2_module_activity", ["ref_key"])


def downgrade() -> None:
    op.drop_table("v2_module_activity")
