"""add_question_import_metadata

Revision ID: 6736e5d5172a
Revises: 274729e5d444
Create Date: 2026-07-25 02:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '6736e5d5172a'
down_revision = '274729e5d444'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('difficulty', sa.Integer(), nullable=True))
    op.add_column('questions', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('questions', sa.Column('source', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('fingerprint', sa.String(length=64), nullable=True))
    op.add_column('questions', sa.Column('imported_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('questions', sa.Column('import_filename', sa.Text(), nullable=True))
    op.add_column(
        'questions',
        sa.Column('flagged_for_review', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )
    op.add_column('questions', sa.Column('flag_reason', sa.Text(), nullable=True))
    op.create_index(op.f('ix_questions_fingerprint'), 'questions', ['fingerprint'], unique=False)
    op.create_index(op.f('ix_questions_flagged_for_review'), 'questions', ['flagged_for_review'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_questions_flagged_for_review'), table_name='questions')
    op.drop_index(op.f('ix_questions_fingerprint'), table_name='questions')
    op.drop_column('questions', 'flag_reason')
    op.drop_column('questions', 'flagged_for_review')
    op.drop_column('questions', 'import_filename')
    op.drop_column('questions', 'imported_at')
    op.drop_column('questions', 'fingerprint')
    op.drop_column('questions', 'source')
    op.drop_column('questions', 'tags')
    op.drop_column('questions', 'difficulty')
