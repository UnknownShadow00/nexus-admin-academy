"""Align the first two beginner modules with their required assessments.

Revision ID: 0070_beginner_content_ux_polish
Revises: 0069_merge_v2_beginner_heads
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = "0070_beginner_content_ux_polish"
down_revision = "0069_merge_v2_beginner_heads"
branch_labels = None
depends_on = None

_INTRO_TITLES = ("Anatomy of a Good Ticket", "Meet the Command Line")
_POLISHED_ESTIMATES = {
    "Anatomy of a Good Ticket": 25,
    "Meet the Command Line": 10,
    "Storage: Symptoms Before Specs": 45,
    "RAM, CPU, Power, and POST": 45,
    "BIOS/UEFI and Boot Order": 30,
}
_LEGACY_ESTIMATES = {
    "Anatomy of a Good Ticket": 60,
    "Meet the Command Line": 90,
    "Storage: Symptoms Before Specs": 90,
    "RAM, CPU, Power, and POST": 90,
    "BIOS/UEFI and Boot Order": 60,
}


def _connection():
    return op.get_bind()


def _set_intro_requirement(required: bool) -> None:
    connection = _connection()
    lesson_ids = [
        str(row.id)
        for row in connection.execute(
            sa.text("SELECT id FROM lessons WHERE title IN (:first, :second)"),
            {"first": _INTRO_TITLES[0], "second": _INTRO_TITLES[1]},
        )
    ]
    if not lesson_ids:
        return
    connection.execute(
        sa.text(
            "UPDATE training_week_activities "
            "SET is_required = :required "
            "WHERE activity_type = 'lesson' AND content_ref IN (:first, :second)"
        ),
        {
            "required": required,
            "first": lesson_ids[0],
            "second": lesson_ids[-1],
        },
    )


def _set_estimates(estimates: dict[str, int], module_hours: tuple[int, int]) -> None:
    connection = _connection()
    for title, minutes in estimates.items():
        connection.execute(
            sa.text("UPDATE lessons SET estimated_minutes = :minutes WHERE title = :title"),
            {"minutes": minutes, "title": title},
        )
        connection.execute(
            sa.text(
                "UPDATE training_week_activities SET estimated_minutes = :minutes "
                "WHERE activity_type = 'lesson' AND content_ref IN "
                "(SELECT CAST(id AS TEXT) FROM lessons WHERE title = :title)"
            ),
            {"minutes": minutes, "title": title},
        )
    connection.execute(
        sa.text(
            "UPDATE modules SET estimated_hours = CASE code "
            "WHEN 'MOD-001' THEN :week1 WHEN 'MOD-002' THEN :week2 ELSE estimated_hours END "
            "WHERE code IN ('MOD-001', 'MOD-002')"
        ),
        {"week1": module_hours[0], "week2": module_hours[1]},
    )


def _move_week_two_quiz(*, after_power: bool) -> None:
    connection = _connection()
    week_id = connection.execute(
        sa.text("SELECT id FROM training_weeks WHERE week_number = 2")
    ).scalar_one_or_none()
    if week_id is None:
        return
    rows = list(
        connection.execute(
            sa.text(
                "SELECT id, activity_type, content_ref, display_order, is_required "
                "FROM training_week_activities WHERE training_week_id = :week_id "
                "ORDER BY display_order, id"
            ),
            {"week_id": week_id},
        ).mappings()
    )
    quiz = next((row for row in rows if row["activity_type"] == "quiz" and row["is_required"]), None)
    power = next((row for row in rows if row["activity_type"] == "video" and row["content_ref"] == "44"), None)
    if quiz is None or power is None:
        return
    ordered = [row for row in rows if row["id"] != quiz["id"]]
    power_index = next(index for index, row in enumerate(ordered) if row["id"] == power["id"])
    ordered.insert(power_index + (1 if after_power else 0), quiz)
    if [row["id"] for row in ordered] == [row["id"] for row in rows]:
        return
    temporary_start = max(row["display_order"] for row in rows) + len(rows) + 1
    for offset, row in enumerate(rows):
        connection.execute(
            sa.text("UPDATE training_week_activities SET display_order = :position WHERE id = :id"),
            {"position": temporary_start + offset, "id": row["id"]},
        )
    for position, row in enumerate(ordered, start=1):
        connection.execute(
            sa.text("UPDATE training_week_activities SET display_order = :position WHERE id = :id"),
            {"position": position, "id": row["id"]},
        )


def _move_week_one_cli(*, before_ticket: bool) -> None:
    connection = _connection()
    week_id = connection.execute(
        sa.text("SELECT id FROM training_weeks WHERE week_number = 1")
    ).scalar_one_or_none()
    if week_id is None:
        return
    rows = list(
        connection.execute(
            sa.text(
                "SELECT id, activity_type, display_order FROM training_week_activities "
                "WHERE training_week_id = :week_id ORDER BY display_order, id"
            ),
            {"week_id": week_id},
        ).mappings()
    )
    cli = next((row for row in rows if row["activity_type"] == "networking_lab"), None)
    ticket = next((row for row in rows if row["activity_type"] == "service_desk_scenario"), None)
    if cli is None or ticket is None:
        return
    ordered = [row for row in rows if row["id"] != cli["id"]]
    ticket_index = next(index for index, row in enumerate(ordered) if row["id"] == ticket["id"])
    ordered.insert(ticket_index + (0 if before_ticket else 1), cli)
    if [row["id"] for row in ordered] == [row["id"] for row in rows]:
        return
    temporary_start = max(row["display_order"] for row in rows) + len(rows) + 1
    for offset, row in enumerate(rows):
        connection.execute(
            sa.text("UPDATE training_week_activities SET display_order = :position WHERE id = :id"),
            {"position": temporary_start + offset, "id": row["id"]},
        )
    for position, row in enumerate(ordered, start=1):
        connection.execute(
            sa.text("UPDATE training_week_activities SET display_order = :position WHERE id = :id"),
            {"position": position, "id": row["id"]},
        )


def upgrade() -> None:
    _set_intro_requirement(True)
    _set_estimates(_POLISHED_ESTIMATES, (2, 5))
    _move_week_two_quiz(after_power=True)
    _move_week_one_cli(before_ticket=True)


def downgrade() -> None:
    _move_week_one_cli(before_ticket=False)
    _move_week_two_quiz(after_power=False)
    _set_intro_requirement(False)
    _set_estimates(_LEGACY_ESTIMATES, (6, 14))
