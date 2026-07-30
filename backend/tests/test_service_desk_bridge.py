from app.models.squad_activity import SquadActivity
from app.models.xp_ledger import XPLedger
from app.routers import service_desk_bridge
from app.services.admin_auth import issue_admin_session, revoke_admin_session
from app.services.auth_service import STUDENT_SESSION_COOKIE, create_access_token
from conftest import auth_headers, make_client, make_student


def test_progress_events_are_recorded_and_summarized(db):
    student = make_student(db)
    client = make_client(service_desk_bridge.router)
    headers = auth_headers(student)

    ticket_response = client.post(
        "/api/service-desk/progress",
        headers=headers,
        json={
            "event_type": "ticket_resolved",
            "ticket_id": "ticket-123",
            "title": "Resolved locked account",
            "detail": "Verified the requester and restored access.",
            "xp_delta": 25,
        },
    )
    achievement_response = client.post(
        "/api/service-desk/progress",
        headers=headers,
        json={
            "event_type": "achievement_unlocked",
            "title": "Identity verifier",
            "xp_delta": 0,
        },
    )

    assert ticket_response.status_code == 204
    assert achievement_response.status_code == 204
    assert db.query(SquadActivity).filter_by(student_id=student.id).count() == 2
    assert db.query(XPLedger).filter_by(student_id=student.id, source_type="service_desk").count() == 1

    summary_response = client.get("/api/service-desk/progress-summary", headers=headers)

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["tickets_completed"] == 1
    assert summary["achievements_unlocked"] == 1
    assert summary["total_xp"] == 25
    assert [item["title"] for item in summary["recent_activity"]] == [
        "Identity verifier",
        "Resolved locked account",
    ]
    assert all(item["created_at"] for item in summary["recent_activity"])


def test_progress_endpoints_require_student_authentication():
    client = make_client(service_desk_bridge.router)

    assert client.post(
        "/api/service-desk/progress",
        json={"event_type": "ticket_resolved", "title": "Unauthorized event"},
    ).status_code == 401
    assert client.get("/api/service-desk/progress-summary").status_code == 401


def test_admin_check_accepts_api_key_or_active_admin_session(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "bridge-admin-key")
    client = make_client(service_desk_bridge.router)

    assert client.get("/api/service-desk/admin-check").json() == {"is_admin": False}
    assert client.get(
        "/api/service-desk/admin-check",
        headers={"X-Admin-Key": "bridge-admin-key"},
    ).json() == {"is_admin": True}
    assert client.get(
        "/api/service-desk/admin-check",
        headers={"X-Admin-Key": "wrong-key"},
    ).json() == {"is_admin": False}

    token = issue_admin_session()
    try:
        client.cookies.set("admin_session", token)
        assert client.get("/api/service-desk/admin-check").json() == {"is_admin": True}
    finally:
        revoke_admin_session(token)


def test_admin_authorize_requires_mentor_or_active_admin_session(db):
    student = make_student(db, username="not-a-mentor")
    mentor = make_student(db, username="mentor")
    mentor.is_mentor = True
    db.commit()
    client = make_client(service_desk_bridge.router)

    assert client.get("/api/service-desk/admin-authorize").status_code == 403

    student_token = create_access_token(
        {"sub": str(student.id), "name": student.name, "is_mentor": False}
    )
    client.cookies.set(STUDENT_SESSION_COOKIE, student_token)
    assert client.get("/api/service-desk/admin-authorize").status_code == 403

    mentor_token = create_access_token(
        {"sub": str(mentor.id), "name": mentor.name, "is_mentor": True}
    )
    client.cookies.set(STUDENT_SESSION_COOKIE, mentor_token)
    assert client.get("/api/service-desk/admin-authorize").status_code == 204

    client.cookies.clear()
    admin_token = issue_admin_session()
    try:
        client.cookies.set("admin_session", admin_token)
        assert client.get("/api/service-desk/admin-authorize").status_code == 204
    finally:
        revoke_admin_session(admin_token)
