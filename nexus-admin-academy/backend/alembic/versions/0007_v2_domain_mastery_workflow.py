"""v2 domain mastery and verification workflow

Revision ID: 0007_v2_domain_mastery_workflow
Revises: 0006_feature_enhancement
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_v2_domain_mastery_workflow"
down_revision = "0006_feature_enhancement"
branch_labels = None
depends_on = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    quiz_cols = _get_columns("quizzes")
    if "domain_id" not in quiz_cols:
        op.add_column("quizzes", sa.Column("domain_id", sa.String(length=10), nullable=True))
        op.execute("UPDATE quizzes SET domain_id = '1.0' WHERE domain_id IS NULL")

    ticket_cols = _get_columns("tickets")
    if "domain_id" not in ticket_cols:
        op.add_column("tickets", sa.Column("domain_id", sa.String(length=10), nullable=True))
        op.execute("UPDATE tickets SET domain_id = '1.0' WHERE domain_id IS NULL")

    student_cols = _get_columns("students")
    if "last_active_at" not in student_cols:
        op.add_column("students", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))

    sub_cols = _get_columns("ticket_submissions")
    if "structure_score" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("structure_score", sa.Integer(), nullable=True))
    if "technical_score" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("technical_score", sa.Integer(), nullable=True))
    if "communication_score" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("communication_score", sa.Integer(), nullable=True))
    if "final_score" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("final_score", sa.Integer(), nullable=True))
    if "xp_granted" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("xp_granted", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "status" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("status", sa.String(length=20), nullable=True))
        op.execute("UPDATE ticket_submissions SET status = 'verified' WHERE ai_score IS NOT NULL")
        op.execute("UPDATE ticket_submissions SET status = 'pending' WHERE status IS NULL")
    if "verified_at" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    if "verified_by" not in sub_cols:
        op.add_column("ticket_submissions", sa.Column("verified_by", sa.Integer(), nullable=True))

    op.create_table(
        "student_domain_mastery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("domain_id", sa.String(length=10), nullable=False),
        sa.Column("quiz_score_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quiz_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ticket_score_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ticket_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mastery_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_mastery_student_domain", "student_domain_mastery", ["student_id", "domain_id"])

    op.create_table(
        "weekly_domain_leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_key", sa.String(length=20), nullable=False),
        sa.Column("domain_id", sa.String(length=10), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("xp_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("badge_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_weekly_leads_week_domain", "weekly_domain_leads", ["week_key", "domain_id"])

    op.create_table(
        "squad_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_squad_activity_created", "squad_activity", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_squad_activity_created", table_name="squad_activity")
    op.drop_table("squad_activity")
    op.drop_index("idx_weekly_leads_week_domain", table_name="weekly_domain_leads")
    op.drop_table("weekly_domain_leads")
    op.drop_index("idx_mastery_student_domain", table_name="student_domain_mastery")
    op.drop_table("student_domain_mastery")

    sub_cols = _get_columns("ticket_submissions")
    for col in ["verified_by", "verified_at", "status", "xp_granted", "final_score", "communication_score", "technical_score", "structure_score"]:
        if col in sub_cols:
            op.drop_column("ticket_submissions", col)

    student_cols = _get_columns("students")
    if "last_active_at" in student_cols:
        op.drop_column("students", "last_active_at")

    ticket_cols = _get_columns("tickets")
    if "domain_id" in ticket_cols:
        op.drop_column("tickets", "domain_id")

    quiz_cols = _get_columns("quizzes")
    if "domain_id" in quiz_cols:
        op.drop_column("quizzes", "domain_id")
