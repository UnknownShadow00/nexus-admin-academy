"""fix quiz_attempts best_score constraint

Revision ID: 0015_fix_best_score_constraint
Revises: 0014_question_multi_answer
Create Date: 2026-02-21
"""

from alembic import op


revision = "0015_fix_best_score_constraint"
down_revision = "0014_question_multi_answer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove the 0-10 cap — quizzes can have any number of questions
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.drop_constraint("ck_quiz_attempts_best_score", type_="check")
        batch_op.create_check_constraint(
            "ck_quiz_attempts_best_score",
            "best_score IS NULL OR best_score >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.drop_constraint("ck_quiz_attempts_best_score", type_="check")
        batch_op.create_check_constraint(
            "ck_quiz_attempts_best_score",
            "best_score IS NULL OR best_score BETWEEN 0 AND 10",
        )
