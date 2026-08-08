"""Expose reviewed legacy quizzes as non-blocking extra practice.

Revision ID: 0038_safe_optional_quiz_mappings
Revises: 0037_curated_question_explanations
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0038_safe_optional_quiz_mappings"
down_revision = "0037_curated_question_explanations"
branch_labels = None
depends_on = None


MAPPINGS = {
    28: (5, "practice"),
    32: (7, "practice"),
    33: (7, "practice"),
    56: (11, "remediation"),
    59: (8, "remediation"),
    63: (9, "remediation"),
}


def upgrade() -> None:
    bind = op.get_bind()
    for quiz_id, (week, purpose) in MAPPINGS.items():
        bind.execute(sa.text("""
            UPDATE quizzes
            SET week_number=:week, recommended_week=:week,
                prerequisite_week=:prerequisite, quiz_purpose=:purpose,
                is_required=:required, show_in_weekly_checklist=:required,
                show_in_practice_library=:practice
            WHERE id=:id
        """), {
            "id": quiz_id, "week": week, "prerequisite": max(0, week - 1),
            "purpose": purpose, "required": False, "practice": True,
        })


def downgrade() -> None:
    bind = op.get_bind()
    for quiz_id in MAPPINGS:
        bind.execute(sa.text("""
            UPDATE quizzes
            SET show_in_practice_library=:practice
            WHERE id=:id AND is_required=:required
        """), {"id": quiz_id, "practice": False, "required": False})
