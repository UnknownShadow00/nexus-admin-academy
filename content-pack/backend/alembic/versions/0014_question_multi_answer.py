"""add questions correct_answers

Revision ID: 0014_question_multi_answer
Revises: 0013_quiz_attempt_results
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_question_multi_answer"
down_revision = "0013_quiz_attempt_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(sa.Column("correct_answers", sa.Text(), nullable=True))
        batch_op.drop_constraint("ck_questions_correct_answer", type_="check")


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_column("correct_answers")
        batch_op.create_check_constraint(
            "ck_questions_correct_answer",
            "correct_answer IN ('A','B','C','D')",
        )
