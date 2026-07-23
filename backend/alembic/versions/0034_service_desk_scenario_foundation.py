"""Add the disabled-by-default Service Desk scenario foundation.

Revision ID: 0034_service_desk_scenario_foundation
Revises: 0033_finalize_training_quiz_mappings
Create Date: 2026-07-23
"""

import sqlalchemy as sa
from alembic import op


revision = "0034_service_desk_scenario_foundation"
down_revision = "0033_finalize_training_quiz_mappings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_desk_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stable_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False, server_default="service_desk"),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("stable_key", name="uq_service_desk_scenarios_stable_key"),
        sa.CheckConstraint("status IN ('active','disabled')", name="ck_service_desk_scenarios_status"),
    )
    op.create_index("ix_service_desk_scenarios_stable_key", "service_desk_scenarios", ["stable_key"])
    op.create_index("ix_service_desk_scenarios_status", "service_desk_scenarios", ["status"])

    op.create_table(
        "service_desk_scenario_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("definition_json", sa.JSON(), nullable=False),
        sa.Column("definition_hash", sa.String(length=64), nullable=False),
        sa.Column("validation_status", sa.String(length=20), nullable=False, server_default="valid"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["service_desk_scenarios.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("scenario_id", "version_number", name="uq_service_desk_scenario_version_number"),
        sa.UniqueConstraint("scenario_id", "definition_hash", name="uq_service_desk_scenario_definition_hash"),
        sa.CheckConstraint("status IN ('draft','published','disabled')", name="ck_service_desk_versions_status"),
    )
    op.create_index("ix_service_desk_versions_scenario_id", "service_desk_scenario_versions", ["scenario_id"])
    op.create_index("ix_service_desk_versions_definition_hash", "service_desk_scenario_versions", ["definition_hash"])
    op.create_index("ix_service_desk_versions_status", "service_desk_scenario_versions", ["status"])

    op.create_table(
        "service_desk_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("scenario_version_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("current_state", sa.JSON(), nullable=False),
        sa.Column("current_state_hash", sa.String(length=64), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("admin_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_reset_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scenario_version_id"], ["service_desk_scenario_versions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("student_id", "scenario_version_id", "attempt_number", name="uq_service_desk_attempt_number"),
        sa.CheckConstraint("mode IN ('learning','simulation')", name="ck_service_desk_attempts_mode"),
        sa.CheckConstraint("status IN ('in_progress','completed','failed')", name="ck_service_desk_attempts_status"),
    )
    op.create_index("ix_service_desk_attempts_student_id", "service_desk_attempts", ["student_id"])
    op.create_index("ix_service_desk_attempts_scenario_version_id", "service_desk_attempts", ["scenario_version_id"])
    op.create_index("ix_service_desk_attempts_status", "service_desk_attempts", ["status"])

    op.create_table(
        "service_desk_attempt_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("tool", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_state_hash", sa.String(length=64), nullable=False),
        sa.Column("resulting_state_hash", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["service_desk_attempts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id", "sequence_number", name="uq_service_desk_event_sequence"),
        sa.UniqueConstraint("attempt_id", "idempotency_key", name="uq_service_desk_event_idempotency"),
    )
    op.create_index("ix_service_desk_events_attempt_id", "service_desk_attempt_events", ["attempt_id"])
    op.create_index("ix_service_desk_events_event_type", "service_desk_attempt_events", ["event_type"])
    op.create_index("ix_service_desk_events_created_at", "service_desk_attempt_events", ["created_at"])

    op.create_table(
        "service_desk_attempt_grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("scenario_version_id", sa.Integer(), nullable=False),
        sa.Column("rubric_version", sa.String(length=40), nullable=False),
        sa.Column("technical_complete", sa.Boolean(), nullable=False),
        sa.Column("critical_failure", sa.Boolean(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("feedback_summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["service_desk_attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scenario_version_id"], ["service_desk_scenario_versions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("attempt_id", name="uq_service_desk_grade_attempt"),
    )
    op.create_index("ix_service_desk_grades_attempt_id", "service_desk_attempt_grades", ["attempt_id"])
    op.create_index("ix_service_desk_grades_scenario_version_id", "service_desk_attempt_grades", ["scenario_version_id"])


def downgrade() -> None:
    op.drop_table("service_desk_attempt_grades")
    op.drop_table("service_desk_attempt_events")
    op.drop_table("service_desk_attempts")
    op.drop_table("service_desk_scenario_versions")
    op.drop_table("service_desk_scenarios")
