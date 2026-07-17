"""Add quizzes.status — corrects pre-existing model/migration drift.

The Quiz model declared a status column (draft/published) that no migration
ever created; tests passed via create_all while Alembic-migrated databases
lacked the column. Found by systematic drift audit during Phase A seeding.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-10
"""
import sqlalchemy as sa
from alembic import op

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing quizzes were live before this column existed → default them to
    # published so student-visible content doesn't vanish on upgrade.
    op.add_column("quizzes", sa.Column("status", sa.String(20), nullable=False, server_default="published"))


def downgrade() -> None:
    op.drop_column("quizzes", "status")
