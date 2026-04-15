"""competency engine foundation

Revision ID: 0008_competency_engine_foundation
Revises: 0007_v2_domain_mastery_workflow
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_competency_engine_foundation"
down_revision = "0007_v2_domain_mastery_workflow"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(table_name)}


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("modules"):
        op.create_table(
            "modules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False, unique=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("target_role", sa.String(50), nullable=True),
            sa.Column("difficulty_band", sa.Integer(), nullable=True),
            sa.Column("estimated_hours", sa.Integer(), nullable=True),
            sa.Column("prerequisite_module_id", sa.Integer(), sa.ForeignKey("modules.id", ondelete="SET NULL"), nullable=True),
            sa.Column("unlock_threshold", sa.Integer(), nullable=False, server_default="70"),
            sa.Column("module_order", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_modules_order", "modules", ["module_order"])

    if not _has_table("lessons"):
        op.create_table(
            "lessons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("module_id", sa.Integer(), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("lesson_order", sa.Integer(), nullable=False),
            sa.Column("outcomes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("estimated_minutes", sa.Integer(), nullable=True),
            sa.Column("required_notes_template", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("module_id", "lesson_order", name="uq_lessons_module_order"),
        )
        op.create_index("idx_lessons_module", "lessons", ["module_id"])

    for table in ("resources", "quizzes", "tickets"):
        cols = _columns(table)
        if "lesson_id" not in cols:
            op.add_column(table, sa.Column("lesson_id", sa.Integer(), nullable=True))
            op.create_index(f"idx_{table}_lesson", table, ["lesson_id"])

    resource_cols = _columns("resources")
    if "provider" not in resource_cols:
        op.add_column("resources", sa.Column("provider", sa.String(100), nullable=True))
    if "license_notes" not in resource_cols:
        op.add_column("resources", sa.Column("license_notes", sa.Text(), nullable=True))
    if "expected_minutes" not in resource_cols:
        op.add_column("resources", sa.Column("expected_minutes", sa.Integer(), nullable=True))

    ticket_cols = _columns("tickets")
    if "root_cause" not in ticket_cols:
        op.add_column("tickets", sa.Column("root_cause", sa.Text(), nullable=True))
    if "root_cause_type" not in ticket_cols:
        op.add_column("tickets", sa.Column("root_cause_type", sa.String(50), nullable=True))
    if "required_checkpoints" not in ticket_cols:
        op.add_column("tickets", sa.Column("required_checkpoints", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "required_evidence" not in ticket_cols:
        op.add_column("tickets", sa.Column("required_evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "scoring_anchors" not in ticket_cols:
        op.add_column("tickets", sa.Column("scoring_anchors", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "model_answer" not in ticket_cols:
        op.add_column("tickets", sa.Column("model_answer", sa.Text(), nullable=True))

    if not _has_table("evidence_artifacts"):
        op.create_table(
            "evidence_artifacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("submission_type", sa.String(20), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("artifact_type", sa.String(50), nullable=False),
            sa.Column("storage_key", sa.Text(), nullable=False),
            sa.Column("original_filename", sa.Text(), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), nullable=True),
            sa.Column("mime_type", sa.String(100), nullable=True),
            sa.Column("checksum", sa.String(64), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("validation_status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("validation_notes", sa.Text(), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("validated_by", sa.Integer(), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("idx_artifacts_submission", "evidence_artifacts", ["submission_type", "submission_id"])
        op.create_index("idx_artifacts_checksum", "evidence_artifacts", ["checksum"])

    sub_cols = _columns("ticket_submissions")
    if "screenshots" in sub_cols:
        op.drop_column("ticket_submissions", "screenshots")
    if "evidence_complete" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("evidence_complete", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "before_screenshot_id" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("before_screenshot_id", sa.Integer(), nullable=True))
    if "after_screenshot_id" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("after_screenshot_id", sa.Integer(), nullable=True))
    if "methodology_steps_mentioned" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("methodology_steps_mentioned", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "methodology_score" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("methodology_score", sa.Integer(), nullable=True))

    if not _has_table("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("rank_order", sa.Integer(), nullable=False, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    student_cols = _columns("students")
    if "current_role_id" not in student_cols:
        op.add_column("students", sa.Column("current_role_id", sa.Integer(), nullable=True))
    if "role_since" not in student_cols:
        op.add_column("students", sa.Column("role_since", sa.DateTime(timezone=True), nullable=True))

    if not _has_table("promotion_gates"):
        op.create_table(
            "promotion_gates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("requirement_type", sa.String(50), nullable=False),
            sa.Column("requirement_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
        )
        op.create_index("idx_promotion_role", "promotion_gates", ["role_id"])

    if not _has_table("student_roles"):
        op.create_table(
            "student_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("promoted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("promoted_by", sa.Integer(), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
            sa.Column("promotion_notes", sa.Text(), nullable=True),
        )
        op.create_index("idx_student_roles_student", "student_roles", ["student_id"])

    if not _has_table("methodology_frameworks"):
        op.create_table(
            "methodology_frameworks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("steps", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("required_for_role", sa.Integer(), sa.ForeignKey("roles.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _has_table("student_methodology_progress"):
        op.create_table(
            "student_methodology_progress",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("framework_id", sa.Integer(), sa.ForeignKey("methodology_frameworks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("quiz_score", sa.Integer(), nullable=True),
            sa.Column("practice_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("student_id", "framework_id", name="uq_student_framework"),
        )
        op.create_index("idx_methodology_progress_student", "student_methodology_progress", ["student_id"])

    if not _has_table("lab_templates"):
        op.create_table(
            "lab_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("lab_type", sa.String(50), nullable=True),
            sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("estimated_minutes", sa.Integer(), nullable=True),
            sa.Column("environment_requirements", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("setup_instructions", sa.Text(), nullable=True),
            sa.Column("break_script", sa.Text(), nullable=True),
            sa.Column("success_criteria", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("required_evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("hints", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("model_solution", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_lab_templates_difficulty"),
        )
        op.create_index("idx_lab_templates_lesson", "lab_templates", ["lesson_id"])

    if not _has_table("lab_runs"):
        op.create_table(
            "lab_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lab_template_id", sa.Integer(), sa.ForeignKey("lab_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="assigned"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("time_spent_minutes", sa.Integer(), nullable=True),
            sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("final_score", sa.Integer(), nullable=True),
            sa.Column("xp_awarded", sa.Integer(), nullable=True),
            sa.Column("feedback", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_lab_runs_student", "lab_runs", ["student_id"])

    if not _has_table("root_causes"):
        op.create_table(
            "root_causes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("service_area", sa.String(100), nullable=True),
            sa.Column("cause_type", sa.String(100), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("break_method", sa.Text(), nullable=True),
            sa.Column("fix_method", sa.Text(), nullable=True),
            sa.Column("validation_steps", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _has_table("incidents"):
        op.create_table(
            "incidents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("incident_type", sa.String(50), nullable=True),
            sa.Column("impacted_services", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("root_cause_id", sa.Integer(), sa.ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rca_required", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("severity", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.CheckConstraint("severity BETWEEN 1 AND 5", name="ck_incidents_severity"),
        )

    if not _has_table("incident_tickets"):
        op.create_table(
            "incident_tickets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("symptom_role", sa.String(50), nullable=True),
            sa.Column("dependency_order", sa.Integer(), nullable=True),
            sa.UniqueConstraint("incident_id", "ticket_id", name="uq_incident_ticket"),
        )

    if not _has_table("incident_participants"):
        op.create_table(
            "incident_participants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(50), nullable=True),
            sa.Column("performance_score", sa.Integer(), nullable=True),
            sa.Column("feedback", sa.Text(), nullable=True),
        )

    if not _has_table("rca_submissions"):
        op.create_table(
            "rca_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("timeline", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("root_cause_analysis", sa.Text(), nullable=True),
            sa.Column("resolution_steps", sa.Text(), nullable=True),
            sa.Column("prevention_recommendations", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("xp_awarded", sa.Integer(), nullable=True),
        )

    if not _has_table("capstone_templates"):
        op.create_table(
            "capstone_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("role_level", sa.Integer(), sa.ForeignKey("roles.id", ondelete="SET NULL"), nullable=True),
            sa.Column("requirements", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("deliverables", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("estimated_hours", sa.Integer(), nullable=True),
            sa.Column("rubric", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _has_table("capstone_runs"):
        op.create_table(
            "capstone_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("capstone_template_id", sa.Integer(), sa.ForeignKey("capstone_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="assigned"),
            sa.Column("github_repo_url", sa.Text(), nullable=True),
            sa.Column("demo_video_url", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("technical_score", sa.Integer(), nullable=True),
            sa.Column("documentation_score", sa.Integer(), nullable=True),
            sa.Column("presentation_score", sa.Integer(), nullable=True),
            sa.Column("final_score", sa.Integer(), nullable=True),
            sa.Column("xp_awarded", sa.Integer(), nullable=True),
            sa.Column("pass", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    sub_cols = _columns("ticket_submissions")
    for col in [
        "methodology_score",
        "methodology_steps_mentioned",
        "after_screenshot_id",
        "before_screenshot_id",
        "evidence_complete",
    ]:
        if col in sub_cols:
            op.drop_column("ticket_submissions", col)
    if "screenshots" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("screenshots", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    ticket_cols = _columns("tickets")
    for col in [
        "model_answer",
        "scoring_anchors",
        "required_evidence",
        "required_checkpoints",
        "root_cause_type",
        "root_cause",
        "lesson_id",
    ]:
        if col in ticket_cols:
            op.drop_column("tickets", col)

    quiz_cols = _columns("quizzes")
    if "lesson_id" in quiz_cols:
        op.drop_column("quizzes", "lesson_id")

    resource_cols = _columns("resources")
    for col in ["expected_minutes", "license_notes", "provider", "lesson_id"]:
        if col in resource_cols:
            op.drop_column("resources", col)

    student_cols = _columns("students")
    for col in ["role_since", "current_role_id"]:
        if col in student_cols:
            op.drop_column("students", col)

    for idx_name, table in [
        ("idx_resources_lesson", "resources"),
        ("idx_quizzes_lesson", "quizzes"),
        ("idx_tickets_lesson", "tickets"),
        ("idx_modules_order", "modules"),
        ("idx_lessons_module", "lessons"),
        ("idx_artifacts_submission", "evidence_artifacts"),
        ("idx_artifacts_checksum", "evidence_artifacts"),
        ("idx_promotion_role", "promotion_gates"),
        ("idx_student_roles_student", "student_roles"),
        ("idx_methodology_progress_student", "student_methodology_progress"),
        ("idx_lab_templates_lesson", "lab_templates"),
        ("idx_lab_runs_student", "lab_runs"),
    ]:
        if _has_table(table):
            try:
                op.drop_index(idx_name, table_name=table)
            except Exception:
                pass

    for table in [
        "capstone_runs",
        "capstone_templates",
        "rca_submissions",
        "incident_participants",
        "incident_tickets",
        "incidents",
        "root_causes",
        "lab_runs",
        "lab_templates",
        "student_methodology_progress",
        "methodology_frameworks",
        "student_roles",
        "promotion_gates",
        "roles",
        "evidence_artifacts",
        "lessons",
        "modules",
    ]:
        if _has_table(table):
            op.drop_table(table)
