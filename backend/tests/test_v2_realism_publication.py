"""Fresh V2 loads publish and bind the current evidence-based scenarios."""

import seed_v2_foundation
from app.models.certification import CertificationModule, ModuleAssessment
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.routers import service_desk
from app.services.service_desk_realism import fixture_catalog
from app.services.v2_curriculum_service import launch_service_desk
from conftest import auth_headers, enroll_v2, make_client, make_student


def _current_version(db, stable_key):
    scenario = db.query(ServiceDeskScenario).filter_by(
        stable_key=stable_key.lower()
    ).one()
    published = db.query(ServiceDeskScenarioVersion).filter_by(
        scenario_id=scenario.id, status="published"
    ).all()
    assert len(published) == 1
    return scenario, published[0]


def test_fresh_v2_load_publishes_all_ten_current_realistic_versions(db):
    seed_v2_foundation.run(db)
    fixtures = fixture_catalog()
    assert set(fixtures) == {f"INC25{number:02d}" for number in range(1, 11)}

    current_ids = {}
    for ticket_id, fixture in fixtures.items():
        scenario, version = _current_version(db, ticket_id)
        current_ids[scenario.id] = version.id
        assert version.definition_json["simulation_fixture"] == fixture
        assert version.definition_json["objective_catalog_version"].startswith("realism-v")

    assessments = db.query(ModuleAssessment).filter_by(
        assessment_role="service_desk", active=True
    ).all()
    assert assessments
    for assessment in assessments:
        if assessment.service_desk_scenario_id is None:
            continue
        scenario = db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
        if scenario is None or scenario.stable_key.upper() not in fixtures:
            continue
        assert assessment.service_desk_scenario_id in current_ids
        _, version = _current_version(db, scenario.stable_key)
        assert scenario.id == assessment.service_desk_scenario_id
        assert version.id == current_ids[scenario.id]
        assert version.definition_json["simulation_fixture"] == fixtures[
            scenario.stable_key.upper()
        ]


def test_converted_catalog_is_practice_and_only_inc2503_is_a_v2_module_assessment(db):
    """Do not manufacture required module bindings for the optional practice catalog."""
    seed_v2_foundation.run(db)
    converted = {f"inc25{number:02d}" for number in range(1, 11)}
    bound = {
        scenario.stable_key
        for assessment, scenario in (
            db.query(ModuleAssessment, ServiceDeskScenario)
            .join(
                ServiceDeskScenario,
                ServiceDeskScenario.id == ModuleAssessment.service_desk_scenario_id,
            )
            .filter(
                ModuleAssessment.assessment_role == "service_desk",
                ModuleAssessment.active.is_(True),
                ServiceDeskScenario.stable_key.in_(converted),
            )
            .all()
        )
    }
    assert bound == {"inc2503"}


def test_reload_disables_obsolete_published_version_and_is_idempotent(db):
    seed_v2_foundation.run(db)
    scenario, current = _current_version(db, "INC2501")
    obsolete = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=current.version_number + 1,
        definition_json={"id": "INC2501", "steps": ["generic-wizard"]},
        definition_hash="obsolete-inc2501".ljust(64, "0"),
        validation_status="valid",
        status="published",
        published_by="test",
    )
    db.add(obsolete)
    db.commit()

    seed_v2_foundation.run(db)
    _, republished = _current_version(db, "INC2501")
    db.refresh(obsolete)
    assert republished.id == current.id
    assert obsolete.status == "disabled"

    census = db.query(ServiceDeskScenarioVersion).count()
    seed_v2_foundation.run(db)
    assert db.query(ServiceDeskScenarioVersion).count() == census


def test_reload_reactivates_curated_scenario_before_publication(db):
    seed_v2_foundation.run(db)
    scenario, _ = _current_version(db, "INC2501")
    scenario.status = "disabled"
    db.commit()

    seed_v2_foundation.run(db)

    db.refresh(scenario)
    assert scenario.status == "active"


def test_every_converted_curriculum_assignment_launches_its_current_version(
    db, monkeypatch
):
    seed_v2_foundation.run(db)
    fixtures = fixture_catalog()
    student = make_student(db, username="realism-publication-launch")
    enroll_v2(monkeypatch, student)
    client = make_client(service_desk.router)
    rows = (
        db.query(ModuleAssessment, CertificationModule, ServiceDeskScenario)
        .join(
            CertificationModule,
            CertificationModule.id == ModuleAssessment.certification_module_id,
        )
        .join(
            ServiceDeskScenario,
            ServiceDeskScenario.id == ModuleAssessment.service_desk_scenario_id,
        )
        .filter(
            ModuleAssessment.assessment_role == "service_desk",
            ModuleAssessment.active.is_(True),
            ServiceDeskScenario.stable_key.in_(
                {ticket.lower() for ticket in fixtures}
            ),
        )
        .all()
    )
    assert rows
    for assessment, module, scenario in rows:
        launch_service_desk(
            db, student.id, module.module_key, assessment.assessment_key
        )
        assignment = db.query(ServiceDeskAssignment).filter_by(
            student_id=student.id, scenario_id=scenario.id, mode="learning"
        ).one()
        started = client.post(
            f"/api/service-desk/assignments/{assignment.id}/attempts",
            headers=auth_headers(student),
        )
        assert started.status_code == 201, started.text
        attempt = db.get(ServiceDeskAttempt, started.json()["id"])
        _, current = _current_version(db, scenario.stable_key)
        assert attempt.scenario_version_id == current.id
        assert current.definition_json["simulation_fixture"] == fixtures[
            scenario.stable_key.upper()
        ]

    launched_ticket_ids = set()
    for ticket_id in sorted(fixtures):
        scenario, current = _current_version(db, ticket_id)
        assignment = ServiceDeskAssignment(
            student_id=student.id,
            scenario_id=scenario.id,
            mode="simulation",
            maximum_attempts=3,
            assigned_by="publication-rehearsal",
        )
        db.add(assignment)
        db.commit()
        started = client.post(
            f"/api/service-desk/assignments/{assignment.id}/attempts",
            headers=auth_headers(student),
        )
        assert started.status_code == 201, started.text
        attempt = db.get(ServiceDeskAttempt, started.json()["id"])
        assert attempt.scenario_version_id == current.id
        launched_ticket_ids.add(ticket_id)
    assert launched_ticket_ids == set(fixtures)
