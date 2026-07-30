"""Add private-beta Service Desk Lab browser MVP records.

Revision ID: 0035_service_desk_browser_mvp
Revises: 0034_service_desk_scenario_foundation
"""

import sqlalchemy as sa
from alembic import op


revision = "0035_service_desk_browser_mvp"
down_revision = "0034_service_desk_scenario_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This adds a future curriculum capability only; no live week receives one.
    with op.batch_alter_table("training_week_activities") as batch:
        batch.drop_constraint("ck_training_activities_type", type_="check")
        batch.create_check_constraint("ck_training_activities_type", "activity_type IN ('video','quiz','lesson','guided_lab','networking_lab','support_ticket','command_exercise','terminal_exercise','review','capstone','service_desk_scenario')")
    op.create_table(
        "service_desk_beta_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enrolled_by", sa.String(length=120), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.Column("removed_by", sa.String(length=120)),
        sa.Column("note", sa.String(length=500)),
        sa.UniqueConstraint("student_id", name="uq_service_desk_beta_enrollment_student"),
    )
    op.create_index("ix_service_desk_beta_enrollments_student_id", "service_desk_beta_enrollments", ["student_id"])
    op.create_table(
        "service_desk_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("service_desk_scenarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="learning"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("maximum_attempts", sa.Integer()),
        sa.Column("assigned_by", sa.String(length=120), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("mode IN ('learning','simulation')", name="ck_service_desk_assignments_mode"),
        sa.UniqueConstraint("student_id", "scenario_id", "mode", name="uq_service_desk_assignment_student_scenario_mode"),
    )
    op.create_index("ix_service_desk_assignments_student_id", "service_desk_assignments", ["student_id"])
    op.create_index("ix_service_desk_assignments_scenario_id", "service_desk_assignments", ["scenario_id"])
    op.create_table(
        "service_desk_knowledge_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stable_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("skill_tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("stable_id", name="uq_service_desk_knowledge_article_stable_id"),
    )
    op.create_index("ix_service_desk_knowledge_articles_stable_id", "service_desk_knowledge_articles", ["stable_id"])
    op.create_index("ix_service_desk_knowledge_articles_status", "service_desk_knowledge_articles", ["status"])
    op.create_table(
        "service_desk_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_service_desk_audit_logs_action", "service_desk_audit_logs", ["action"])
    op.create_index("ix_service_desk_audit_logs_created_at", "service_desk_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("service_desk_audit_logs")
    op.drop_table("service_desk_knowledge_articles")
    op.drop_table("service_desk_assignments")
    op.drop_table("service_desk_beta_enrollments")
    with op.batch_alter_table("training_week_activities") as batch:
        batch.drop_constraint("ck_training_activities_type", type_="check")
        batch.create_check_constraint("ck_training_activities_type", "activity_type IN ('video','quiz','lesson','guided_lab','networking_lab','support_ticket','command_exercise','terminal_exercise','review','capstone')")
