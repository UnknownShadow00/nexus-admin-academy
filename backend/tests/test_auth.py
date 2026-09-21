from pathlib import Path

from fastapi import APIRouter, Depends

from conftest import auth_headers, make_client, make_student
from app.routers.auth import router
from app.routers.study_tracker import router as study_tracker_router
from app.services.auth_service import get_current_student, verify_password

protected_router = APIRouter()


@protected_router.get("/protected")
def protected(_=Depends(get_current_student)):
    return {"allowed": True}

client = make_client(router, protected_router, study_tracker_router)


def test_login_success(db):
    student = make_student(db, username="alice", password="secret99")
    res = client.post("/auth/login", json={"username": "alice", "password": "secret99"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["student_id"] == student.id
    assert "student_session=" in res.headers.get("set-cookie", "")

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["student_id"] == student.id


def test_login_wrong_password(db):
    make_student(db, username="bob", password="correct")
    res = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert res.status_code == 401


def test_login_unknown_user(db):
    res = client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert res.status_code == 401


def test_existing_student_is_not_forced_to_change_password(db):
    student = make_student(db, username="existing", password="ExistingPass123!")

    response = client.post(
        "/auth/login",
        json={"username": "existing", "password": "ExistingPass123!"},
    )

    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    assert student.must_change_password is False
    assert client.get("/protected").status_code == 200


def test_forced_password_change_blocks_bypass_and_rotates_session(db):
    student = make_student(db, username="fresh", password="TemporaryPass123!")
    student.must_change_password = True
    db.commit()

    login = client.post(
        "/auth/login",
        json={"username": "fresh", "password": "TemporaryPass123!"},
    )
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True
    assert "has_unlocked_capstones" not in login.json()
    temporary_token = login.json()["access_token"]

    current = client.get("/auth/me")
    assert current.status_code == 200
    assert current.json()["data"]["must_change_password"] is True
    assert "a_plus_progress_pct" not in current.json()["data"]
    assert client.get("/auth/authorize").status_code == 403

    blocked = client.get("/protected")
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    tracker_bypass = client.get("/api/study-tracker/curriculum")
    assert tracker_bypass.status_code == 403
    assert tracker_bypass.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    mismatch = client.post(
        "/auth/change-password",
        json={"new_password": "NewPermanentPass123!", "confirm_password": "DifferentPass123!"},
    )
    assert mismatch.status_code == 400

    weak = client.post(
        "/auth/change-password",
        json={"new_password": "short", "confirm_password": "short"},
    )
    assert weak.status_code == 400

    too_long = client.post(
        "/auth/change-password",
        json={"new_password": "x" * 73, "confirm_password": "x" * 73},
    )
    assert too_long.status_code == 400

    unchanged = client.post(
        "/auth/change-password",
        json={"new_password": "TemporaryPass123!", "confirm_password": "TemporaryPass123!"},
    )
    assert unchanged.status_code == 400

    changed = client.post(
        "/auth/change-password",
        json={"new_password": "NewPermanentPass123!", "confirm_password": "NewPermanentPass123!"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert changed.json()["has_unlocked_capstones"] is False
    assert "a_plus_progress_pct" in changed.json()
    assert changed.json()["access_token"] != temporary_token
    assert "student_session=" in changed.headers.get("set-cookie", "")

    db.refresh(student)
    assert student.must_change_password is False
    assert student.auth_version == 1
    assert verify_password("NewPermanentPass123!", student.password_hash)
    assert not verify_password("TemporaryPass123!", student.password_hash)

    stale = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {temporary_token}"},
    )
    assert stale.status_code == 401
    assert client.get("/protected").status_code == 200
    assert client.get("/auth/authorize").status_code == 204


def test_service_desk_nginx_auth_uses_password_gate():
    repository_root = Path(__file__).resolve().parents[2]
    for relative_path in ("frontend/nginx.conf", "frontend/nginx.host.conf"):
        config = (repository_root / relative_path).read_text()
        auth_location = config.split("location = /_service_desk_auth", 1)[1].split("}", 1)[0]
        assert "/auth/authorize" in auth_location
        assert "/auth/me" not in auth_location
        assert "error_page 403 = @service_desk_password_change;" in config


def test_change_password_requires_confirmation_and_authentication(db):
    response = client.post(
        "/auth/change-password",
        json={"new_password": "NewPermanentPass123!", "confirm_password": "NewPermanentPass123!"},
    )
    assert response.status_code == 401

    student = make_student(db, username="already-onboarded", password="ExistingPass123!")
    response = client.post(
        "/auth/change-password",
        headers=auth_headers(student),
        json={"new_password": "NewPermanentPass123!", "confirm_password": "NewPermanentPass123!"},
    )
    assert response.status_code == 403
