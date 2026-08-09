"""Publish improved, grading-aligned ticket content as new versions.

Revision ID: 0040_service_desk_quality_versions
Revises: 0039_week20_required_path
Create Date: 2026-08-08
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from alembic import op
import sqlalchemy as sa


revision = "0040_service_desk_quality_versions"
down_revision = "0039_week20_required_path"
branch_labels = None
depends_on = None


PATCHES = {
    "inc2402": {
        "description": {
            "businessImpact": "One loading lane is recording orders on paper, slowing dispatch and increasing re-entry work.",
            "issue": "The scanner at loading lane 2 disconnects from the warehouse network every few minutes. The scanner at the next lane stays connected.",
            "reportedByLine": "Reported by the morning dispatch lead after the issue continued through the first hour of the shift.",
            "troubleshooting": [
                "Restarted the affected scanner.",
                "Moved the affected scanner beside a working scanner; only the affected unit disconnected.",
                "Confirmed wired packing stations remain connected.",
            ],
        },
        "hints": [
            "Use the working scanner beside it to decide whether the fault follows the network area or one device.",
            "Open Remote Desktop and compare the affected scanner's network settings with the working unit.",
            "Repair the affected network profile, renew its address, and then watch the connection long enough to verify stability.",
        ],
    },
    "inc2404": {
        "hints": [
            "Work out whether the fault follows the headset or remains with the workstation.",
            "Use Asset Management to record the confirmed hardware condition, then review replacement options.",
            "Mark the faulty headset as damaged, ship one replacement headset to Elliot Ward, and document how the requester should verify it.",
        ],
    },
}


def upgrade() -> None:
    bind = op.get_bind()
    for stable_key, patch in PATCHES.items():
        row = bind.execute(sa.text("""
            SELECT s.id AS scenario_id, v.definition_json, v.version_number
            FROM service_desk_scenarios s
            JOIN service_desk_scenario_versions v ON v.scenario_id=s.id
            WHERE s.stable_key=:stable_key AND v.status='published'
            ORDER BY v.version_number DESC LIMIT 1
        """), {"stable_key": stable_key}).mappings().first()
        if not row:
            continue
        stored_definition = row["definition_json"]
        definition = (
            json.loads(stored_definition)
            if isinstance(stored_definition, str)
            else deepcopy(stored_definition)
        )
        definition.update(patch)
        encoded = json.dumps(definition, sort_keys=True)
        definition_hash = hashlib.sha256(encoded.encode()).hexdigest()
        exists = bind.execute(sa.text("""
            SELECT id FROM service_desk_scenario_versions
            WHERE scenario_id=:scenario_id AND definition_hash=:definition_hash
        """), {"scenario_id": row["scenario_id"], "definition_hash": definition_hash}).first()
        if exists:
            continue
        statement = sa.text("""
            INSERT INTO service_desk_scenario_versions
              (scenario_id, version_number, definition_json, definition_hash,
               validation_status, status, published_at, published_by)
            VALUES
              (:scenario_id, :version_number, :definition, :definition_hash,
               'valid', 'published', :published_at, 'migration-0040')
        """).bindparams(sa.bindparam("definition", type_=sa.JSON()))
        bind.execute(statement, {
            "scenario_id": row["scenario_id"],
            "version_number": row["version_number"] + 1,
            "definition": definition,
            "definition_hash": definition_hash,
            "published_at": datetime.now(timezone.utc),
        })


def downgrade() -> None:
    op.get_bind().execute(sa.text("""
        UPDATE service_desk_scenario_versions
        SET status='disabled'
        WHERE published_by='migration-0040' AND status='published'
    """))
