from datetime import datetime, timezone

import pytest

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.routers.admin_students import StudentCreateRequest, create_student
from app.routers.service_desk import router
from app.services.service_desk_progression import SERVICE_DESK_PACKS
from app.services.training_curriculum_seed import SERVICE_DESK_WEEKS
from conftest import auth_headers, make_client, make_student
from seed import seed_service_desk_scenarios


client = make_client(router)


def test_weekly_service_desk_mapping_keeps_the_endpoint_security_case():
    assert SERVICE_DESK_WEEKS[7] == "inc2508"
    assert SERVICE_DESK_WEEKS[8] == "inc2407"


def test_foundational_prototypes_publish_as_current_immutable_versions_idempotently(db):
    stable_keys = ("locked-user-account", "password-reset", "mfa-reset")
    expected_ticket_ids = {
        "locked-user-account": "INC2511",
        "password-reset": "INC2512",
        "mfa-reset": "INC2513",
    }
    seed_service_desk_scenarios(db)
    db.commit()
    initial_versions = {
        key: db.query(ServiceDeskScenarioVersion)
        .join(ServiceDeskScenario)
        .filter(ServiceDeskScenario.stable_key == key)
        .count()
        for key in stable_keys
    }

    seed_service_desk_scenarios(db)
    db.commit()

    for key in stable_keys:
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=key).one()
        version = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id, status="published")
            .order_by(ServiceDeskScenarioVersion.version_number.desc())
            .first()
        )
        assert version.definition_json["id"] == expected_ticket_ids[key]
        assert version.definition_json["objective_catalog_version"] == "process-v3"
        assert scenario.difficulty == 1
        assert (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id)
            .count()
            == initial_versions[key]
        )


def _seed_pack_assignments(db, *students):
    scenarios = {}
    for pack in SERVICE_DESK_PACKS:
        for index, stable_key in enumerate(pack.scenario_keys):
            scenario = ServiceDeskScenario(
                stable_key=stable_key,
                title=f"Scenario {stable_key.upper()}",
                description="A realistic support request.",
                category="support",
                difficulty=min(3, index + 1),
                status="active",
            )
            db.add(scenario)
            db.flush()
            version = ServiceDeskScenarioVersion(
                scenario_id=scenario.id,
                version_number=1,
                definition_json={
                    "activity": [],
                    "assignedTo": None,
                    "category": "software",
                    "createdAt": "2026-08-12T09:00:00Z",
                    "description": {
                        "businessImpact": "One employee cannot complete assigned work.",
                        "issue": "The application stops during one repeatable task.",
                        "reportedByLine": "Submitted through the support portal.",
                        "troubleshooting": [],
                    },
                    "device": {
                        "assetTag": f"NX-{stable_key.upper()}",
                        "deviceName": "TEST-WS",
                        "kind": "desktop",
                        "operatingSystem": "Windows 11",
                        "state": "active",
                    },
                    "escalated": False,
                    "hints": [],
                    "id": stable_key.upper(),
                    "notes": [],
                    "priority": "medium",
                    "requester": {
                        "contact": "Support portal",
                        "department": "Operations",
                        "email": "requester@example.test",
                        "location": "Main office",
                        "name": "Test Requester",
                    },
                    "sla": {
                        "dueAt": "2026-08-12T14:00:00Z",
                        "target": "Respond within 4 hours",
                    },
                    "status": "open",
                    "suggestedTools": ["remote-desktop"],
                    "title": f"Scenario {stable_key.upper()}",
                },
                definition_hash=f"{stable_key:0<64}"[:64],
                validation_status="valid",
                status="published",
            )
            db.add(version)
            db.flush()
            scenarios[stable_key] = (scenario, version)
            for student in students:
                db.add(
                    ServiceDeskAssignment(
                        student_id=student.id,
                        scenario_id=scenario.id,
                        mode="simulation",
                        is_required=False,
                        assigned_by="seed",
                    )
                )
    db.commit()
    return scenarios


def _pass(db, student, scenario_and_version, *, experience_mode="assessment"):
    _, version = scenario_and_version
    attempt_number = (
        db.query(ServiceDeskAttempt)
        .filter_by(student_id=student.id, scenario_version_id=version.id)
        .count()
        + 1
    )
    db.add(
        ServiceDeskAttempt(
            student_id=student.id,
            scenario_version_id=version.id,
            mode="simulation",
            experience_mode=experience_mode,
            status="completed",
            current_state={},
            current_state_hash="a" * 64,
            state_version=1,
            attempt_number=attempt_number,
            completed_at=datetime.now(timezone.utc),
            score=90,
            passed=True,
        )
    )
    db.commit()


