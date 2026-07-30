"""fix quiz_attempts best_score constraint

Revision ID: 0015_fix_best_score_constraint
Revises: 0014_question_multi_answer
Create Date: 2026-02-21
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_fix_best_score_constraint"
down_revision = "0014_question_multi_answer"
branch_labels = None
depends_on = None


def _has_best_score_constraint() -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        constraint.get("name") == "ck_quiz_attempts_best_score"
        for constraint in inspector.get_check_constraints("quiz_attempts")
    )


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    with op.batch_alter_table("quiz_attempts") as batch_op:
        if dialect != "sqlite" and _has_best_score_constraint():
            batch_op.drop_constraint("ck_quiz_attempts_best_score", type_="check")
        batch_op.create_check_constraint(
            "ck_quiz_attempts_best_score",
            "best_score IS NULL OR best_score >= 0",
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    with op.batch_alter_table("quiz_attempts") as batch_op:
        if dialect != "sqlite" and _has_best_score_constraint():
            batch_op.drop_constraint("ck_quiz_attempts_best_score", type_="check")
        batch_op.create_check_constraint(
            "ck_quiz_attempts_best_score",
            "best_score IS NULL OR best_score BETWEEN 0 AND 10",
        )
