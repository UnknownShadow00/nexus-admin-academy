"""Add database-backed A+ hands-on unlock setting.

Revision ID: 0027
Revises: c8d9e0f1a2b3
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op


revision = "0027"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    app_settings = op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.bulk_insert(
        app_settings,
        [{"key": "a_plus_unlock_threshold_pct", "value": 40}],
    )


def downgrade() -> None:
    op.drop_table("app_settings")
