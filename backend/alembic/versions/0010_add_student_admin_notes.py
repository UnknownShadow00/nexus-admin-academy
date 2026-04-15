"""add student admin_notes

Revision ID: 0010_add_student_admin_notes
Revises: 0009_ticket_commands_used
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0010_add_student_admin_notes"
down_revision = "0009_ticket_commands_used"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("admin_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("students", "admin_notes")

