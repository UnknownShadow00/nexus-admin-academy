"""Publish process-aware Service Desk grading definitions.

Revision ID: 0042_service_desk_process_grading
Revises: 0041_verified_question_keys
Create Date: 2026-08-09
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from alembic import op
import sqlalchemy as sa


revision = "0042_service_desk_process_grading"
down_revision = "0041_verified_question_keys"
branch_labels = None
depends_on = None


PATCHES = {
    "inc2401": {
        "description": {
            "issue": "The finance reporting portal accepts the first authentication step, then returns to the sign-in screen before the dashboard loads on the assigned laptop.",
            "troubleshooting": [
                "Confirmed Avery can sign in to another internal service.",
                "Confirmed the directory account is active and not locked.",
                "The Finance portal returned to sign-in before the dashboard loaded.",
            ],
        },
        "hints": [
            "The employee account is healthy, so distinguish an account problem from a browser-session problem.",
            "Reproduce the Finance sign-in loop and review the local browser/profile evidence.",
            "Clear the stale browser profile storage, then confirm the original Finance portal opens.",
        ],
    },
    "inc2402": {
        "priority": "high",
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
    "inc2403": {},
    "inc2404": {
        "hints": [
            "Work out whether the fault follows the headset or remains with the workstation.",
            "Use Asset Management to record the confirmed hardware condition, then review replacement options.",
            "Mark the faulty headset as damaged, ship one replacement headset to Elliot Ward, and document how the requester should verify it.",
        ],
    },
    "inc2405": {
        "title": "Facilities calendar shortcut opens an archived workspace",
        "description": {
            "issue": "The new coordinator can sign in and already has Facilities Calendar access, but the desktop calendar shortcut opens an archived-location error.",
            "troubleshooting": [
                "Confirmed the user can open their personal calendar and another current Facilities calendar.",
                "Confirmed the requester is already in the Facilities Calendar access group.",
                "Used the desktop calendar shortcut, which opened an archived-location error.",
            ],
        },
        "hints": [
            "Confirm that the requested calendar exists and that the requester already has legitimate access.",
            "Inspect the calendar workspace shortcut or mapping and compare it with the current Facilities location.",
            "Repair the obsolete mapping and ask the requester to open the original calendar workspace again.",
        ],
    },
    "inc2406": {
        "title": "Partner workspace unavailable while VPN is disconnected",
        "description": {
            "issue": "The laptop has normal internet access, but the secure partner workspace cannot be reached because the company VPN is disconnected.",
            "troubleshooting": [
                "Confirmed normal internet browsing works.",
                "Confirmed the partner share is unavailable from the home network.",
                "The company VPN client is disconnected.",
            ],
        },
        "hints": [
            "Separate ordinary internet access from access to a private company resource.",
            "Confirm whether the secure partner share is reachable before changing its mapped-drive configuration.",
            "Reconnect the company VPN, then verify the original partner workspace opens.",
        ],
    },
    "inc2407": {},
    "inc2408": {},
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
        definition = json.loads(stored_definition) if isinstance(stored_definition, str) else deepcopy(stored_definition)
        for key, value in patch.items():
            if key == "description":
                definition.setdefault("description", {}).update(value)
            else:
                definition[key] = value
        definition["objective_catalog_version"] = "process-v3"
        scenario_description = " ".join(
            part for part in (
                definition.get("description", {}).get("issue"),
                definition.get("description", {}).get("businessImpact"),
            ) if isinstance(part, str)
        )
        bind.execute(sa.text("""
            UPDATE service_desk_scenarios
            SET title=:title, description=:description,
                category=:category, difficulty=:difficulty
            WHERE id=:scenario_id
        """), {
            "scenario_id": row["scenario_id"], "title": definition.get("title", stable_key),
            "description": scenario_description, "category": definition.get("category", "service_desk"),
            "difficulty": {"low": 1, "medium": 2, "high": 3, "critical": 5}.get(definition.get("priority"), 1),
        })
        encoded = json.dumps(definition, sort_keys=True)
        definition_hash = hashlib.sha256(encoded.encode()).hexdigest()
        exists = bind.execute(sa.text("""
            SELECT id FROM service_desk_scenario_versions
            WHERE scenario_id=:scenario_id AND definition_hash=:definition_hash
        """), {"scenario_id": row["scenario_id"], "definition_hash": definition_hash}).first()
        if exists:
            continue
        number = bind.execute(sa.text("""
            SELECT COALESCE(MAX(version_number), 0) FROM service_desk_scenario_versions
            WHERE scenario_id=:scenario_id
        """), {"scenario_id": row["scenario_id"]}).scalar_one() + 1
        statement = sa.text("""
            INSERT INTO service_desk_scenario_versions
              (scenario_id, version_number, definition_json, definition_hash,
               validation_status, status, published_at, published_by)
            VALUES
              (:scenario_id, :version_number, :definition, :definition_hash,
               'valid', 'published', :published_at, 'migration-0042')
        """).bindparams(sa.bindparam("definition", type_=sa.JSON()))
        bind.execute(statement, {
            "scenario_id": row["scenario_id"], "version_number": number,
            "definition": definition, "definition_hash": definition_hash,
            "published_at": datetime.now(timezone.utc),
        })


def downgrade() -> None:
    op.get_bind().execute(sa.text("""
        UPDATE service_desk_scenario_versions SET status='disabled'
        WHERE published_by='migration-0042' AND status='published'
    """))
