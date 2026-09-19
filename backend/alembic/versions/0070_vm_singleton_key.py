"""Add an atomic singleton lease for fixed-network VM labs.

Revision ID: 0070_vm_singleton_key
Revises: 0069_legacy_assessment_attempts
Create Date: 2026-09-19
"""

import json

from alembic import op
import sqlalchemy as sa


revision = "0070_vm_singleton_key"
down_revision = "0069_legacy_assessment_attempts"
branch_labels = None
depends_on = None

_INC2504_KEY = "inc2504_printer_stale_ip"
_ACTIVE_STATUSES = (
    "provisioning",
    "starting",
    "configuring_vm",
    "waiting_for_ip",
    "configuring_connection",
    "running",
    "destroying",
    "cleanup_failed",
)


def _requirements(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def upgrade() -> None:
    op.add_column(
        "vm_assignments",
        sa.Column("singleton_key", sa.String(length=80), nullable=True),
    )

    connection = op.get_bind()
    active = connection.execute(
        sa.text(
            "SELECT va.id, lt.environment_requirements "
            "FROM vm_assignments AS va "
            "JOIN lab_runs AS lr ON lr.id = va.lab_run_id "
            "JOIN lab_templates AS lt ON lt.id = lr.lab_template_id "
            "WHERE va.status IN ("
            + ", ".join(f":status_{index}" for index in range(len(_ACTIVE_STATUSES)))
            + ")"
        ),
        {
            f"status_{index}": status
            for index, status in enumerate(_ACTIVE_STATUSES)
        },
    ).mappings()
    singleton_ids = []
    for row in active:
        provisioning = _requirements(row["environment_requirements"]).get("provisioning")
        if isinstance(provisioning, dict) and provisioning.get("handler") == _INC2504_KEY:
            singleton_ids.append(row["id"])

    if len(singleton_ids) > 1:
        raise RuntimeError(
            "Cannot add INC2504 singleton lease while multiple active assignments exist"
        )
    if singleton_ids:
        connection.execute(
            sa.text(
                "UPDATE vm_assignments SET singleton_key = :singleton_key WHERE id = :id"
            ),
            {"singleton_key": _INC2504_KEY, "id": singleton_ids[0]},
        )

    op.create_index(
        "uq_vm_assignments_singleton_key",
        "vm_assignments",
        ["singleton_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_vm_assignments_singleton_key", table_name="vm_assignments")
    op.drop_column("vm_assignments", "singleton_key")
