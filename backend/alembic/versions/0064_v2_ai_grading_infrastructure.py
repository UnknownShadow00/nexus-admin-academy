"""Nexus V2 Phase 1C: AI grading infrastructure (additive).

Revision ID: 0064_v2_ai_grading_infrastructure
Revises: 0063_v2_content_and_assessment
Create Date: 2026-08-29

ADDITIVE ONLY. Creates three new tables and touches nothing else — no legacy
grading/progress table, no training_weeks, no 40% A+ gate, no Service Desk, no
students schema. `downgrade` drops the three tables.

* pending_grades         — durable per-submission grading job (mutable state)
* ai_grades              — append-only log of every AI grading attempt
* mentor_grade_overrides — append-only log of mentor overrides
"""

from alembic import op
import sqlalchemy as sa


revision = "0064_v2_ai_grading_infrastructure"
down_revision = "0063_v2_content_and_assessment"
branch_labels = None
depends_on = None

_JSON = sa.JSON()
_NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "pending_grades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_key", sa.String(length=200), nullable=True),
        sa.Column("submission_ref", sa.String(length=200), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("submitted_answer", sa.Text(), nullable=False),
        sa.Column("rubric_json", _JSON, nullable=True),
        sa.Column("rubric_version", sa.String(length=40), nullable=True),
        sa.Column("expected_concepts_json", _JSON, nullable=True),
        sa.Column("deterministic_result_json", _JSON, nullable=True),
        sa.Column("pass_threshold", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=40), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("resolved_grade_source", sa.String(length=20), nullable=True),
        sa.Column("resolved_score", sa.Float(), nullable=True),
        sa.Column("resolved_passed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "submission_ref", name="uq_pending_grades_submission"),
    )
    op.create_index("ix_pending_grades_id", "pending_grades", ["id"])
    op.create_index("ix_pending_grades_student_id", "pending_grades", ["student_id"])
    op.create_index("ix_pending_grades_source_type", "pending_grades", ["source_type"])
    op.create_index("ix_pending_grades_status", "pending_grades", ["status"])
    op.create_index("ix_pending_grades_next_retry_at", "pending_grades", ["next_retry_at"])

    op.create_table(
        "ai_grades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pending_grade_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("endpoint_label", sa.String(length=120), nullable=True),
        sa.Column("rubric_version", sa.String(length=40), nullable=True),
        sa.Column("prompt_version", sa.String(length=40), nullable=True),
        sa.Column("schema_version", sa.String(length=40), nullable=True),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("matched_concepts_json", _JSON, nullable=True),
        sa.Column("missing_concepts_json", _JSON, nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("review_recommended", sa.Boolean(), nullable=True),
        sa.Column("raw_response_json", _JSON, nullable=True),
        sa.Column("error_category", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW),
        sa.ForeignKeyConstraint(["pending_grade_id"], ["pending_grades.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_grades_id", "ai_grades", ["id"])
    op.create_index("ix_ai_grades_pending_grade_id", "ai_grades", ["pending_grade_id"])
    op.create_index("ix_ai_grades_outcome", "ai_grades", ["outcome"])

    op.create_table(
        "mentor_grade_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pending_grade_id", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.Integer(), nullable=True),
        sa.Column("mentor_label", sa.String(length=120), nullable=False, server_default="mentor"),
        sa.Column("override_score", sa.Float(), nullable=True),
        sa.Column("override_passed", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW),
        sa.ForeignKeyConstraint(["pending_grade_id"], ["pending_grades.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_id"], ["mentor_grade_overrides.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mentor_grade_overrides_id", "mentor_grade_overrides", ["id"])
    op.create_index(
        "ix_mentor_grade_overrides_pending_grade_id", "mentor_grade_overrides", ["pending_grade_id"]
    )


def downgrade() -> None:
    op.drop_table("mentor_grade_overrides")
    op.drop_table("ai_grades")
    op.drop_table("pending_grades")
