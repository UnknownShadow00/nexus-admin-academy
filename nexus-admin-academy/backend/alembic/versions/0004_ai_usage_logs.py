"""add ai usage logs

Revision ID: 0004_ai_usage_logs
Revises: 0003_add_quiz_attempt_score_columns
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_ai_usage_logs"
down_revision = "0003_add_quiz_attempt_score_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_estimate", sa.DECIMAL(10, 6), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_ai_usage_feature", "ai_usage_logs", ["feature"])
    op.create_index("idx_ai_usage_created", "ai_usage_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_ai_usage_created", table_name="ai_usage_logs")
    op.drop_index("idx_ai_usage_feature", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
