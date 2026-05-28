"""add_flashcard_reviews

Revision ID: 17dcbbab1af8
Revises: 853fceaf9a7a
Create Date: 2026-05-16 19:02:01.800127
"""

from alembic import op
import sqlalchemy as sa

revision = '17dcbbab1af8'
down_revision = '853fceaf9a7a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('flashcard_reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('interval_days', sa.Integer(), nullable=False),
    sa.Column('ease_factor', sa.Float(), nullable=False),
    sa.Column('review_count', sa.Integer(), nullable=False),
    sa.Column('last_rating', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('student_id', 'question_id', name='uq_flashcard_reviews_student_question')
    )
    op.create_index(op.f('ix_flashcard_reviews_id'), 'flashcard_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_flashcard_reviews_question_id'), 'flashcard_reviews', ['question_id'], unique=False)
    op.create_index(op.f('ix_flashcard_reviews_student_id'), 'flashcard_reviews', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_flashcard_reviews_student_id'), table_name='flashcard_reviews')
    op.drop_index(op.f('ix_flashcard_reviews_question_id'), table_name='flashcard_reviews')
    op.drop_index(op.f('ix_flashcard_reviews_id'), table_name='flashcard_reviews')
    op.drop_table('flashcard_reviews')
