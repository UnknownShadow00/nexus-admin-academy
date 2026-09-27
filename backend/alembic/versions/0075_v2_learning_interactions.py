"""Add versioned native V2 interactions and immutable attempts.

Revision ID: 0075_v2_learning_interactions
Revises: 0074_v2_learning_evidence
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0075_v2_learning_interactions"
down_revision = "0074_v2_learning_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_interaction_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interaction_key", sa.String(160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("interaction_type", sa.String(32), nullable=False),
        sa.Column("module_id", sa.Integer(), sa.ForeignKey("certification_modules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lesson_v2_meta.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("config", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pass_percent", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("interaction_key", "version", name="uq_v2_interaction_version"),
        sa.CheckConstraint("version > 0", name="ck_v2_interaction_version_positive"),
        sa.CheckConstraint("pass_percent BETWEEN 1 AND 100", name="ck_v2_interaction_pass_percent"),
        sa.CheckConstraint("interaction_type IN ('matching','image_identification','ordering','command_output','typed_answer','safe_action')", name="ck_v2_interaction_type"),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_v2_interaction_status"),
    )
    for column in ("interaction_key", "module_id", "lesson_id"):
        op.create_index(f"ix_v2_interaction_definitions_{column}", "v2_interaction_definitions", [column])
    op.create_table(
        "v2_interaction_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("definition_id", sa.Integer(), sa.ForeignKey("v2_interaction_definitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("interaction_key", sa.String(160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("definition_snapshot", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
        sa.Column("response_snapshot", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
        sa.Column("result_snapshot", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("student_id", "interaction_key", "attempt_number", name="uq_v2_interaction_attempt_number"),
        sa.CheckConstraint("attempt_number > 0", name="ck_v2_interaction_attempt_positive"),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_v2_interaction_score"),
    )
    for column in ("student_id", "definition_id", "interaction_key"):
        op.create_index(f"ix_v2_interaction_attempts_{column}", "v2_interaction_attempts", [column])
    op.create_table(
        "v2_interaction_requirement_changes",
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("v2_evidence_requirements.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created", sa.Boolean(), nullable=False),
        sa.Column("previous_is_required", sa.Boolean(), nullable=True),
        sa.Column("previous_active", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    # Restore 0074 requirements that the loader reused; remove only rows it
    # created. Drop evidence sourced from attempts that this rollback discards.
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM v2_evidence_records
        WHERE requirement_id IN (
            SELECT requirement_id FROM v2_interaction_requirement_changes WHERE created IS TRUE
        ) OR (
            requirement_id IN (
                SELECT requirement_id FROM v2_interaction_requirement_changes WHERE created IS FALSE
            ) AND source_ref LIKE 'v2-interaction-attempt:%'
        )
    """))
    connection.execute(sa.text("""
        UPDATE v2_evidence_requirements
        SET is_required = (
            SELECT previous_is_required FROM v2_interaction_requirement_changes
            WHERE requirement_id = v2_evidence_requirements.id
        ), active = (
            SELECT previous_active FROM v2_interaction_requirement_changes
            WHERE requirement_id = v2_evidence_requirements.id
        )
        WHERE id IN (
            SELECT requirement_id FROM v2_interaction_requirement_changes WHERE created IS FALSE
        )
    """))
    connection.execute(sa.text("""
        DELETE FROM v2_evidence_requirements
        WHERE id IN (
            SELECT requirement_id FROM v2_interaction_requirement_changes WHERE created IS TRUE
        )
    """))
    op.drop_table("v2_interaction_requirement_changes")
    op.drop_table("v2_interaction_attempts")
    op.drop_table("v2_interaction_definitions")
