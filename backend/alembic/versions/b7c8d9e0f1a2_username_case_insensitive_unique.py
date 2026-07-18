"""Case-insensitive unique index on students.username

"Shak" and "shak" must be the same account: logins compare lower(username),
and this index makes the DB reject case-variant duplicates. Expression
indexes work on both SQLite (3.9+) and PostgreSQL.

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_students_username_lower",
        "students",
        [sa.text("lower(username)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_students_username_lower", table_name="students")
