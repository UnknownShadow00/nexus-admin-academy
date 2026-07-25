"""add_flashcard_last_wrong_answer

Revision ID: 274729e5d444
Revises: 0035_service_desk_browser_mvp
Create Date: 2026-07-25 02:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '274729e5d444'
down_revision = '0035_service_desk_browser_mvp'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('flashcard_reviews', sa.Column('last_wrong_answer', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('flashcard_reviews', 'last_wrong_answer')
