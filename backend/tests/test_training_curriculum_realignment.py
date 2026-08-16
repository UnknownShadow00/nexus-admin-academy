from app.models.cli_lab import CliLab
from app.models.lab import LabTemplate
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.training_curriculum_seed import (
    sync_initial_training_activities,
    sync_weeks_1_4_practice_realignment,
)
from app.services.training_service import validate_training_curriculum


def _add_week(db, number):
    week = TrainingWeek(
        week_number=number,
        display_order=number,
        title=f"Week {number}",
        learning_goals=[],
        is_active=True,
        requires_previous_week=False if number == 1 else True,
    )
    db.add(week)
    return week


def _add_lab(db, lab_id, title, week_number, lab_type="guided"):
    db.add(
        LabTemplate(
            id=lab_id,
            title=title,
            description="Legacy lab",
            lab_type=lab_type,
            difficulty=2,
            week_number=week_number,
            estimated_minutes=30,
            is_published=True,
            environment_requirements={},
            success_criteria={"tasks": ["Legacy task"]},
            required_evidence={"screenshot": True},
            hints={},
        )
    )


def test_weeks_1_4_practice_realignment_converges_seeded_curriculum(db):
    for number in range(1, 5):
        _add_week(db, number)
    _add_lab(db, 1, "IP Addressing & Subnetting Practice", 2)
    _add_lab(db, 2, "Troubleshoot a Network Connectivity Scenario", 3, "scenario")
    _add_lab(db, 3, "Windows Command-Line Diagnostics", 4)
    _add_lab(db, 4, "Hardware Component Identification", 1, "identification")
    _add_lab(db, 5, "AD Break-Fix: locked and misplaced account on a live domain", 15, "break_fix")
    db.add(CliLab(id="meet-cli-001", compartment_id="meet-the-cli", vendor_id="cisco", title="Meet the CLI", order_index=1, content={}))
    scenarios = [
        ServiceDeskScenario(stable_key=key, title=key, category="service_desk", difficulty=1, status="active")
        for key in ("locked-user-account", "inc2404", "password-reset", "mfa-reset")
    ]
    db.add_all(scenarios)
    db.flush()
    db.add_all(
        [
            ServiceDeskScenarioVersion(
                scenario_id=scenario.id,
                version_number=1,
                definition_json={},
                definition_hash=f"test-{scenario.id}",
                validation_status="valid",
                status="published",
            )
            for scenario in scenarios
        ]
    )
    db.commit()

    initial = sync_initial_training_activities(db)

    # sync_initial_training_activities already seeds each week's Apply step
    # (a service_desk_scenario activity) ahead of the realignment run, as in
    # the real curriculum — reuse those to assert Practice lands *before*
    # Apply, not just appended after it.
    apply_activities = {
        number: db.query(TrainingWeekActivity)
        .filter_by(training_week_id=week.id, activity_type="service_desk_scenario")
        .one()
        for number, week in ((n, db.query(TrainingWeek).filter_by(week_number=n).one()) for n in range(1, 5))
    }

    first = sync_weeks_1_4_practice_realignment(db)

    assert initial["created"] == 9
    assert first["created_templates"] == 1
    assert db.get(LabTemplate, 1).is_published is False
    assert db.get(LabTemplate, 2).is_published is False
    assert (db.get(LabTemplate, 3).week_number, db.get(LabTemplate, 3).lab_type) == (3, "structured_diagnostic")
    assert (db.get(LabTemplate, 4).week_number, db.get(LabTemplate, 4).lab_type) == (2, "structured_identification")
    assert (db.get(LabTemplate, 5).week_number, db.get(LabTemplate, 5).lab_type, db.get(LabTemplate, 5).is_published) == (15, "break_fix", True)

    weeks = {week.week_number: week for week in db.query(TrainingWeek).all()}
    guided_refs = {
        number: [activity.content_ref for activity in db.query(TrainingWeekActivity).filter_by(training_week_id=week.id, activity_type="guided_lab").all()]
        for number, week in weeks.items()
    }
    triage = db.query(LabTemplate).filter_by(title="Prioritize the Queue").one()
    assert guided_refs[1] == []
    assert guided_refs[2] == ["4"]
    assert guided_refs[3] == ["3"]
    assert guided_refs[4] == [str(triage.id)]
    assert db.query(TrainingWeekActivity).filter_by(activity_type="networking_lab", content_ref="meet-cli-001").one().is_required is True
    assert validate_training_curriculum(db)["valid"] is True

    # Practice must be sequenced before Apply, not appended after it.
    for number in (2, 3, 4):
        week = weeks[number]
        practice = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id, activity_type="guided_lab").one()
        apply_activity = db.get(TrainingWeekActivity, apply_activities[number].id)
        assert practice.display_order < apply_activity.display_order, f"week {number} Practice must precede Apply"

    second = sync_weeks_1_4_practice_realignment(db)
    assert second == {
        "updated_templates": 0,
        "created_templates": 0,
        "moved_activities": 0,
        "created_activities": 0,
        "deleted_activities": 0,
        "updated_cli_activities": 0,
        "skipped": False,
    }
