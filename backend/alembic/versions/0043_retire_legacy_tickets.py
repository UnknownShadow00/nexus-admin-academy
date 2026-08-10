"""Convert reviewed legacy ticket curriculum to immutable Service Desk cases.

Revision ID: 0043_retire_legacy_tickets
Revises: 0042_service_desk_process_grading
Create Date: 2026-08-10

Ticket and TicketSubmission history is deliberately untouched. This migration
adds new Service Desk scenario versions and changes only live curriculum
configuration rows that pointed at the retired student product.
"""

from datetime import datetime, timezone
import hashlib
import json

from alembic import op
import sqlalchemy as sa

from app.services.service_desk_objectives import PROCESS_CATALOG_VERSION
from seed import SERVICE_DESK_TICKET_FIXTURES


revision = "0043_retire_legacy_tickets"
down_revision = "0042_service_desk_process_grading"
branch_labels = None
depends_on = None


CURRICULUM_SCENARIOS = {
    1: "inc2407", 2: "inc2503", 3: "inc2501", 4: "inc2509",
    5: "inc2502", 6: "inc2505", 7: "inc2508", 8: "inc2504",
    14: "inc2510",
}
NEW_KEYS = {f"inc{number}" for number in range(2501, 2511)}


def upgrade():
    bind = op.get_bind()
    now = datetime.now(timezone.utc).isoformat()
    for ticket in SERVICE_DESK_TICKET_FIXTURES:
        stable_key = ticket["id"].lower()
        if stable_key not in NEW_KEYS:
            continue
        definition = {**ticket, "objective_catalog_version": PROCESS_CATALOG_VERSION}
        definition_hash = hashlib.sha256(json.dumps(definition, sort_keys=True).encode("utf-8")).hexdigest()
        row = bind.execute(sa.text("SELECT id FROM service_desk_scenarios WHERE stable_key=:stable_key"), {"stable_key": stable_key}).first()
        if row is None:
            bind.execute(sa.text("""
                INSERT INTO service_desk_scenarios (stable_key, title, description, category, difficulty, status)
                VALUES (:stable_key, :title, :description, :category, :difficulty, 'active')
            """), {
                "stable_key": stable_key, "title": ticket["title"],
                "description": f'{ticket["description"]["issue"]} {ticket["description"]["businessImpact"]}',
                "category": ticket["category"], "difficulty": {"critical": 4, "high": 3, "medium": 2, "low": 1}[ticket["priority"]],
            })
            scenario_id = bind.execute(
                sa.text("SELECT id FROM service_desk_scenarios WHERE stable_key=:stable_key"),
                {"stable_key": stable_key},
            ).scalar_one()
        else:
            scenario_id = row[0]
        exists = bind.execute(sa.text("SELECT id FROM service_desk_scenario_versions WHERE scenario_id=:scenario_id AND definition_hash=:definition_hash"), {"scenario_id": scenario_id, "definition_hash": definition_hash}).first()
        if exists is None:
            version = bind.execute(sa.text("SELECT COALESCE(MAX(version_number), 0) FROM service_desk_scenario_versions WHERE scenario_id=:scenario_id"), {"scenario_id": scenario_id}).scalar_one()
            bind.execute(sa.text("""
                INSERT INTO service_desk_scenario_versions
                (scenario_id, version_number, definition_json, definition_hash, validation_status, status, published_at, published_by)
                VALUES (:scenario_id, :version_number, :definition_json, :definition_hash, 'valid', 'published', :published_at, 'migration-0043')
            """), {
                "scenario_id": scenario_id, "version_number": int(version) + 1,
                "definition_json": json.dumps(definition), "definition_hash": definition_hash, "published_at": now,
            })

    # Retire all live references to old support_ticket content. Existing learner
    # submissions stay in their own historical table; only curriculum config is
    # replaced, and only where the reviewed Service Desk equivalent exists.
    legacy_activity_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM training_week_activities WHERE activity_type='support_ticket'")
    ).scalar_one()
    if legacy_activity_count:
        bind.execute(sa.text("DELETE FROM training_week_activities WHERE activity_type='support_ticket'"))
        for week_number, scenario_key in CURRICULUM_SCENARIOS.items():
            week = bind.execute(sa.text("SELECT id FROM training_weeks WHERE week_number=:week_number"), {"week_number": week_number}).first()
            if week is None:
                continue
            stable_id = f"week-{week_number}-service_desk_scenario-{scenario_key}"
            existing = bind.execute(sa.text("SELECT id FROM training_week_activities WHERE stable_id=:stable_id"), {"stable_id": stable_id}).first()
            if existing is not None:
                continue
            next_order = bind.execute(sa.text("SELECT COALESCE(MAX(display_order), 0) + 1 FROM training_week_activities WHERE training_week_id=:week_id"), {"week_id": week[0]}).scalar_one()
            bind.execute(sa.text("""
                INSERT INTO training_week_activities
                (stable_id, training_week_id, activity_type, content_ref, display_order, is_required, estimated_minutes, prerequisite_mode, metadata_json)
                VALUES (:stable_id, :week_id, 'service_desk_scenario', :content_ref, :display_order, 1, 30, 'soft', :metadata_json)
            """), {"stable_id": stable_id, "week_id": week[0], "content_ref": scenario_key, "display_order": next_order, "metadata_json": json.dumps({})})


def downgrade():
    # Data-retention policy intentionally does not recreate retired curriculum
    # dependencies or delete immutable Service Desk versions.
    pass
