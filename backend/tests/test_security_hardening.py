"""Regression coverage for the scoped CSRF, header, cookie, and upload hardening."""
import io

import pytest
from fastapi.testclient import TestClient

from conftest import auth_headers, make_client, make_student
from app.config import load_env
from app.database import get_db
from app.models.evidence import EvidenceArtifact
from app.models.login_streak import LoginStreak
from app.routers.evidence import router as evidence_router
from app.routers.admin_session import router as admin_session_router
from app.routers.admin_students import router as admin_students_router
from app.routers.auth import router as auth_router
from app.routers.students import router as students_router
from app.routers.tickets import router as tickets_router
from app.services.auth_service import STUDENT_SESSION_COOKIE, create_access_token


auth_client = make_client(auth_router)
admin_client = make_client(admin_session_router)
tickets_client = make_client(tickets_router)
students_client = make_client(students_router)
admin_students_client = make_client(admin_students_router)
evidence_client = make_client(evidence_router)


def _admin_env(monkeypatch):
    load_env.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "security-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "security-password")
    monkeypatch.setenv("ADMIN_API_KEY", "security-api-key")
    load_env()


@pytest.fixture()
def main_client(db):
    from app.main import create_app

    app = create_app()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    client.close()


@pytest.mark.parametrize("secure_cookie", ["false", "true"])
def test_student_login_cookie_is_always_samesite_lax(db, monkeypatch, secure_cookie):
    import app.routers.auth as auth_module
    import app.routers.capstones as capstones_module

    monkeypatch.setenv("COOKIE_SECURE", secure_cookie)
    monkeypatch.setattr(auth_module, "get_a_plus_progress", lambda *_: {})
    monkeypatch.setattr(capstones_module, "has_unlocked_capstones", lambda *_: False)
    make_student(db, username=f"cookie-{secure_cookie}", password="pass123")

    response = auth_client.post(
        "/auth/login", json={"username": f"cookie-{secure_cookie}", "password": "pass123"}
    )

    assert response.status_code == 200
    assert "samesite=lax" in response.headers["set-cookie"].lower()


@pytest.mark.parametrize("secure_cookie", ["false", "true"])
def test_admin_login_cookie_is_always_samesite_lax(monkeypatch, secure_cookie):
    _admin_env(monkeypatch)
    monkeypatch.setenv("COOKIE_SECURE", secure_cookie)

    response = admin_client.post(
        "/api/admin/session/login",
        json={"username": "security-admin", "password": "security-password"},
    )

    assert response.status_code == 200
    assert "samesite=lax" in response.headers["set-cookie"].lower()


def test_csrf_allows_trusted_student_origin_and_rejects_foreign_or_missing(db, main_client):
    student = make_student(db, username="csrf-student", password="pass123")
    token = create_access_token({"sub": str(student.id), "name": student.name, "email": student.email or ""})
    main_client.cookies.set(STUDENT_SESSION_COOKIE, token)

    allowed = main_client.post("/auth/logout", headers={"Origin": "http://testserver"})
    assert allowed.status_code == 200

    main_client.cookies.set(STUDENT_SESSION_COOKIE, token)
    rejected = main_client.post("/auth/logout", headers={"Origin": "https://evil.example"})
    assert rejected.status_code == 403
    assert rejected.json()["code"] == "CSRF_REJECTED"

    missing = main_client.post("/auth/logout")
    assert missing.status_code == 403


def test_csrf_allows_trusted_admin_origin_and_skips_cookie_free_requests(monkeypatch, main_client):
    _admin_env(monkeypatch)
    login = main_client.post(
        "/api/admin/session/login",
        json={"username": "security-admin", "password": "security-password"},
        headers={"Origin": "https://evil.example"},
    )
    assert login.status_code == 200  # no cookie existed before this request

    allowed = main_client.post("/api/admin/session/logout", headers={"Origin": "http://testserver"})
    assert allowed.status_code == 200

    cookie_free_login = TestClient(main_client.app).post(
        "/api/admin/session/login",
        json={"username": "security-admin", "password": "security-password"},
        headers={"Origin": "https://evil.example"},
    )
    assert cookie_free_login.status_code == 200