def test_guided_starter_pass_does_not_count_as_curriculum_mastery_or_pack_progress(
    monkeypatch, db
):
    student = make_student(db, "guided-is-not-mastery")
    scenarios = _seed_pack_assignments(db, student)
    _map_required_case(db, 3, "password-reset")
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 1,
    )
    _pass(db, student, scenarios["password-reset"], experience_mode="guided")

    listing = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    password = next(
        row for row in listing if row["scenario"]["stable_key"] == "password-reset"
    )
    assert password["experience_mode"] == "guided"
    assert password["guided_completed"] is True
    assert password["required_this_week"] is False
    assert password["queue_type"] != "practice"
    assert "suggestedTools" in password["latest_published_version"]["definition_json"]

    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 3,
    )
    listing = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    password = next(
        row for row in listing if row["scenario"]["stable_key"] == "password-reset"
    )
    assert password["experience_mode"] == "assessment"
    assert password["guided_completed"] is True
    assert password["required_this_week"] is True
    assert password["queue_type"] == "assigned"
    assert "hints" not in password["latest_published_version"]["definition_json"]
    assert (
        "suggestedTools" not in password["latest_published_version"]["definition_json"]
    )


def _map_required_case(db, week_number, stable_key):
    week = TrainingWeek(
        week_number=week_number,
        display_order=week_number,
        title=f"Week {week_number}",
        learning_goals=[],
    )
    db.add(week)
    db.flush()
    db.add(
        TrainingWeekActivity(
            stable_id=f"week-{week_number}-service-desk-{stable_key}",
            training_week_id=week.id,
            activity_type="service_desk_scenario",
            content_ref=stable_key,
            display_order=1,
            is_required=True,
            prerequisite_mode="soft",
            metadata_json={},
        )
    )
    db.commit()


def _assignment_id(db, student, scenario):
    return (
        db.query(ServiceDeskAssignment.id)
        .filter_by(student_id=student.id, scenario_id=scenario.id)
        .scalar()
    )


@pytest.fixture(autouse=True)
def _fresh_week(monkeypatch):
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 1,
    )


def test_week_zero_incomplete_hides_starter_cases_and_rejects_direct_start(
    monkeypatch, db
):
    student = make_student(db, "pre-shift")
    scenarios = _seed_pack_assignments(db, student)
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 0,
    )

    assignments = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    )
    progression = client.get(
        "/api/service-desk/progression", headers=auth_headers(student)
    )

    assert assignments.json() == []
    assert progression.json()["current_pack"] is None
    assert progression.json()["counts"] == {
        "available": 0,
        "in_progress": 0,
        "completed": 0,
        "practice": 0,
        "earlier": 0,
    }
    assert progression.json()["next_pack"]["key"] == "starter-support"
    assert progression.json()["next_pack"]["requirements"]["week"] == {
        "label": "Complete Week 0 training",
        "met": False,
    }
    for stable_key in SERVICE_DESK_PACKS[0].scenario_keys:
        starter_scenario, _ = scenarios[stable_key]
        direct = client.post(
            f"/api/service-desk/assignments/{_assignment_id(db, student, starter_scenario)}/attempts",
            headers=auth_headers(student),
        )
        assert direct.status_code == 403
        assert direct.json()["detail"]["code"] == "SERVICE_DESK_PACK_LOCKED"


def test_fresh_student_sees_only_four_starter_assignments_and_next_pack_preview(db):
    student = make_student(db, "fresh-service-desk")
    _seed_pack_assignments(db, student)

    assignments = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    )
    progression = client.get(
        "/api/service-desk/progression", headers=auth_headers(student)
    )

    assert assignments.status_code == 200
    assert [row["scenario"]["stable_key"] for row in assignments.json()] == list(
        SERVICE_DESK_PACKS[0].scenario_keys
    )
    assert {row["queue_type"] for row in assignments.json()} == {"assigned"}
    assert all(row["pack_name"] == "Starter Support" for row in assignments.json())
    assert progression.status_code == 200
    assert progression.json()["counts"] == {
        "available": 4,
        "in_progress": 0,
        "completed": 0,
        "practice": 0,
        "earlier": 0,
    }
    next_pack = progression.json()["next_pack"]
    assert next_pack["key"] == "desktop-support"
    assert next_pack["requirements"] == {
        "week": {"label": "Reach Week 3 training", "met": False},
        "passes": {
            "label": "Successfully resolve 2 Starter Support cases",
            "met": False,
            "completed": 0,
            "required": 2,
        },
    }


