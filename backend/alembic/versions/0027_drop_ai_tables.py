"""drop ai_usage_logs and ai_rate_limits tables

Revision ID: 0027_drop_ai_tables
Revises: c7d8e9f0a1b2
Create Date: 2026-07-13 00:00:00.000000
"""

from alembic import op

revision = "0027_drop_ai_tables"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_rate_limits_user_endpoint", table_name="ai_rate_limits", if_exists=True)
    op.drop_table("ai_rate_limits")
    op.drop_index("idx_ai_usage_created", table_name="ai_usage_logs", if_exists=True)
    op.drop_index("idx_ai_usage_feature", table_name="ai_usage_logs", if_exists=True)
    op.drop_table("ai_usage_logs")


def downgrade() -> None:
    import sqlalchemy as sa

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("feature", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("total_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("cost_estimate", sa.Numeric(10, 6), nullable=False, default=0),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_usage_feature", "ai_usage_logs", ["feature"])
    op.create_index("idx_ai_usage_created", "ai_usage_logs", ["created_at"])

    op.create_table(
        "ai_rate_limits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, default=0),
        sa.Column("endpoint", sa.String(100), nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False, default=1),
        sa.Column("window_start", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rate_limits_user_endpoint", "ai_rate_limits", ["user_id", "endpoint", "window_start"])