def test_csrf_does_not_block_get_requests_with_session_cookie(db, main_client):
    student = make_student(db, username="csrf-get", password="pass123")
    token = create_access_token({"sub": str(student.id), "name": student.name, "email": student.email or ""})
    main_client.cookies.set(STUDENT_SESSION_COOKIE, token)

    response = main_client.get("/health", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200


def test_security_headers_and_https_only_hsts(main_client):
    plain = main_client.get("/api/admin/session/status")
    assert plain.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in plain.headers["content-security-policy"]
    assert plain.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert plain.headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in plain.headers

    https = main_client.get("/api/admin/session/status", headers={"X-Forwarded-Proto": "https"})
    assert https.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"


def test_examcompass_cors_is_limited_to_api_key_bookmarklet(main_client):
    origin = "https://www.examcompass.com"
    preflight = main_client.options(
        "/api/admin/quiz/bookmarklet-import",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                 "Access-Control-Request-Headers": "X-Admin-Key, Content-Type"},
    )
    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in preflight.headers

    unrelated = main_client.get("/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in unrelated.headers


def test_evidence_download_requires_owner_or_mentor(db, monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    owner = make_student(db, username="evidence-owner")
    other = make_student(db, username="evidence-other")
    mentor = make_student(db, username="evidence-mentor")
    mentor.is_mentor = True
    path = tmp_path / "private.png"
    path.write_bytes(b"private-evidence")
    artifact = EvidenceArtifact(
        student_id=owner.id,
        submission_type="ticket",
        submission_id=1,
        artifact_type="screenshot",
        storage_key=path.name,
        original_filename="proof.png",
        mime_type="image/png",
        metadata_json={},
        validation_status="valid",
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    url = f"/api/evidence/{artifact.id}/file"
    assert evidence_client.get(url, headers=auth_headers(other)).status_code == 403
    owner_response = evidence_client.get(url, headers=auth_headers(owner))
    assert owner_response.status_code == 200
    assert owner_response.content == b"private-evidence"
    assert evidence_client.get(url, headers=auth_headers(mentor)).status_code == 200

    # Lab uploads intentionally live in UPLOAD_DIR/screenshots while ticket and
    # orientation evidence use UPLOAD_DIR directly.
    lab_dir = tmp_path / "screenshots"
    lab_dir.mkdir()
    lab_path = lab_dir / "lab-private.png"
    lab_path.write_bytes(b"private-lab-evidence")
    lab_artifact = EvidenceArtifact(
        student_id=owner.id,
        submission_type="lab",
        submission_id=2,
        artifact_type="screenshot",
        storage_key=lab_path.name,
        original_filename="lab-proof.png",
        mime_type="image/png",
        metadata_json={},
        validation_status="valid",
    )
    db.add(lab_artifact)
    db.commit()
    db.refresh(lab_artifact)
    lab_response = evidence_client.get(
        f"/api/evidence/{lab_artifact.id}/file", headers=auth_headers(owner)
    )
    assert lab_response.status_code == 200
    assert lab_response.content == b"private-lab-evidence"


def test_mentor_stats_review_does_not_create_student_presence_state(db):
    student = make_student(db, username="stats-owner")
    mentor = make_student(db, username="stats-mentor")
    mentor.is_mentor = True
    db.commit()

    response = students_client.get(
        f"/api/students/{student.id}/stats", headers=auth_headers(mentor)
    )

    assert response.status_code == 200
    assert response.json()["streak"] == 0
    assert db.query(LoginStreak).filter_by(student_id=student.id).first() is None


def test_ticket_upload_is_bounded_and_valid_upload_still_succeeds(db, monkeypatch, tmp_path):
    import app.routers.tickets as ticket_module

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(ticket_module, "MAX_FILE_SIZE", 1024)
    monkeypatch.setattr(ticket_module, "MAX_TOTAL_UPLOAD_BYTES", 2048)
    student = make_student(db, username="upload-student")

    too_large = tickets_client.post(
        "/api/tickets/uploads",
        files=[("files", ("large.png", io.BytesIO(b"x" * 1025), "image/png"))],
        headers=auth_headers(student),
    )
    assert too_large.status_code == 400
    assert too_large.json()["detail"] == "File too large (max 5MB)"

    valid = tickets_client.post(
        "/api/tickets/uploads",
        files=[("files", ("small.png", io.BytesIO(b"small"), "image/png"))],
        headers=auth_headers(student),
    )
    assert valid.status_code == 200, valid.text
    assert len(valid.json()["data"]["files"]) == 1


def test_ticket_upload_rejects_combined_size_and_invalid_mime(db, monkeypatch, tmp_path):
    import app.routers.tickets as ticket_module

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(ticket_module, "MAX_FILE_SIZE", 1024)
    monkeypatch.setattr(ticket_module, "MAX_TOTAL_UPLOAD_BYTES", 10)
    student = make_student(db, username="aggregate-student")

    aggregate = tickets_client.post(
        "/api/tickets/uploads",
        files=[
            ("files", ("one.png", io.BytesIO(b"123456"), "image/png")),
            ("files", ("two.png", io.BytesIO(b"123456"), "image/png")),
        ],
        headers=auth_headers(student),
    )
    assert aggregate.status_code == 400
    assert aggregate.json()["detail"] == "Too many files or combined size too large"

    invalid_mime = tickets_client.post(
        "/api/tickets/uploads",
        files=[("files", ("fake.png", io.BytesIO(b"nope"), "text/plain"))],
        headers=auth_headers(student),
    )
    assert invalid_mime.status_code == 400
    assert invalid_mime.json()["detail"] == "Invalid MIME type"


# ------------------------------------------------------------ student roster privacy

def test_student_roster_leaks_no_email_or_private_fields(db):
    make_student(db, username="roster-a", password="pass123")
    make_student(db, username="roster-b", password="pass123")
    viewer = make_student(db, username="roster-viewer", password="pass123")

    response = students_client.get("/api/students", headers=auth_headers(viewer))

    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 3
    for row in rows:
        assert set(row.keys()) == {"id", "name"}
    assert "@test.local" not in response.text
    assert "email" not in response.text.lower()


def test_admin_overview_still_returns_email_for_account_management(monkeypatch, db):
    _admin_env(monkeypatch)
    make_student(db, username="managed-student", password="pass123")

    response = admin_students_client.get(
        "/api/admin/students/overview",
        headers={"X-Admin-Key": "security-api-key"},
    )

    assert response.status_code == 200
    rows = response.json()["data"]
    assert any(row["username"] == "managed-student" and row["email"] for row in rows)