def test_new_student_accounts_receive_managed_assignment_inventory(db):
    _seed_pack_assignments(db)

    create_student(
        StudentCreateRequest(
            name="New Progression Student",
            email="new-progression@example.test",
            username="new-progression",
            password="SafeTestPassword!2026",
        ),
        db,
    )

    student = db.query(Student).filter_by(username="new-progression").one()
    assert db.query(ServiceDeskAssignment).filter(
        ServiceDeskAssignment.student_id == student.id
    ).count() == sum(len(pack.scenario_keys) for pack in SERVICE_DESK_PACKS)
    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    assert [row["scenario"]["stable_key"] for row in rows] == list(
        SERVICE_DESK_PACKS[0].scenario_keys
    )


def test_one_students_unlocks_never_change_another_students_queue(monkeypatch, db):
    first = make_student(db, "student-a")
    second = make_student(db, "student-b")
    scenarios = _seed_pack_assignments(db, first, second)
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda student_id, _db: 3 if student_id == first.id else 1,
    )
    for stable_key in SERVICE_DESK_PACKS[0].scenario_keys[:2]:
        _pass(db, first, scenarios[stable_key])

    first_rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(first)
    ).json()
    second_rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(second)
    ).json()

    assert len(first_rows) == 9
    assert len([row for row in first_rows if row["queue_type"] == "assigned"]) == 4
    assert len([row for row in first_rows if row["queue_type"] == "practice"]) == 2
    assert len([row for row in first_rows if row["queue_type"] == "earlier"]) == 3
    assert [row["scenario"]["stable_key"] for row in second_rows] == list(
        SERVICE_DESK_PACKS[0].scenario_keys
    )


def test_pack_requires_both_curriculum_week_and_prior_successes(monkeypatch, db):
    student = make_student(db, "dual-gate")
    scenarios = _seed_pack_assignments(db, student)
    week = {"value": 1}
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: week["value"],
    )
    for stable_key in SERVICE_DESK_PACKS[0].scenario_keys[:2]:
        _pass(db, student, scenarios[stable_key])

    before_week = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    assert len(before_week) == 4

    week["value"] = 3
    after_week = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    assert len(after_week) == 9
    assert {
        row["scenario"]["stable_key"]
        for row in after_week
        if row["queue_type"] == "assigned"
    } == set(SERVICE_DESK_PACKS[1].scenario_keys[:4])
    assert (
        next(
            row
            for row in after_week
            if row["scenario"]["stable_key"] == SERVICE_DESK_PACKS[1].scenario_keys[4]
        )["queue_type"]
        == "earlier"
    )


def test_direct_api_cannot_start_locked_assignment(monkeypatch, db):
    student = make_student(db, "direct-lock")
    scenarios = _seed_pack_assignments(db, student)
    locked_scenario, _ = scenarios[SERVICE_DESK_PACKS[1].scenario_keys[0]]
    assignment_id = _assignment_id(db, student, locked_scenario)

    response = client.post(
        f"/api/service-desk/assignments/{assignment_id}/attempts",
        headers=auth_headers(student),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "SERVICE_DESK_PACK_LOCKED"
    assert response.json()["detail"]["data"]["pack"] == "Desktop Support"


def test_completed_cases_move_to_practice_and_can_be_replayed(db):
    student = make_student(db, "practice-replay")
    scenarios = _seed_pack_assignments(db, student)
    stable_key = SERVICE_DESK_PACKS[0].scenario_keys[0]
    scenario, _ = scenarios[stable_key]
    _pass(db, student, scenarios[stable_key])

    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    row = next(item for item in rows if item["scenario"]["stable_key"] == stable_key)
    assert row["queue_type"] == "practice"
    assert row["most_recent_attempt"]["status"] == "completed"

    response = client.post(
        f"/api/service-desk/assignments/{_assignment_id(db, student, scenario)}/attempts",
        headers=auth_headers(student),
    )
    assert response.status_code == 201
    assert response.json()["attempt_number"] == 2


def test_unfinished_older_cases_are_earlier_never_practice(monkeypatch, db):
    student = make_student(db, "earlier-not-practice")
    scenarios = _seed_pack_assignments(db, student)
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 3,
    )
    for stable_key in SERVICE_DESK_PACKS[0].scenario_keys[:2]:
        _pass(db, student, scenarios[stable_key])

    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    starter_rows = [row for row in rows if row["pack_key"] == "starter-support"]
    assert {row["queue_type"] for row in starter_rows} == {"practice", "earlier"}
    assert len([row for row in starter_rows if row["queue_type"] == "practice"]) == 2
    assert len([row for row in starter_rows if row["queue_type"] == "earlier"]) == 2


