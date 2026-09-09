"""Durable server-owned legacy assessment presentations.

Revision ID: 0069_legacy_assessment_attempts
Revises: 0068_v2_runtime_stabilization
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa


revision = "0069_legacy_assessment_attempts"
down_revision = "0068_v2_runtime_stabilization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch:
        batch.add_column(
            sa.Column(
                "status",
                sa.String(length=24),
                server_default="submitted",
                nullable=False,
            )
        )
        batch.add_column(sa.Column("question_snapshot", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column(
                "current_position", sa.Integer(), server_default="0", nullable=False
            )
        )
        batch.add_column(
            sa.Column("revision", sa.Integer(), server_default="0", nullable=False)
        )
        batch.add_column(
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_index("ix_quiz_attempts_status", ["status"])


def downgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch:
        batch.drop_index("ix_quiz_attempts_status")
        batch.drop_column("submitted_at")
        batch.drop_column("current_position")
        batch.drop_column("revision")
        batch.drop_column("question_snapshot")
        batch.drop_column("status")
