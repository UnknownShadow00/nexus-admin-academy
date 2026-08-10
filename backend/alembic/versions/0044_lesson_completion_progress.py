"""Make lesson completion explicit and retire the empty methodology wrapper.

Revision ID: 0044_lesson_completion_progress
Revises: 0043_retire_legacy_tickets
Create Date: 2026-08-10

StudentLessonNote remains an optional study aid. It is deliberately preserved
and is no longer a completion signal.
"""

from alembic import op
import sqlalchemy as sa


revision = "0044_lesson_completion_progress"
down_revision = "0043_retire_legacy_tickets"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "student_lesson_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "lesson_id", name="uq_student_lesson_progress"),
    )
    op.create_index(op.f("ix_student_lesson_progress_id"), "student_lesson_progress", ["id"], unique=False)
    op.create_index(op.f("ix_student_lesson_progress_student_id"), "student_lesson_progress", ["student_id"], unique=False)
    op.create_index(op.f("ix_student_lesson_progress_lesson_id"), "student_lesson_progress", ["lesson_id"], unique=False)

    bind = op.get_bind()
    # Keep the historical row and its notes, but remove the empty wrapper from
    # every live learning surface and weekly requirement.
    bind.execute(sa.text("""
        UPDATE lessons
        SET status = 'retired'
        WHERE title = 'CompTIA 6-Step Process'
          AND module_id = (SELECT id FROM modules WHERE code = 'MOD-000')
    """))
    bind.execute(sa.text("""
        DELETE FROM training_week_activities
        WHERE activity_type = 'lesson'
          AND content_ref IN (
              SELECT CAST(id AS TEXT)
              FROM lessons
              WHERE title = 'CompTIA 6-Step Process'
                AND module_id = (SELECT id FROM modules WHERE code = 'MOD-000')
          )
    """))


def downgrade():
    op.drop_index(op.f("ix_student_lesson_progress_lesson_id"), table_name="student_lesson_progress")
    op.drop_index(op.f("ix_student_lesson_progress_student_id"), table_name="student_lesson_progress")
    op.drop_index(op.f("ix_student_lesson_progress_id"), table_name="student_lesson_progress")
    op.drop_table("student_lesson_progress")
