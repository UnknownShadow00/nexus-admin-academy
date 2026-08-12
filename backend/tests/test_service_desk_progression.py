from datetime import datetime, timezone

import pytest

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.routers.admin_students import StudentCreateRequest, create_student
from app.routers.service_desk import router
from app.services.service_desk_progression import SERVICE_DESK_PACKS
from conftest import auth_headers, make_client, make_student


client = make_client(router)


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
                        assigned_by="test",
                    )
                )
    db.commit()
    return scenarios


def _pass(db, student, scenario_and_version):
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
        lambda _student_id, _db: 0,
    )


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
    }
    assert progression.json()["next_pack"] == {
        "key": "desktop-support",
        "name": "Desktop Support",
        "required_week": 3,
        "required_passes": 2,
        "source_pack_name": "Starter Support",
        "source_pack_passes": 0,
        "reason": "Reach Week 3 and complete 2 Starter Support cases successfully.",
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
        lambda student_id, _db: 3 if student_id == first.id else 0,
    )
    for stable_key in SERVICE_DESK_PACKS[0].scenario_keys[:2]:
        _pass(db, first, scenarios[stable_key])

    first_rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(first)
    ).json()
    second_rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(second)
    ).json()

    assert len(first_rows) == 8
    assert len([row for row in first_rows if row["queue_type"] == "assigned"]) == 4
    assert len([row for row in first_rows if row["queue_type"] == "practice"]) == 4
    assert [row["scenario"]["stable_key"] for row in second_rows] == list(
        SERVICE_DESK_PACKS[0].scenario_keys
    )


def test_pack_requires_both_curriculum_week_and_prior_successes(monkeypatch, db):
    student = make_student(db, "dual-gate")
    scenarios = _seed_pack_assignments(db, student)
    week = {"value": 0}
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
    assert len(after_week) == 8
    assert {
        row["scenario"]["stable_key"]
        for row in after_week
        if row["queue_type"] == "assigned"
    } == set(SERVICE_DESK_PACKS[1].scenario_keys)


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

    response = client.post(
        f"/api/service-desk/assignments/{_assignment_id(db, student, scenario)}/attempts",
        headers=auth_headers(student),
    )
    assert response.status_code == 201
    assert response.json()["attempt_number"] == 2
