"""Nexus V2 Phase 2B: durable Explain submissions (additive, development only).

Revision ID: 0066_v2_explain_submissions
Revises: 0065_v2_module_activity
Create Date: 2026-08-29

The original student response is committed here before deterministic/queued
grading runs. Grading results remain in the Phase 1C grading tables.
"""

from alembic import op
import sqlalchemy as sa

revision = "0066_v2_explain_submissions"
down_revision = "0065_v2_module_activity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_explain_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("submitted_answer", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["interview_prompts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "prompt_id", "attempt_number", name="uq_v2_explain_submission_attempt"),
    )
    op.create_index("ix_v2_explain_submissions_id", "v2_explain_submissions", ["id"])
    op.create_index("ix_v2_explain_submissions_student_id", "v2_explain_submissions", ["student_id"])
    op.create_index("ix_v2_explain_submissions_prompt_id", "v2_explain_submissions", ["prompt_id"])


def downgrade() -> None:
    op.drop_table("v2_explain_submissions")
