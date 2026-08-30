"""Nexus V2 additive foundation: certification hierarchy + lesson/question mapping.

Revision ID: 0062_v2_certification_foundation
Revises: 0061_integrated_support_prove
Create Date: 2026-08-29

Phase 1A — ADDITIVE ONLY. This migration:

* creates the V2 certification hierarchy tables (certifications,
  certification_versions, certification_domains, certification_modules,
  certification_objectives) plus the lesson<->objective and lesson<->lesson
  join tables;
* adds nullable V2 mapping/provenance columns to the existing ``lessons`` and
  ``questions`` tables.

It does NOT touch ``training_weeks``, ``training_week_activities``, any
progression table, the 40% A+ unlock setting, or any student record. Every
new column is nullable or defaulted, so current behaviour is unchanged and V1
and V2 data coexist. ``downgrade`` fully reverses it.
"""

from alembic import op
import sqlalchemy as sa


revision = "0062_v2_certification_foundation"
down_revision = "0061_integrated_support_prove"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "certifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cert_key", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cert_key", name="uq_certifications_cert_key"),
    )
    op.create_index(op.f("ix_certifications_id"), "certifications", ["id"], unique=False)
    op.create_index(op.f("ix_certifications_cert_key"), "certifications", ["cert_key"], unique=False)

    op.create_table(
        "certification_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certification_id", sa.Integer(), nullable=False),
        sa.Column("version_key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("exam_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("effective_date", sa.String(length=40), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["certification_id"], ["certifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_key", name="uq_certification_versions_version_key"),
        sa.UniqueConstraint(
            "certification_id", "version_key", name="uq_certification_versions_cert_version"
        ),
    )
    op.create_index(op.f("ix_certification_versions_id"), "certification_versions", ["id"], unique=False)
    op.create_index(
        op.f("ix_certification_versions_certification_id"),
        "certification_versions",
        ["certification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_versions_version_key"),
        "certification_versions",
        ["version_key"],
        unique=False,
    )

    op.create_table(
        "certification_domains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certification_version_id", sa.Integer(), nullable=False),
        sa.Column("domain_key", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("weight_percent", sa.Integer(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "certification_version_id", "domain_key", name="uq_certification_domains_version_key"
        ),
    )
    op.create_index(op.f("ix_certification_domains_id"), "certification_domains", ["id"], unique=False)
    op.create_index(
        op.f("ix_certification_domains_certification_version_id"),
        "certification_domains",
        ["certification_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_domains_domain_key"),
        "certification_domains",
        ["domain_key"],
        unique=False,
    )

    op.create_table(
        "certification_modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certification_version_id", sa.Integer(), nullable=False),
        sa.Column("certification_domain_id", sa.Integer(), nullable=True),
        sa.Column("module_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("skill_promise", sa.Text(), nullable=True),
        sa.Column("importance_hint", sa.String(length=20), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("legacy_training_week_id", sa.Integer(), nullable=True),
        sa.Column("legacy_module_code", sa.String(length=20), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["certification_domain_id"], ["certification_domains.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["legacy_training_week_id"], ["training_weeks.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_key", name="uq_certification_modules_module_key"),
    )
    op.create_index(op.f("ix_certification_modules_id"), "certification_modules", ["id"], unique=False)
    op.create_index(
        op.f("ix_certification_modules_certification_version_id"),
        "certification_modules",
        ["certification_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_modules_certification_domain_id"),
        "certification_modules",
        ["certification_domain_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_modules_module_key"),
        "certification_modules",
        ["module_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_modules_legacy_training_week_id"),
        "certification_modules",
        ["legacy_training_week_id"],
        unique=False,
    )

    op.create_table(
        "certification_objectives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("certification_version_id", sa.Integer(), nullable=False),
        sa.Column("domain_key", sa.String(length=40), nullable=True),
        sa.Column("objective_code", sa.String(length=40), nullable=False),
        sa.Column("objective_text", sa.Text(), nullable=False),
        sa.Column("subtopics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "certification_version_id",
            "objective_code",
            name="uq_certification_objectives_version_code",
        ),
    )
    op.create_index(
        op.f("ix_certification_objectives_id"), "certification_objectives", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_certification_objectives_certification_version_id"),
        "certification_objectives",
        ["certification_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_objectives_domain_key"),
        "certification_objectives",
        ["domain_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certification_objectives_objective_code"),
        "certification_objectives",
        ["objective_code"],
        unique=False,
    )

    op.create_table(
        "lesson_objectives",
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["objective_id"], ["certification_objectives.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("lesson_id", "objective_id"),
    )

    op.create_table(
        "lesson_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_lesson_id", sa.Integer(), nullable=False),
        sa.Column("to_lesson_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["from_lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_lesson_id",
            "to_lesson_id",
            "relationship_type",
            name="uq_lesson_relationships_edge",
        ),
        sa.CheckConstraint(
            "from_lesson_id <> to_lesson_id", name="ck_lesson_relationships_no_self_edge"
        ),
        sa.CheckConstraint(
            "relationship_type IN ('builds_on','review_of')",
            name="ck_lesson_relationships_type",
        ),
    )
    op.create_index(op.f("ix_lesson_relationships_id"), "lesson_relationships", ["id"], unique=False)
    op.create_index(
        op.f("ix_lesson_relationships_from_lesson_id"),
        "lesson_relationships",
        ["from_lesson_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lesson_relationships_to_lesson_id"),
        "lesson_relationships",
        ["to_lesson_id"],
        unique=False,
    )

    op.create_table(
        "lesson_v2_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("lesson_key", sa.String(length=160), nullable=True),
        sa.Column("certification_version_id", sa.Integer(), nullable=True),
        sa.Column("certification_module_id", sa.Integer(), nullable=True),
        sa.Column("domain_key", sa.String(length=40), nullable=True),
        sa.Column("importance", sa.String(length=20), nullable=True),
        sa.Column("learning_relationship", sa.String(length=20), nullable=True),
        sa.Column("content_path", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["certification_module_id"], ["certification_modules.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", name="uq_lesson_v2_meta_lesson_id"),
        sa.UniqueConstraint("lesson_key", name="uq_lesson_v2_meta_lesson_key"),
    )
    op.create_index(op.f("ix_lesson_v2_meta_id"), "lesson_v2_meta", ["id"], unique=False)
    op.create_index(op.f("ix_lesson_v2_meta_lesson_id"), "lesson_v2_meta", ["lesson_id"], unique=False)
    op.create_index(
        op.f("ix_lesson_v2_meta_lesson_key"), "lesson_v2_meta", ["lesson_key"], unique=False
    )
    op.create_index(
        op.f("ix_lesson_v2_meta_certification_version_id"),
        "lesson_v2_meta",
        ["certification_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lesson_v2_meta_certification_module_id"),
        "lesson_v2_meta",
        ["certification_module_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lesson_v2_meta_domain_key"), "lesson_v2_meta", ["domain_key"], unique=False
    )

    op.create_table(
        "question_v2_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("certification", sa.String(length=60), nullable=True),
        sa.Column("certification_version", sa.String(length=80), nullable=True),
        sa.Column("certification_version_id", sa.Integer(), nullable=True),
        sa.Column("domain", sa.String(length=40), nullable=True),
        sa.Column("module", sa.String(length=120), nullable=True),
        sa.Column("objective_code", sa.String(length=40), nullable=True),
        sa.Column("importance", sa.String(length=20), nullable=True),
        sa.Column("source_name", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column(
            "permission_status",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", name="uq_question_v2_meta_question_id"),
    )
    op.create_index(op.f("ix_question_v2_meta_id"), "question_v2_meta", ["id"], unique=False)
    op.create_index(
        op.f("ix_question_v2_meta_question_id"), "question_v2_meta", ["question_id"], unique=False
    )
    op.create_index(
        op.f("ix_question_v2_meta_certification_version"),
        "question_v2_meta",
        ["certification_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_v2_meta_certification_version_id"),
        "question_v2_meta",
        ["certification_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_v2_meta_objective_code"),
        "question_v2_meta",
        ["objective_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_v2_meta_permission_status"),
        "question_v2_meta",
        ["permission_status"],
        unique=False,
    )


def downgrade():
    op.drop_table("question_v2_meta")
    op.drop_table("lesson_v2_meta")

    op.drop_table("lesson_relationships")
    op.drop_table("lesson_objectives")
    op.drop_table("certification_objectives")
    op.drop_table("certification_modules")
    op.drop_table("certification_domains")
    op.drop_table("certification_versions")
    op.drop_table("certifications")
