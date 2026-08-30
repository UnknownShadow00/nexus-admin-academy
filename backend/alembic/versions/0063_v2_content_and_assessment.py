"""Nexus V2 Phase 1B: content + assessment foundation (additive).

Revision ID: 0063_v2_content_and_assessment
Revises: 0062_v2_certification_foundation
Create Date: 2026-08-29

ADDITIVE ONLY. Does not touch training_weeks, progression, the 40% A+ gate,
students, Service Desk, or the legacy lessons/questions tables. This migration:

* reshapes the (empty, never-deployed) V2 tables lesson_v2_meta /
  lesson_objectives / lesson_relationships so a V2 lesson is a first-class
  Markdown-sourced record that need not have a legacy `lessons` row;
* adds free-form (short_answer / free_response) grading metadata columns to
  question_v2_meta (still a companion table — no columns on `questions`);
* adds resources / resource_links / student_resource_activity,
  module_assessments, and interview_prompts / interview_prompt_objectives.

The three reshaped V2 tables are dropped and recreated because they hold no
rows anywhere (no production V2 deploy has happened). `downgrade` restores the
exact 0062 shapes.
"""

from alembic import op
import sqlalchemy as sa


revision = "0063_v2_content_and_assessment"
down_revision = "0062_v2_certification_foundation"
branch_labels = None
depends_on = None