def test_replaying_one_scenario_does_not_count_as_two_unique_passes(monkeypatch, db):
    student = make_student(db, "unique-pass-count")
    scenarios = _seed_pack_assignments(db, student)
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 3,
    )
    stable_key = SERVICE_DESK_PACKS[0].scenario_keys[0]
    _pass(db, student, scenarios[stable_key])
    _pass(db, student, scenarios[stable_key])

    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    assert {row["pack_key"] for row in rows} == {"starter-support"}
    progression = client.get(
        "/api/service-desk/progression", headers=auth_headers(student)
    ).json()
    assert progression["next_pack"]["source_pack_passes"] == 1


def test_instructor_assignment_unlocks_only_the_exact_case(monkeypatch, db):
    student = make_student(db, "mentor-override")
    scenarios = _seed_pack_assignments(db, student)
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 1,
    )
    future_key = SERVICE_DESK_PACKS[-1].scenario_keys[0]
    future_scenario, _ = scenarios[future_key]
    assignment = (
        db.query(ServiceDeskAssignment)
        .filter_by(student_id=student.id, scenario_id=future_scenario.id)
        .one()
    )
    assignment.assigned_by = "mentor.alex"
    db.commit()

    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    future_rows = [row for row in rows if row["pack_key"] == SERVICE_DESK_PACKS[-1].key]
    assert [row["scenario"]["stable_key"] for row in future_rows] == [future_key]
    assert future_rows[0]["queue_type"] == "assigned"
    assert (
        client.post(
            f"/api/service-desk/assignments/{assignment.id}/attempts",
            headers=auth_headers(student),
        ).status_code
        == 201
    )
    assert (
        client.get(
            "/api/service-desk/progression", headers=auth_headers(student)
        ).json()["current_pack"]["key"]
        == "starter-support"
    )

    _pass(db, student, scenarios[future_key])
    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    future_row = next(
        row for row in rows if row["scenario"]["stable_key"] == future_key
    )
    assert future_row["queue_type"] == "practice"
    assert (
        client.get(
            "/api/service-desk/progression", headers=auth_headers(student)
        ).json()["current_pack"]["key"]
        == "starter-support"
    )


def test_required_weekly_case_unlocks_exactly_without_unlocking_its_future_pack(
    monkeypatch, db
):
    student = make_student(db, "curriculum-exact-case")
    scenarios = _seed_pack_assignments(db, student)
    weekly_key = "inc2508"
    _map_required_case(db, 7, weekly_key)
    _map_required_case(db, 8, "inc2407")
    current_week = 7
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: current_week,
    )

    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    weekly_row = next(
        row for row in rows if row["scenario"]["stable_key"] == weekly_key
    )
    assert weekly_row["queue_type"] == "assigned"
    assert (
        client.get(
            "/api/service-desk/progression", headers=auth_headers(student)
        ).json()["current_pack"]["key"]
        == "starter-support"
    )

    unrelated_scenario, _ = scenarios["inc2506"]
    unrelated_assignment = (
        db.query(ServiceDeskAssignment)
        .filter_by(student_id=student.id, scenario_id=unrelated_scenario.id)
        .one()
    )
    assert (
        client.post(
            f"/api/service-desk/assignments/{unrelated_assignment.id}/attempts",
            headers=auth_headers(student),
        ).status_code
        == 403
    )

    current_week = 8
    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    weekly_row = next(
        row for row in rows if row["scenario"]["stable_key"] == weekly_key
    )
    assert weekly_row["queue_type"] == "earlier"
    assert (
        client.post(
            f"/api/service-desk/assignments/{weekly_row['id']}/attempts",
            headers=auth_headers(student),
        ).status_code
        == 201
    )
