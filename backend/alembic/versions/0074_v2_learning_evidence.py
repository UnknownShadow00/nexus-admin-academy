"""Separate V2 viewing from trusted mastery evidence (additive only).

Revision ID: 0074_v2_learning_evidence
Revises: 0073_mfa_week7_curriculum_card
"""

from alembic import op
import sqlalchemy as sa


revision = "0074_v2_learning_evidence"
down_revision = "0073_mfa_week7_curriculum_card"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("v2_student_resource_activity") as batch:
        batch.add_column(sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "v2_evidence_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("module_id", sa.Integer(), sa.ForeignKey("certification_modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("ref_key", sa.String(200), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.UniqueConstraint("module_id", "evidence_type", "ref_key", name="uq_v2_evidence_requirement"),
        sa.CheckConstraint("evidence_type IN ('interaction','apply')", name="ck_v2_evidence_requirement_type"),
    )
    op.create_index("ix_v2_evidence_requirements_module_id", "v2_evidence_requirements", ["module_id"])
    op.create_table(
        "v2_evidence_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("v2_evidence_requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("satisfied_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("source_ref", sa.String(200), nullable=False),
        sa.UniqueConstraint("student_id", "requirement_id", name="uq_v2_evidence_record"),
    )
    op.create_index("ix_v2_evidence_records_student_id", "v2_evidence_records", ["student_id"])
    op.create_index("ix_v2_evidence_records_requirement_id", "v2_evidence_records", ["requirement_id"])


def downgrade() -> None:
    op.drop_table("v2_evidence_records")
    op.drop_table("v2_evidence_requirements")
    with op.batch_alter_table("v2_student_resource_activity") as batch:
        batch.drop_column("watched_at")
