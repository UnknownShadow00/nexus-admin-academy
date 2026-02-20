"""add quiz multi video fields

Revision ID: 0011_quiz_multi_video
Revises: 0010_add_student_admin_notes
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0011_quiz_multi_video"
down_revision = "0010_add_student_admin_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quizzes") as batch_op:
        batch_op.add_column(sa.Column("source_urls", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("question_count", sa.Integer(), nullable=False, server_default="10"))
        batch_op.alter_column("source_url", existing_type=sa.Text(), nullable=True)



def downgrade() -> None:
    with op.batch_alter_table("quizzes") as batch_op:
        batch_op.alter_column("source_url", existing_type=sa.Text(), nullable=False)
        batch_op.drop_column("question_count")
        batch_op.drop_column("source_urls")
