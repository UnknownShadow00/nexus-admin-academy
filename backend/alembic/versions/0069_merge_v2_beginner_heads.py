"""Merge the V2 and beginner-rollout migration lineages.

Revision ID: 0069_merge_v2_beginner_heads
Revises: 0068_v2_runtime_stabilization, 0062_beginner_learning_rollout
Create Date: 2026-09-20

This is intentionally a merge-only revision. Both parent branches retain
their existing history and Alembic applies each branch before recording this
single reconciled head.
"""

revision = "0069_merge_v2_beginner_heads"
down_revision = (
    "0068_v2_runtime_stabilization",
    "0062_beginner_learning_rollout",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
