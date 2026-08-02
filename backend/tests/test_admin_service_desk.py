import hashlib
import json

from app.models.service_desk import ServiceDeskAssignment, ServiceDeskAttemptGrade, ServiceDeskScenario
from app.routers import admin_service_desk, service_desk
from conftest import auth_headers, make_client, make_student

from test_service_desk_attempts import setup_assignment, start


def admin_headers(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "service-desk-admin")
    return {"X-Admin-Key": "service-desk-admin"}


def test_admin_auth_listing_filter_pagination_and_timeline(db, monkeypatch):
    headers = admin_headers(monkeypatch); student = make_student(db); assignment = setup_assignment(db, student)
    student_client = make_client(service_desk.router); started = start(student_client, student, assignment)
    event = {"idempotency_key": "timeline", "event_type": "click", "tool": "browser", "payload": {}, "resulting_state": {"step": 1}, "success": True}
    student_client.post(f"/api/service-desk/attempts/{started.json()['id']}/events", headers=auth_headers(student), json=event)
    admin_client = make_client(admin_service_desk.router)
    assert admin_client.get("/api/admin/service-desk/attempts", headers=headers, params={"student_id": student.id, "limit": 1}).json()[0]["student_email"] == student.email
    detail = admin_client.get(f"/api/admin/service-desk/attempts/{started.json()['id']}", headers=headers)
    assert detail.status_code == 200 and detail.json()["events"][0]["sequence_number"] == 1


def test_admin_assignment_duplicate_versions_and_publish(db, monkeypatch):
    headers = admin_headers(monkeypatch); student = make_student(db); scenario = ServiceDeskScenario(stable_key="admin-scenario", title="Admin scenario", category="service_desk", difficulty=1); db.add(scenario); db.commit(); db.refresh(scenario)
    client = make_client(admin_service_desk.router)
    assignment = {"student_id": student.id, "scenario_id": scenario.id, "mode": "learning"}
    assert client.post("/api/admin/service-desk/assignments", headers=headers, json=assignment).status_code == 201
    assert client.post("/api/admin/service-desk/assignments", headers=headers, json=assignment).status_code == 409
    definition = {"nodes": [{"id": "start"}]}; version = client.post(f"/api/admin/service-desk/scenarios/{scenario.id}/versions", headers=headers, json={"definition_json": definition})
    assert version.status_code == 201 and version.json()["definition_hash"] == hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()
    assert client.post(f"/api/admin/service-desk/scenarios/{scenario.id}/versions", headers=headers, json={"definition_json": definition}).status_code == 409
    published = client.post(f"/api/admin/service-desk/scenarios/{scenario.id}/versions/{version.json()['id']}/publish", headers=headers)
    assert published.status_code == 200
    assert client.post(f"/api/admin/service-desk/scenarios/{scenario.id}/versions/{version.json()['id']}/publish", headers=headers).status_code == 409


def test_feedback_requires_grade_then_succeeds(db, monkeypatch):
    headers = admin_headers(monkeypatch); student = make_student(db); assignment = setup_assignment(db, student)
    student_client = make_client(service_desk.router); attempt = start(student_client, student, assignment).json(); admin_client = make_client(admin_service_desk.router)
    path = f"/api/admin/service-desk/attempts/{attempt['id']}/feedback"
    assert admin_client.post(path, headers=headers, json={"mentor_feedback": "wait"}).status_code == 404
    student_client.post(f"/api/service-desk/attempts/{attempt['id']}/events", headers=auth_headers(student), json={"idempotency_key":"close","event_type":"ticket.close","tool":"ticket","payload":{"verifiedResolved":True,"resolutionNote":"ok"},"resulting_state":{},"success":True})
    student_client.post(f"/api/service-desk/attempts/{attempt['id']}/complete", headers=auth_headers(student), json={"idempotency_key":"c"})
    response = admin_client.post(path, headers=headers, json={"mentor_feedback": "Nice work"})
    assert response.status_code == 200 and response.json()["mentor_feedback"] == "Nice work"
