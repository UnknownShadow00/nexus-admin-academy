"""Durable V2 assessment attempts and grading leases.

Revision ID: 0068_v2_runtime_stabilization
Revises: 0067_v2_question_objectives
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0068_v2_runtime_stabilization"
down_revision = "0067_v2_question_objectives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pending_grades") as batch:
        batch.add_column(sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("claim_token", sa.String(length=36), nullable=True))
        batch.create_index("ix_pending_grades_claimed_at", ["claimed_at"])
        batch.create_index("ix_pending_grades_claim_token", ["claim_token"])
    with op.batch_alter_table("ai_grades") as batch:
        batch.create_unique_constraint(
            "uq_ai_grade_attempt", ["pending_grade_id", "attempt_number"]
        )

    op.create_table(
        "v2_assessment_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("module_key", sa.String(length=160), nullable=False),
        sa.Column("assessment_key", sa.String(length=200), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="in_progress", nullable=False),
        sa.Column("grading_state", sa.String(length=24), server_default="unsubmitted", nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["module_assessments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "assessment_id", "attempt_number", name="uq_v2_assessment_attempt_number"),
    )
    for column in ("id", "student_id", "assessment_id", "module_key", "assessment_key", "status"):
        op.create_index(f"ix_v2_assessment_attempts_{column}", "v2_assessment_attempts", [column])

    op.create_table(
        "v2_assessment_attempt_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question_snapshot", sa.JSON(), nullable=False),
        sa.Column("submitted_answer", sa.Text(), nullable=True),
        sa.Column("grading_status", sa.String(length=24), server_default="unsubmitted", nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("pending_grade_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["v2_assessment_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pending_grade_id"], ["pending_grades.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "position", name="uq_v2_attempt_question_position"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_v2_attempt_question_id"),
        sa.UniqueConstraint("pending_grade_id"),
    )
    for column in ("id", "attempt_id", "question_id", "pending_grade_id"):
        op.create_index(f"ix_v2_assessment_attempt_questions_{column}", "v2_assessment_attempt_questions", [column])


def downgrade() -> None:
    op.drop_table("v2_assessment_attempt_questions")
    op.drop_table("v2_assessment_attempts")
    with op.batch_alter_table("ai_grades") as batch:
        batch.drop_constraint("uq_ai_grade_attempt", type_="unique")
    with op.batch_alter_table("pending_grades") as batch:
        batch.drop_index("ix_pending_grades_claim_token")
        batch.drop_index("ix_pending_grades_claimed_at")
        batch.drop_column("claim_token")
        batch.drop_column("claimed_at")
