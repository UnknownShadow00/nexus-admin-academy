"""Keep Week 20 focused on its Linux operations goal.

Revision ID: 0039_week20_required_path
Revises: 0038_safe_optional_quiz_mappings
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0039_week20_required_path"
down_revision = "0038_safe_optional_quiz_mappings"
branch_labels = None
depends_on = None


def _set_required(value: bool) -> None:
    op.get_bind().execute(sa.text("""
        UPDATE training_week_activities
        SET is_required=:required
        WHERE activity_type='video'
          AND content_ref IN ('145', '149', '153', '155', '161')
          AND training_week_id IN (
              SELECT id FROM training_weeks WHERE week_number=20
          )
    """), {"required": value})


def upgrade() -> None:
    _set_required(False)


def downgrade() -> None:
    _set_required(True)
