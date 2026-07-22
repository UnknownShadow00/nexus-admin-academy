from conftest import make_client, make_student
from app.routers.auth import router

client = make_client(router)


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
