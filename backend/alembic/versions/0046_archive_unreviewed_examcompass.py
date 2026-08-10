"""Archive unreviewed imported quiz banks without deleting history.

Revision ID: 0046_archive_unreviewed_examcompass
Revises: 0045_preserve_authored_question_identity
Create Date: 2026-08-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0046_archive_unreviewed_examcompass"
down_revision = "0045_preserve_authored_question_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Imported banks without completed editorial/key review are already blocked
    # by the student visibility gate. Archive them explicitly so active admin
    # inventory no longer implies a student-ready destination. IDs, questions,
    # attempts, and snapshots remain untouched.
    op.get_bind().execute(sa.text("""
        UPDATE quizzes
        SET is_active = 0,
            show_in_practice_library = 0,
            editorial_status = 'archived'
        WHERE source_type = 'examcompass'
          AND (editorial_status <> 'validated' OR answer_keys_validated = 0)
    """))


def downgrade() -> None:
    # Deliberately non-destructive: restoring prior publication state requires
    # an explicit editorial decision, not a blind downgrade side effect.
    pass
