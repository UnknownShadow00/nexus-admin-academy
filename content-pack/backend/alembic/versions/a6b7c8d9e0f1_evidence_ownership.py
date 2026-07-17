"""Evidence uploader ownership — Part 9 security audit.

EvidenceArtifact had no link to its uploader, so any student could reference
another student's artifact IDs in a submission. Nullable for existing rows
(pre-fix artifacts have unknown uploaders and are treated as unowned).

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-10
"""
import sqlalchemy as sa
from alembic import op

revision = "a6b7c8d9e0f1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence_artifacts", sa.Column("student_id", sa.Integer(), nullable=True))
    op.create_index("ix_evidence_artifacts_student_id", "evidence_artifacts", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_artifacts_student_id", table_name="evidence_artifacts")
    op.drop_column("evidence_artifacts", "student_id")
