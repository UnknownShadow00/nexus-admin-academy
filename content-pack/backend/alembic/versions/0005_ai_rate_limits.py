"""add ai rate limits

Revision ID: 0005_ai_rate_limits
Revises: 0004_ai_usage_logs
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_ai_rate_limits"
down_revision = "0004_ai_usage_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_rate_limits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("endpoint", sa.String(length=100), nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("idx_rate_limits_user_endpoint", "ai_rate_limits", ["user_id", "endpoint", "window_start"])


def downgrade() -> None:
    op.drop_index("idx_rate_limits_user_endpoint", table_name="ai_rate_limits")
    op.drop_table("ai_rate_limits")
