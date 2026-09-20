"""Nexus V2: ordered multi-objective question mappings (development only).

Revision ID: 0067_v2_question_objectives
Revises: 0066_v2_explain_submissions
Create Date: 2026-08-30

The existing ``question_v2_meta.objective_code`` remains the deterministic
primary objective for backwards compatibility. Existing resolved mappings are
backfilled into the new association table.
"""

from alembic import op
import sqlalchemy as sa

revision = "0067_v2_question_objectives"
down_revision = "0066_v2_explain_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_objectives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_v2_meta_id", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["objective_id"], ["certification_objectives.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_v2_meta_id"], ["question_v2_meta.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "question_v2_meta_id", "objective_id", name="uq_question_objectives_mapping"
        ),
        sa.UniqueConstraint(
            "question_v2_meta_id", "position", name="uq_question_objectives_position"
        ),
    )
    op.create_index("ix_question_objectives_id", "question_objectives", ["id"])
    op.create_index(
        "ix_question_objectives_question_v2_meta_id",
        "question_objectives",
        ["question_v2_meta_id"],
    )
    op.create_index(
        "ix_question_objectives_objective_id",
        "question_objectives",
        ["objective_id"],
    )
    op.execute(
        """
        INSERT INTO question_objectives (question_v2_meta_id, objective_id, position)
        SELECT qvm.id, objective.id, 0
        FROM question_v2_meta AS qvm
        JOIN certification_objectives AS objective
          ON objective.certification_version_id = qvm.certification_version_id
         AND objective.objective_code = qvm.objective_code
        WHERE qvm.objective_code IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("question_objectives")
