"""Fix the Week 1 module prerequisite and capstone role requirements.

MOD-000 has no lesson-linked quiz, ticket, or lab, so its mastery is
permanently 0%. Its prerequisite on MOD-001 made Week 1 permanently locked in
the Learning Path even though the Week Plan correctly made it available.

Revision ID: 0030_week_gating_data_fixes
Revises: 0029
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op


revision = "0030_week_gating_data_fixes"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MOD-000 has no lesson-linked assessment. Its calculated mastery therefore
    # cannot rise above 0%, so MOD-001's 70% prerequisite was unsatisfiable.
    op.execute(
        sa.text(
            """
            UPDATE modules
               SET prerequisite_module_id = NULL
             WHERE code = 'MOD-001'
               AND prerequisite_module_id = (
                   SELECT id FROM modules WHERE code = 'MOD-000'
               )
            """
        )
    )

    # Resolve role IDs by the existing role name and rank; IDs are deployment
    # data and must not be assumed to equal rank_order. Each statement is
    # explicitly limited to one existing live template row.
    for capstone_id, title, role_name, rank_order in (
        (1, "CompTIA A+ Module 1 Capstone: Hardware & Troubleshooting", "Support Technician I", 2),
        (2, "CompTIA A+ Module 2 Capstone: Networking & OS", "Support Technician II", 3),
        (3, "Take Over Maple & Finch Co.", "Junior Systems Technician", 5),
    ):
        op.execute(
            sa.text(
                """
                UPDATE capstone_templates
                   SET role_level = (
                       SELECT id
                         FROM roles
                        WHERE name = :role_name
                          AND rank_order = :rank_order
                   )
                 WHERE id = :capstone_id
                   AND title = :title
                """
            ).bindparams(
                capstone_id=capstone_id,
                title=title,
                role_name=role_name,
                rank_order=rank_order,
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE modules
               SET prerequisite_module_id = (SELECT id FROM modules WHERE code = 'MOD-000')
             WHERE code = 'MOD-001'
               AND prerequisite_module_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE capstone_templates
               SET role_level = NULL
             WHERE id IN (1, 2, 3)
               AND title IN (
                   'CompTIA A+ Module 1 Capstone: Hardware & Troubleshooting',
                   'CompTIA A+ Module 2 Capstone: Networking & OS',
                   'Take Over Maple & Finch Co.'
               )
            """
        )
    )