def _create_lesson_v2_meta_1b():
    op.create_table(
        "lesson_v2_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("lesson_key", sa.String(length=160), nullable=True),
        sa.Column("certification_version_id", sa.Integer(), nullable=True),
        sa.Column("certification_module_id", sa.Integer(), nullable=True),
        sa.Column("domain_key", sa.String(length=40), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("importance", sa.String(length=20), nullable=True),
        sa.Column("learning_relationship", sa.String(length=20), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("content_path", sa.String(length=300), nullable=True),
        sa.Column("content_body", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
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
    for col in ("id", "lesson_id", "lesson_key", "certification_version_id",
                "certification_module_id", "domain_key"):
        op.create_index(op.f(f"ix_lesson_v2_meta_{col}"), "lesson_v2_meta", [col], unique=False)


def _create_lesson_join_tables_1b():
    op.create_table(
        "lesson_objectives",
        sa.Column("lesson_v2_meta_id", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["lesson_v2_meta_id"], ["lesson_v2_meta.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["objective_id"], ["certification_objectives.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("lesson_v2_meta_id", "objective_id"),
    )
    op.create_table(
        "lesson_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_lesson_meta_id", sa.Integer(), nullable=False),
        sa.Column("to_lesson_meta_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["from_lesson_meta_id"], ["lesson_v2_meta.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_lesson_meta_id"], ["lesson_v2_meta.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_lesson_meta_id", "to_lesson_meta_id", "relationship_type",
            name="uq_lesson_relationships_edge",
        ),
        sa.CheckConstraint(
            "from_lesson_meta_id <> to_lesson_meta_id", name="ck_lesson_relationships_no_self_edge"
        ),
        sa.CheckConstraint(
            "relationship_type IN ('builds_on','review_of')", name="ck_lesson_relationships_type"
        ),
    )
    op.create_index(op.f("ix_lesson_relationships_id"), "lesson_relationships", ["id"], unique=False)
    op.create_index(
        op.f("ix_lesson_relationships_from_lesson_meta_id"),
        "lesson_relationships", ["from_lesson_meta_id"], unique=False,
    )
    op.create_index(
        op.f("ix_lesson_relationships_to_lesson_meta_id"),
        "lesson_relationships", ["to_lesson_meta_id"], unique=False,
    )


def upgrade():
    # --- 1. Free-form question grading metadata on the companion table ---
    with op.batch_alter_table("question_v2_meta", schema=None) as batch_op:
        batch_op.add_column(sa.Column("question_type", sa.String(length=20), nullable=True))
        batch_op.add_column(
            sa.Column("acceptable_answers", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("answer_match_mode", sa.String(length=20), nullable=False, server_default="normalized")
        )
        batch_op.add_column(
            sa.Column("expected_concepts", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("rubric", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("rubric_version", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("min_concepts_for_pass", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("partial_credit", sa.Boolean(), nullable=False, server_default="1")
        )
    op.create_index(
        op.f("ix_question_v2_meta_question_type"), "question_v2_meta", ["question_type"], unique=False
    )

    # --- 2. Reshape the empty V2 lesson tables ---
    op.drop_table("lesson_relationships")
    op.drop_table("lesson_objectives")
    op.drop_table("lesson_v2_meta")
    _create_lesson_v2_meta_1b()
    _create_lesson_join_tables_1b()

    # --- 3. Resources ---
    op.create_table(
        "v2_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=160), nullable=True),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("certification_version_id", sa.Integer(), nullable=True),
        sa.Column("duration", sa.String(length=20), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("permission_status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_key", name="uq_v2_resources_resource_key"),
        sa.CheckConstraint(
            "resource_type IN ('video','article','documentation','external_practice','reference')",
            name="ck_v2_resources_type",
        ),
    )
    for col in ("id", "resource_key", "resource_type", "certification_version_id", "permission_status"):
        op.create_index(op.f(f"ix_v2_resources_{col}"), "v2_resources", [col], unique=False)

    op.create_table(
        "v2_resource_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("lesson_v2_meta_id", sa.Integer(), nullable=True),
        sa.Column("certification_module_id", sa.Integer(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["resource_id"], ["v2_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_v2_meta_id"], ["lesson_v2_meta.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["certification_module_id"], ["certification_modules.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resource_id", "lesson_v2_meta_id", "certification_module_id",
            name="uq_v2_resource_links_target",
        ),
        sa.CheckConstraint(
            "lesson_v2_meta_id IS NOT NULL OR certification_module_id IS NOT NULL",
            name="ck_v2_resource_links_has_target",
        ),
    )
    for col in ("id", "resource_id", "lesson_v2_meta_id", "certification_module_id"):
        op.create_index(op.f(f"ix_v2_resource_links_{col}"), "v2_resource_links", [col], unique=False)

    op.create_table(
        "v2_student_resource_activity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_score", sa.Integer(), nullable=True),
        sa.Column("student_note", sa.Text(), nullable=True),
        sa.Column("confusing_topic", sa.Text(), nullable=True),
        sa.Column("question_for_mentor", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["v2_resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "resource_id", name="uq_v2_student_resource_activity"),
    )
    for col in ("id", "student_id", "resource_id"):
        op.create_index(
            op.f(f"ix_v2_student_resource_activity_{col}"), "v2_student_resource_activity", [col], unique=False
        )

    # --- 4. Module assessments (reference the existing engines) ---
    op.create_table(
        "module_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_key", sa.String(length=160), nullable=False),
        sa.Column("certification_module_id", sa.Integer(), nullable=False),
        sa.Column("lesson_v2_meta_id", sa.Integer(), nullable=True),
        sa.Column("assessment_role", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("quiz_id", sa.Integer(), nullable=True),
        sa.Column("lab_template_id", sa.Integer(), nullable=True),
        sa.Column("service_desk_scenario_id", sa.Integer(), nullable=True),
        sa.Column("displayed_count", sa.Integer(), nullable=True),
        sa.Column("pass_percent", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["certification_module_id"], ["certification_modules.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["lesson_v2_meta_id"], ["lesson_v2_meta.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lab_template_id"], ["lab_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["service_desk_scenario_id"], ["service_desk_scenarios.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_key", name="uq_module_assessments_key"),
        sa.CheckConstraint(
            "assessment_role IN ('quick_check','module_quiz','practical','service_desk','explain')",
            name="ck_module_assessments_role",
        ),
    )
    for col in ("id", "assessment_key", "certification_module_id", "lesson_v2_meta_id",
                "assessment_role", "quiz_id", "lab_template_id", "service_desk_scenario_id"):
        op.create_index(op.f(f"ix_module_assessments_{col}"), "module_assessments", [col], unique=False)

    # --- 5. Interview / Explain prompts ---
    op.create_table(
        "interview_prompts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prompt_key", sa.String(length=160), nullable=False),
        sa.Column("certification_version_id", sa.Integer(), nullable=True),
        sa.Column("certification_module_id", sa.Integer(), nullable=True),
        sa.Column("domain_key", sa.String(length=40), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("expected_concepts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("rubric", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("rubric_version", sa.String(length=40), nullable=True),
        sa.Column("importance", sa.String(length=20), nullable=True),
        sa.Column("model_answer_outline", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["certification_version_id"], ["certification_versions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["certification_module_id"], ["certification_modules.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_key", name="uq_interview_prompts_key"),
    )
    for col in ("id", "prompt_key", "certification_version_id", "certification_module_id", "domain_key"):
        op.create_index(op.f(f"ix_interview_prompts_{col}"), "interview_prompts", [col], unique=False)

    op.create_table(
        "interview_prompt_objectives",
        sa.Column("interview_prompt_id", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["interview_prompt_id"], ["interview_prompts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["objective_id"], ["certification_objectives.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("interview_prompt_id", "objective_id"),
    )


def _create_lesson_v2_meta_0062():
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
    for col in ("id", "lesson_id", "lesson_key", "certification_version_id",
                "certification_module_id", "domain_key"):
        op.create_index(op.f(f"ix_lesson_v2_meta_{col}"), "lesson_v2_meta", [col], unique=False)


def _create_lesson_join_tables_0062():
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
            "from_lesson_id", "to_lesson_id", "relationship_type", name="uq_lesson_relationships_edge"
        ),
        sa.CheckConstraint(
            "from_lesson_id <> to_lesson_id", name="ck_lesson_relationships_no_self_edge"
        ),
        sa.CheckConstraint(
            "relationship_type IN ('builds_on','review_of')", name="ck_lesson_relationships_type"
        ),
    )
    op.create_index(op.f("ix_lesson_relationships_id"), "lesson_relationships", ["id"], unique=False)
    op.create_index(
        op.f("ix_lesson_relationships_from_lesson_id"), "lesson_relationships", ["from_lesson_id"], unique=False
    )
    op.create_index(
        op.f("ix_lesson_relationships_to_lesson_id"), "lesson_relationships", ["to_lesson_id"], unique=False
    )


def downgrade():
    op.drop_table("interview_prompt_objectives")
    op.drop_table("interview_prompts")
    op.drop_table("module_assessments")
    op.drop_table("v2_student_resource_activity")
    op.drop_table("v2_resource_links")
    op.drop_table("v2_resources")

    op.drop_table("lesson_relationships")
    op.drop_table("lesson_objectives")
    op.drop_table("lesson_v2_meta")
    _create_lesson_v2_meta_0062()
    _create_lesson_join_tables_0062()

    op.drop_index(op.f("ix_question_v2_meta_question_type"), table_name="question_v2_meta")
    with op.batch_alter_table("question_v2_meta", schema=None) as batch_op:
        batch_op.drop_column("partial_credit")
        batch_op.drop_column("min_concepts_for_pass")
        batch_op.drop_column("rubric_version")
        batch_op.drop_column("rubric")
        batch_op.drop_column("expected_concepts")
        batch_op.drop_column("answer_match_mode")
        batch_op.drop_column("acceptable_answers")
        batch_op.drop_column("question_type")
