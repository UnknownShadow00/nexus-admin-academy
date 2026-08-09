"""Correct two objectively wrong Windows troubleshooting answer keys.

Revision ID: 0041_verified_question_keys
Revises: 0040_service_desk_quality_versions
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0041_verified_question_keys"
down_revision = "0040_service_desk_quality_versions"
branch_labels = None
depends_on = None


ROWS = (
    (
        "Which of the tools listed below can be used to identify resource-intensive applications that cause degraded performance in Microsoft Windows?",
        "A", "D",
        "Task Manager shows per-application CPU, memory, disk, and network use, which helps identify an application degrading performance. Event Viewer records system and application events but is not the primary live resource-usage view.",
    ),
    (
        "A technician is troubleshooting a Windows system that powers off unexpectedly after a GPU driver update. Which Windows utility should the technician use to manually roll back the specific driver?",
        "B", "D",
        "Device Manager provides the Roll Back Driver control for a specific device. Windows Update installs updates, but it is not the utility used to manually restore one device's previous driver.",
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    for text, old_answer, new_answer, explanation in ROWS:
        bind.execute(sa.text("""
            UPDATE questions SET correct_answer=:new_answer, correct_answers=NULL,
                explanation=:explanation, flagged_for_review=:review, flag_reason=NULL
            WHERE question_text=:text AND correct_answer=:old_answer
        """), {"text": text, "old_answer": old_answer, "new_answer": new_answer,
                 "explanation": explanation, "review": False})


def downgrade() -> None:
    bind = op.get_bind()
    for text, old_answer, new_answer, explanation in ROWS:
        bind.execute(sa.text("""
            UPDATE questions SET correct_answer=:old_answer, explanation='',
                flagged_for_review=:review,
                flag_reason='Answer key requires review after rollback of migration 0041.'
            WHERE question_text=:text AND correct_answer=:new_answer
              AND explanation=:explanation
        """), {"text": text, "old_answer": old_answer, "new_answer": new_answer,
                 "explanation": explanation, "review": True})
