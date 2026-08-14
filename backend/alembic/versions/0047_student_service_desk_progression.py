"""Align Service Desk cases with the learner progression.

Revision ID: 0047_student_service_desk_progression
Revises: 0046_archive_unreviewed_examcompass
Create Date: 2026-08-12

This is a non-destructive curriculum/content migration. Historical attempts,
grades, assignments, scenario versions, legacy tickets, and student progress
remain untouched. Revised scenario wording is published as a new immutable
version.
"""

from datetime import datetime, timezone
import hashlib
import json

from alembic import op
import sqlalchemy as sa

from app.services.service_desk_objectives import PROCESS_CATALOG_VERSION
from seed import (
    LABS,
    SERVICE_DESK_DIFFICULTY_BY_ID,
    SERVICE_DESK_DIFFICULTY_BY_PRIORITY,
    SERVICE_DESK_TICKET_FIXTURES,
    _current_service_desk_ticket_fixture,
)


revision = "0047_student_service_desk_progression"
down_revision = "0046_archive_unreviewed_examcompass"
branch_labels = None
depends_on = None


WEEK_SCENARIOS = {
    1: "locked-user-account",
    2: "inc2404",
    3: "password-reset",
    4: "mfa-reset",
    5: "inc2502",
    6: "inc2505",
    7: "inc2508",
    8: "inc2407",
    14: "inc2510",
}

PREVIOUS_WEEK_SCENARIOS = {
    1: "inc2407",
    2: "inc2503",
    3: "inc2501",
    4: "inc2509",
    5: "inc2502",
    6: "inc2505",
    7: "inc2508",
    8: "inc2504",
    14: "inc2510",
}

REVISED_SCENARIOS = {
    "INC2511",
    "INC2512",
    "INC2513",
    "INC2405",
    "INC2406",
    "INC2501",
    "INC2504",
}
REVISED_LABS = {
    "Troubleshoot a Network Connectivity Scenario",
    "Windows Command-Line Diagnostics",
}


def _publish_revised_scenarios(bind):
    now = datetime.now(timezone.utc).isoformat()
    for raw_ticket in SERVICE_DESK_TICKET_FIXTURES:
        ticket = _current_service_desk_ticket_fixture(raw_ticket)
        stable_key = ticket.get("stableKey", ticket["id"].lower())
        difficulty = SERVICE_DESK_DIFFICULTY_BY_ID.get(
            ticket["id"], SERVICE_DESK_DIFFICULTY_BY_PRIORITY[ticket["priority"]]
        )
        scenario = bind.execute(
            sa.text(
                "SELECT id FROM service_desk_scenarios WHERE stable_key=:stable_key"
            ),
            {"stable_key": stable_key},
        ).first()
        if scenario is None:
            scenario_id = bind.execute(
                sa.text(
                    """
                    INSERT INTO service_desk_scenarios
                    (stable_key, title, description, category, difficulty,
                     status, created_by)
                    VALUES (:stable_key, :title, :description, :category,
                            :difficulty, 'active', 'migration-0047')
                    RETURNING id
                    """
                ),
                {
                    "stable_key": stable_key,
                    "title": ticket["title"],
                    "description": (
                        f"{ticket['description']['issue']} "
                        f"{ticket['description']['businessImpact']}"
                    ),
                    "category": ticket["category"],
                    "difficulty": difficulty,
                },
            ).scalar_one()
            scenario = (scenario_id,)
        bind.execute(
            sa.text(
                """
                UPDATE service_desk_scenarios
                SET title=:title, description=:description, category=:category,
                    difficulty=:difficulty
                WHERE id=:scenario_id
                """
            ),
            {
                "scenario_id": scenario[0],
                "title": ticket["title"],
                "description": (
                    f"{ticket['description']['issue']} "
                    f"{ticket['description']['businessImpact']}"
                ),
                "category": ticket["category"],
                "difficulty": difficulty,
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO service_desk_assignments
                (student_id, scenario_id, mode, is_required, assigned_by)
                SELECT students.id, :scenario_id, 'simulation', 0,
                       'migration-0047'
                FROM students
                WHERE students.is_mentor = 0
                  AND NOT EXISTS (
                    SELECT 1 FROM service_desk_assignments existing
                    WHERE existing.student_id = students.id
                      AND existing.scenario_id = :scenario_id
                      AND existing.mode = 'simulation'
                  )
                """
            ),
            {"scenario_id": scenario[0]},
        )
        if ticket["id"] not in REVISED_SCENARIOS:
            continue
        definition = {**ticket, "objective_catalog_version": PROCESS_CATALOG_VERSION}
        definition_hash = hashlib.sha256(
            json.dumps(definition, sort_keys=True).encode("utf-8")
        ).hexdigest()
        exists = bind.execute(
            sa.text(
                """
                SELECT id FROM service_desk_scenario_versions
                WHERE scenario_id=:scenario_id AND definition_hash=:definition_hash
                """
            ),
            {"scenario_id": scenario[0], "definition_hash": definition_hash},
        ).first()
        if exists is not None:
            continue
        version_number = bind.execute(
            sa.text(
                """
                SELECT COALESCE(MAX(version_number), 0)
                FROM service_desk_scenario_versions WHERE scenario_id=:scenario_id
                """
            ),
            {"scenario_id": scenario[0]},
        ).scalar_one()
        bind.execute(
            sa.text(
                """
                INSERT INTO service_desk_scenario_versions
                (scenario_id, version_number, definition_json, definition_hash,
                 validation_status, status, published_at, published_by)
                VALUES (:scenario_id, :version_number, :definition_json,
                        :definition_hash, 'valid', 'published', :published_at,
                        'migration-0047')
                """
            ),
            {
                "scenario_id": scenario[0],
                "version_number": int(version_number) + 1,
                "definition_json": json.dumps(definition),
                "definition_hash": definition_hash,
                "published_at": now,
            },
        )


def _update_labs(bind):
    for lab in LABS:
        if lab["title"] not in REVISED_LABS:
            continue
        bind.execute(
            sa.text(
                """
                UPDATE lab_templates
                SET description=:description, setup_instructions=:setup,
                    success_criteria=:success, hints=:hints,
                    difficulty=:difficulty, estimated_minutes=:minutes
                WHERE title=:title
                """
            ),
            {
                "title": lab["title"],
                "description": lab["description"],
                "setup": lab["setup_instructions"],
                "success": json.dumps(lab["success_criteria"]),
                "hints": json.dumps(lab["hints"]),
                "difficulty": lab["difficulty"],
                "minutes": lab["estimated_minutes"],
            },
        )


def _map_weeks(bind, mapping):
    for week_number, scenario_key in mapping.items():
        bind.execute(
            sa.text(
                """
                UPDATE training_week_activities
                SET content_ref=:scenario_key
                WHERE activity_type='service_desk_scenario'
                  AND training_week_id=(
                    SELECT id FROM training_weeks WHERE week_number=:week_number
                  )
                """
            ),
            {"week_number": week_number, "scenario_key": scenario_key},
        )


def upgrade():
    bind = op.get_bind()
    _map_weeks(bind, WEEK_SCENARIOS)
    _publish_revised_scenarios(bind)
    _update_labs(bind)


def downgrade():
    _map_weeks(op.get_bind(), PREVIOUS_WEEK_SCENARIOS)
