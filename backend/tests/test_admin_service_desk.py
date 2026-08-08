import hashlib
import json

from app.models.service_desk import ServiceDeskScenario
from app.routers import admin_service_desk, service_desk
from conftest import auth_headers, make_client, make_student

from test_service_desk_attempts import setup_assignment, start


def admin_headers(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "service-desk-admin")
    return {"X-Admin-Key": "service-desk-admin"}


def valid_builder_definition(title="Printer queue stops"):
    return {
        "title": title,
        "slug": "printer-queue-stops",
        "category": "software",
        "priority": "medium",
        "difficulty": "easy",
        "pointValue": 100,
        "explanation": "Restarting the failed spooler restores the local print queue.",
        "description": {
            "issue": "Print jobs disappear from one workstation.",
            "reportedByLine": "Reported through the employee portal.",
            "businessImpact": "The requester cannot print an onboarding pack.",
            "troubleshooting": ["The printer works from a nearby workstation."],
        },
        "requester": {
            "name": "Avery Brooks",
            "department": "Finance",
            "email": "avery@example.test",
            "contact": "Ext. 10",
            "location": "North office",
        },
        "device": {
            "assetTag": "NX-1000",
            "deviceName": "FIN-LT-10",
            "kind": "laptop",
            "operatingSystem": "Windows 11",
            "state": "active",
        },
        "sla": {"dueAt": "2026-08-08T12:00:00Z", "target": "4 hours"},
        "initialWorldState": {
            "directoryOverlaySeeds": {},
            "assetOverlaySeeds": {},
            "chatMessageSeeds": [],
        },
        "objectives": [{
            "id": "restart-spooler",
            "order": 1,
            "description": "Restart the Print Spooler.",
            "pointValue": 100,
            "predicateType": "action_event_occurred",
            "predicateParams": {"actionType": "remote_desktop.restart_service"},
            "required": True,
        }],
        "requiredActions": [],
        "forbiddenActions": [],
        "hints": [
            {"id": "h1", "order": 1, "pointPenalty": 0, "text": "Find where the failure occurs."},
            {"id": "h2", "order": 2, "pointPenalty": 5, "text": "Inspect Windows services."},
            {"id": "h3", "order": 3, "pointPenalty": 5, "text": "Check the Print Spooler."},
        ],
    }


def test_admin_auth_listing_filter_pagination_and_timeline(db, monkeypatch):
    headers = admin_headers(monkeypatch)
    student = make_student(db)
    assignment = setup_assignment(db, student)
    student_client = make_client(service_desk.router)
    started = start(student_client, student, assignment)
    event = {
        "idempotency_key": "timeline",
        "event_type": "ticket.assign",
        "tool": "ticket",
        "payload": {"ticketId": "INC2401"},
        "resulting_state": {"step": 1},
        "success": True,
    }
    student_client.post(
        f"/api/service-desk/attempts/{started.json()['id']}/events",
        headers=auth_headers(student),
        json=event,
    )
    admin_client = make_client(admin_service_desk.router)
    assert (
        admin_client.get(
            "/api/admin/service-desk/attempts",
            headers=headers,
            params={"student_id": student.id, "limit": 1},
        ).json()[0]["student_email"]
        == student.email
    )
    detail = admin_client.get(
        f"/api/admin/service-desk/attempts/{started.json()['id']}", headers=headers
    )
    assert (
        detail.status_code == 200 and detail.json()["events"][0]["sequence_number"] == 1
    )


