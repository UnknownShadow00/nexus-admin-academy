"""add_student_lesson_notes

Revision ID: 853fceaf9a7a
Revises: 0026
Create Date: 2026-05-16 18:05:37.341744
"""

from alembic import op
import sqlalchemy as sa


revision = "853fceaf9a7a"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_lesson_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "lesson_id", name="uq_student_lesson_note"),
    )
    op.create_index(op.f("ix_student_lesson_notes_id"), "student_lesson_notes", ["id"], unique=False)
    op.create_index(op.f("ix_student_lesson_notes_lesson_id"), "student_lesson_notes", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_student_lesson_notes_student_id"), "student_lesson_notes", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_student_lesson_notes_student_id"), table_name="student_lesson_notes")
    op.drop_index(op.f("ix_student_lesson_notes_lesson_id"), table_name="student_lesson_notes")
    op.drop_index(op.f("ix_student_lesson_notes_id"), table_name="student_lesson_notes")
    op.drop_table("student_lesson_notes")
