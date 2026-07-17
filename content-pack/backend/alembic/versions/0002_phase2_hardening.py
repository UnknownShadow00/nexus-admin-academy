"""phase2 hardening

Revision ID: 0002_phase2_hardening
Revises: 0001_init
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_phase2_hardening"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    op.create_table(
        "xp_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_students_xp", "students", ["total_xp"])
    op.create_index("idx_quizzes_week", "quizzes", ["week_number"])
    op.create_index("idx_tickets_week", "tickets", ["week_number"])
    op.create_index("idx_tickets_difficulty", "tickets", ["difficulty"])
    op.create_index("idx_quiz_attempts_student", "quiz_attempts", ["student_id"])
    op.create_index("idx_quiz_attempts_quiz", "quiz_attempts", ["quiz_id"])
    op.create_index("idx_ticket_submissions_student", "ticket_submissions", ["student_id"])
    op.create_index("idx_ticket_submissions_ticket", "ticket_submissions", ["ticket_id"])

    op.create_index("idx_xp_ledger_student", "xp_ledger", ["student_id"])
    op.create_index("idx_xp_ledger_created", "xp_ledger", ["created_at"])
    op.create_index("idx_resources_week", "resources", ["week_number"])
    op.create_index("idx_resources_category", "resources", ["category"])
    op.create_index("idx_resources_type", "resources", ["resource_type"])

    op.add_column("quiz_attempts", sa.Column("best_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("quiz_attempts", sa.Column("first_attempt_xp", sa.Integer(), nullable=False, server_default="0"))
    if dialect == "sqlite":
        op.create_index("uq_student_quiz", "quiz_attempts", ["student_id", "quiz_id"], unique=True)
    else:
        op.create_unique_constraint("uq_student_quiz", "quiz_attempts", ["student_id", "quiz_id"])

    op.add_column("ticket_submissions", sa.Column("screenshots", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("ticket_submissions", sa.Column("collaborator_ids", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("ticket_submissions", sa.Column("admin_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ticket_submissions", sa.Column("admin_comment", sa.Text(), nullable=True))
    op.add_column("ticket_submissions", sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True))
    if dialect == "sqlite":
        with op.batch_alter_table("ticket_submissions") as batch_op:
            batch_op.alter_column("ai_score", existing_type=sa.Integer(), nullable=True)
    else:
        op.alter_column("ticket_submissions", "ai_score", existing_type=sa.Integer(), nullable=True)

    op.create_index("idx_ticket_submissions_reviewed", "ticket_submissions", ["admin_reviewed"])


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.drop_index("idx_ticket_submissions_reviewed", table_name="ticket_submissions")
    op.drop_column("ticket_submissions", "graded_at")
    op.drop_column("ticket_submissions", "admin_comment")
    op.drop_column("ticket_submissions", "admin_reviewed")
    op.drop_column("ticket_submissions", "collaborator_ids")
    op.drop_column("ticket_submissions", "screenshots")
    if dialect == "sqlite":
        with op.batch_alter_table("ticket_submissions") as batch_op:
            batch_op.alter_column("ai_score", existing_type=sa.Integer(), nullable=False)
    else:
        op.alter_column("ticket_submissions", "ai_score", existing_type=sa.Integer(), nullable=False)

    if dialect == "sqlite":
        op.drop_index("uq_student_quiz", table_name="quiz_attempts")
    else:
        op.drop_constraint("uq_student_quiz", "quiz_attempts", type_="unique")
    op.drop_column("quiz_attempts", "first_attempt_xp")
    op.drop_column("quiz_attempts", "best_score")

    op.drop_index("idx_resources_type", table_name="resources")
    op.drop_index("idx_resources_category", table_name="resources")
    op.drop_index("idx_resources_week", table_name="resources")
    op.drop_index("idx_xp_ledger_created", table_name="xp_ledger")
    op.drop_index("idx_xp_ledger_student", table_name="xp_ledger")

    op.drop_index("idx_ticket_submissions_ticket", table_name="ticket_submissions")
    op.drop_index("idx_ticket_submissions_student", table_name="ticket_submissions")
    op.drop_index("idx_quiz_attempts_quiz", table_name="quiz_attempts")
    op.drop_index("idx_quiz_attempts_student", table_name="quiz_attempts")
    op.drop_index("idx_tickets_difficulty", table_name="tickets")
    op.drop_index("idx_tickets_week", table_name="tickets")
    op.drop_index("idx_quizzes_week", table_name="quizzes")
    op.drop_index("idx_students_xp", table_name="students")

    op.drop_table("resources")
    op.drop_table("xp_ledger")
