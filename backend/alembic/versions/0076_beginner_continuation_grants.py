"""Add durable beginner continuation grants without learner-data backfill.

Revision ID: 0076_beginner_continuation_grants
Revises: 0075_v2_learning_interactions
"""

from alembic import op
import sqlalchemy as sa


revision = "0076_beginner_continuation_grants"
down_revision = "0075_v2_learning_interactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_beginner_continuation_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("certification_module_id", sa.Integer(), sa.ForeignKey("certification_modules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("grant_reason", sa.String(32), nullable=False),
        sa.UniqueConstraint("student_id", "certification_module_id", name="uq_v2_beginner_continuation_student_module"),
    )
    op.create_index("ix_v2_beginner_continuation_grants_student_id", "v2_beginner_continuation_grants", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_v2_beginner_continuation_grants_student_id", table_name="v2_beginner_continuation_grants")
    op.drop_table("v2_beginner_continuation_grants")
