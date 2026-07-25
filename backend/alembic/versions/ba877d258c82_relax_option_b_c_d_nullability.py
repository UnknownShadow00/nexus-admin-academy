"""relax_option_b_c_d_nullability

Revision ID: ba877d258c82
Revises: 6736e5d5172a
Create Date: 2026-07-25 10:05:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'ba877d258c82'
down_revision = '6736e5d5172a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only option_a stays required. The shared validator already enforces
    # "at least 2 non-blank options" at the application layer — the DB no
    # longer forces a question to have 4 options just to satisfy NOT NULL.
    # All 967 existing rows already have non-null b/c/d, so this is a pure
    # widening: no data is touched, nothing existing can violate it.
    with op.batch_alter_table("questions") as batch_op:
        batch_op.alter_column("option_b", existing_type=sa.Text(), nullable=True)
        batch_op.alter_column("option_c", existing_type=sa.Text(), nullable=True)
        batch_op.alter_column("option_d", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.alter_column("option_d", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column("option_c", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column("option_b", existing_type=sa.Text(), nullable=False)
