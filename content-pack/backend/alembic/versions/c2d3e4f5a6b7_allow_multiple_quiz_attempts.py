"""Allow multiple quiz attempt rows per (student, quiz) — TB-06.

Retakes previously overwrote the single QuizAttempt row because of
uq_student_quiz, created by migration 0002 as a UNIQUE INDEX on SQLite
and a UNIQUE CONSTRAINT on PostgreSQL. This migration mirrors that
dialect branching when dropping it, so both local SQLite and Supabase
PostgreSQL upgrade cleanly.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-10
"""
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        op.drop_index("uq_student_quiz", table_name="quiz_attempts")
    else:
        op.drop_constraint("uq_student_quiz", "quiz_attempts", type_="unique")


def downgrade() -> None:
    # NOTE: downgrade fails if multiple attempts per (student, quiz) exist.
    # Deduplicate first (keep latest attempt) before downgrading.
    if _is_sqlite():
        op.create_index("uq_student_quiz", "quiz_attempts", ["student_id", "quiz_id"], unique=True)
    else:
        op.create_unique_constraint("uq_student_quiz", "quiz_attempts", ["student_id", "quiz_id"])
