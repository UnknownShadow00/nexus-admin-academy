"""drop uq_student_quiz so each quiz attempt gets its own row

Revision ID: d5e6f7a8b9c0
Revises: c456ad196e2d
Create Date: 2026-07-16 23:55:00.000000
"""

from alembic import op

revision = 'd5e6f7a8b9c0'
down_revision = 'c456ad196e2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.drop_index("uq_student_quiz", table_name="quiz_attempts")
    else:
        op.drop_constraint("uq_student_quiz", "quiz_attempts", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.create_index("uq_student_quiz", "quiz_attempts", ["student_id", "quiz_id"], unique=True)
    else:
        op.create_unique_constraint("uq_student_quiz", "quiz_attempts", ["student_id", "quiz_id"])
