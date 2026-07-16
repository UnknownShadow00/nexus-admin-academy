"""add_evidence_artifact_student_id

Revision ID: c456ad196e2d
Revises: 0027_drop_ai_tables
Create Date: 2026-07-16 23:37:17.468938
"""

from alembic import op
import sqlalchemy as sa

revision = 'c456ad196e2d'
down_revision = '0027_drop_ai_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('evidence_artifacts') as batch_op:
        batch_op.add_column(sa.Column('student_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_evidence_artifacts_student_id', ['student_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_evidence_artifacts_student_id',
            'students',
            ['student_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('evidence_artifacts') as batch_op:
        batch_op.drop_constraint('fk_evidence_artifacts_student_id', type_='foreignkey')
        batch_op.drop_index('ix_evidence_artifacts_student_id')
        batch_op.drop_column('student_id')
