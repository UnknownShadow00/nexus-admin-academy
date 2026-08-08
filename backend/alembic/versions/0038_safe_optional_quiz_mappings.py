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
    28: ("Mobile Device Accessories Quiz", 5, "practice"),
    32: ("Social Engineering Quiz", 7, "practice"),
    33: ("Threats & Vulnerabilities Quiz", 7, "practice"),
    56: ("TCP & UDP Ports Quiz", 11, "remediation"),
    59: ("Network Configuration Concepts Quiz", 8, "remediation"),
    63: ("Network Types Quiz", 9, "remediation"),
}


def upgrade() -> None:
    bind = op.get_bind()
    for quiz_id, (title, week, purpose) in MAPPINGS.items():
        bind.execute(sa.text("""
            UPDATE quizzes
            SET week_number=:week, recommended_week=:week,
                prerequisite_week=:prerequisite, quiz_purpose=:purpose,
                is_required=:required, show_in_weekly_checklist=:required,
                show_in_practice_library=:practice
            WHERE id=:id AND title=:title
        """), {
            "id": quiz_id, "title": title, "week": week, "prerequisite": max(0, week - 1),
            "purpose": purpose, "required": False, "practice": True,
        })


def downgrade() -> None:
    bind = op.get_bind()
    for quiz_id, (title, _week, _purpose) in MAPPINGS.items():
        bind.execute(sa.text("""
            UPDATE quizzes
            SET week_number=NULL, recommended_week=NULL, prerequisite_week=NULL,
                quiz_purpose='certification', is_required=:required,
                show_in_weekly_checklist=:required, show_in_practice_library=:required
            WHERE id=:id AND title=:title AND is_required=:required
        """), {"id": quiz_id, "title": title, "required": False})
