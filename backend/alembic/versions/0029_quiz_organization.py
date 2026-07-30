"""Add safe quiz organization and remediation assignment fields.

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-19
"""

import sqlalchemy as sa
from alembic import op


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deliberately avoid Alembic batch mode here. On SQLite, rebuilding the
    # parent quizzes table can fire ON DELETE CASCADE against questions.
    op.add_column("quizzes", sa.Column("quiz_purpose", sa.String(length=24), server_default="practice", nullable=False))
    op.add_column("quizzes", sa.Column("is_required", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("quizzes", sa.Column("show_in_weekly_checklist", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("quizzes", sa.Column("show_in_practice_library", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("quizzes", sa.Column("editorial_status", sa.String(length=24), server_default="unreviewed", nullable=False))
    op.add_column("quizzes", sa.Column("recommended_week", sa.Integer(), nullable=True))
    op.add_column("quizzes", sa.Column("prerequisite_week", sa.Integer(), nullable=True))
    op.add_column("quizzes", sa.Column("quality_score", sa.Integer(), nullable=True))
    op.add_column("quizzes", sa.Column("source_type", sa.String(length=24), server_default="unknown", nullable=False))
    op.add_column("quizzes", sa.Column("answer_keys_validated", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("quizzes", sa.Column("explanations_complete", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("quizzes", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_index("ix_quizzes_quiz_purpose", "quizzes", ["quiz_purpose"], unique=False)
    op.create_index("ix_quizzes_is_required", "quizzes", ["is_required"], unique=False)
    op.create_index("ix_quizzes_editorial_status", "quizzes", ["editorial_status"], unique=False)
    op.create_index("ix_quizzes_source_type", "quizzes", ["source_type"], unique=False)
    op.create_index("ix_quizzes_answer_keys_validated", "quizzes", ["answer_keys_validated"], unique=False)
    op.create_index("ix_quizzes_is_active", "quizzes", ["is_active"], unique=False)

    # Safe legacy defaults: static seed quizzes remain required; imported
    # content is optional, unreviewed, and excluded from progression.
    op.execute(
        sa.text(
            """
            UPDATE quizzes
               SET quiz_purpose = 'required',
                   is_required = true,
                   show_in_weekly_checklist = true,
                   show_in_practice_library = false,
                   editorial_status = 'validated',
                   recommended_week = week_number,
                   prerequisite_week = CASE WHEN week_number > 0 THEN week_number - 1 ELSE 0 END,
                   source_type = 'seed',
                   answer_keys_validated = true,
                   explanations_complete = true
             WHERE source_url IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE quizzes
               SET quiz_purpose = 'certification',
                   is_required = false,
                   show_in_weekly_checklist = false,
                   show_in_practice_library = true,
                   editorial_status = 'unreviewed',
                   source_type = CASE
                       WHEN lower(coalesce(source_url, '')) LIKE '%examcompass%' THEN 'examcompass'
                       WHEN lower(coalesce(source_url, '')) = 'csv_import' THEN 'manual'
                       ELSE 'scraped'
                   END,
                   answer_keys_validated = false,
                   explanations_complete = false
             WHERE source_url IS NOT NULL
            """
        )
    )

    op.create_table(
        "quiz_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(length=80), server_default="mentor_assignment", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "quiz_id", name="uq_quiz_assignment_student_quiz"),
    )
    op.create_index("ix_quiz_assignments_id", "quiz_assignments", ["id"], unique=False)
    op.create_index("ix_quiz_assignments_student_id", "quiz_assignments", ["student_id"], unique=False)
    op.create_index("ix_quiz_assignments_quiz_id", "quiz_assignments", ["quiz_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quiz_assignments_quiz_id", table_name="quiz_assignments")
    op.drop_index("ix_quiz_assignments_student_id", table_name="quiz_assignments")
    op.drop_index("ix_quiz_assignments_id", table_name="quiz_assignments")
    op.drop_table("quiz_assignments")
    for index in (
        "ix_quizzes_is_active", "ix_quizzes_answer_keys_validated", "ix_quizzes_source_type",
        "ix_quizzes_editorial_status", "ix_quizzes_is_required", "ix_quizzes_quiz_purpose",
    ):
        op.drop_index(index, table_name="quizzes")
    for column in (
        "is_active", "explanations_complete", "answer_keys_validated", "source_type",
        "quality_score", "prerequisite_week", "recommended_week", "editorial_status",
        "show_in_practice_library", "show_in_weekly_checklist", "is_required", "quiz_purpose",
    ):
        op.drop_column("quizzes", column)