def test_admin_assignment_duplicate_versions_and_publish(db, monkeypatch):
    headers = admin_headers(monkeypatch)
    student = make_student(db)
    scenario = ServiceDeskScenario(
        stable_key="admin-scenario",
        title="Admin scenario",
        category="service_desk",
        difficulty=1,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    client = make_client(admin_service_desk.router)
    assignment = {
        "student_id": student.id,
        "scenario_id": scenario.id,
        "mode": "learning",
    }
    assert (
        client.post(
            "/api/admin/service-desk/assignments", headers=headers, json=assignment
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/admin/service-desk/assignments", headers=headers, json=assignment
        ).status_code
        == 409
    )
    definition = valid_builder_definition()
    version = client.post(
        f"/api/admin/service-desk/scenarios/{scenario.id}/versions",
        headers=headers,
        json={"definition_json": definition},
    )
    assert (
        version.status_code == 201
        and version.json()["definition_hash"]
        == hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()
    )
    assert (
        client.post(
            f"/api/admin/service-desk/scenarios/{scenario.id}/versions",
            headers=headers,
            json={"definition_json": definition},
        ).status_code
        == 409
    )
    published = client.post(
        f"/api/admin/service-desk/scenarios/{scenario.id}/versions/{version.json()['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert (
        client.post(
            f"/api/admin/service-desk/scenarios/{scenario.id}/versions/{version.json()['id']}/publish",
            headers=headers,
        ).status_code
        == 409
    )


def test_scenario_builder_create_save_reload_validate_publish_and_new_draft(db, monkeypatch):
    headers = admin_headers(monkeypatch)
    client = make_client(admin_service_desk.router)
    definition = valid_builder_definition()
    created = client.post(
        "/api/admin/service-desk/scenarios",
        headers=headers,
        json={
            "stable_key": definition["slug"],
            "title": definition["title"],
            "description": definition["description"]["issue"],
            "category": definition["category"],
            "difficulty": 1,
            "definition_json": definition,
        },
    )
    assert created.status_code == 201
    scenario = created.json()
    draft = scenario["versions"][0]
    assert draft["status"] == "draft" and draft["validation_status"] == "valid"

    edited = valid_builder_definition("Printer queue stops after sign-in")
    updated = client.put(
        f"/api/admin/service-desk/scenarios/{scenario['id']}/versions/{draft['id']}",
        headers=headers,
        json={
            "stable_key": edited["slug"],
            "title": edited["title"],
            "description": edited["description"]["issue"],
            "category": edited["category"],
            "difficulty": 1,
            "definition_json": edited,
        },
    )
    assert updated.status_code == 200

    reloaded = client.get(
        f"/api/admin/service-desk/scenarios/{scenario['id']}", headers=headers
    )
    assert reloaded.status_code == 200
    assert reloaded.json()["versions"][0]["definition_json"]["title"] == edited["title"]
    validation = client.post(
        f"/api/admin/service-desk/scenarios/{scenario['id']}/versions/{draft['id']}/validate",
        headers=headers,
    )
    assert validation.json() == {"valid": True, "errors": []}

    published = client.post(
        f"/api/admin/service-desk/scenarios/{scenario['id']}/versions/{draft['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert client.put(
        f"/api/admin/service-desk/scenarios/{scenario['id']}/versions/{draft['id']}",
        headers=headers,
        json={
            "stable_key": edited["slug"],
            "title": "Mutated history",
            "description": edited["description"]["issue"],
            "category": edited["category"],
            "difficulty": 1,
            "definition_json": {**edited, "title": "Mutated history"},
        },
    ).status_code == 409

    next_definition = {**edited, "title": "Printer queue stops again"}
    next_draft = client.post(
        f"/api/admin/service-desk/scenarios/{scenario['id']}/versions",
        headers=headers,
        json={"definition_json": next_definition},
    )
    assert next_draft.status_code == 201
    assert next_draft.json()["version_number"] == 2
    assert reloaded.json()["versions"][0]["definition_json"]["title"] == edited["title"]


def test_scenario_builder_allows_incomplete_draft_but_blocks_publish(db, monkeypatch):
    headers = admin_headers(monkeypatch)
    client = make_client(admin_service_desk.router)
    scenario = ServiceDeskScenario(
        stable_key="incomplete-draft",
        title="Incomplete draft",
        category="service_desk",
        difficulty=1,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    version = client.post(
        f"/api/admin/service-desk/scenarios/{scenario.id}/versions",
        headers=headers,
        json={"definition_json": {}},
    )
    assert version.status_code == 201
    assert version.json()["validation_status"] == "invalid"
    publish = client.post(
        f"/api/admin/service-desk/scenarios/{scenario.id}/versions/{version.json()['id']}/publish",
        headers=headers,
    )
    assert publish.status_code == 422
    assert publish.json()["detail"]["errors"]


def test_feedback_requires_grade_then_succeeds(db, monkeypatch):
    headers = admin_headers(monkeypatch)
    student = make_student(db)
    assignment = setup_assignment(db, student)
    student_client = make_client(service_desk.router)
    attempt = start(student_client, student, assignment).json()
    admin_client = make_client(admin_service_desk.router)
    path = f"/api/admin/service-desk/attempts/{attempt['id']}/feedback"
    assert (
        admin_client.post(
            path, headers=headers, json={"mentor_feedback": "wait"}
        ).status_code
        == 404
    )
    student_client.post(
        f"/api/service-desk/attempts/{attempt['id']}/events",
        headers=auth_headers(student),
        json={
            "idempotency_key": "close",
            "event_type": "ticket.close",
            "tool": "ticket",
            "payload": {"verifiedResolved": True, "resolutionNote": "ok"},
            "resulting_state": {},
            "success": True,
        },
    )
    student_client.post(
        f"/api/service-desk/attempts/{attempt['id']}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "c"},
    )
    response = admin_client.post(
        path, headers=headers, json={"mentor_feedback": "Nice work"}
    )
    assert (
        response.status_code == 200
        and response.json()["mentor_feedback"] == "Nice work"
    )
