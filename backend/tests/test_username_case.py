"""Case-insensitive usernames + env-driven account seeding.

Usernames: Shak / shak / SHAK are one account; case-variant duplicates are
rejected; display capitalization is preserved. Passwords stay case-sensitive.
Seeding: passwords come from SEED_PASSWORD_* env vars, legacy accounts are
renamed in place (same id → linked data preserved), and the script is
idempotent.
"""

import importlib.util
import os
import sys

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from conftest import make_client, make_student
from app.models.student import Student
from app.models.xp_ledger import XPLedger
from app.routers.auth import router as auth_router
from app.services.auth_service import normalize_username

client = make_client(auth_router)

_SEED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "seed_users.py")
_spec = importlib.util.spec_from_file_location("seed_users", _SEED_PATH)
seed_users = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_users)

SEED_ENV = {
    "SEED_PASSWORD_MENTOR": "test-Mentor-pw",
    "SEED_PASSWORD_SHAK": "test-Shak-pw",
    "SEED_PASSWORD_RAKIB": "test-Rakib-pw",
    "SEED_PASSWORD_AHMED": "test-Ahmed-pw",
    "SEED_PASSWORD_EMRAN": "test-Emran-pw",
    "SEED_PASSWORD_WALO": "test-Walo-pw",
    "SEED_PASSWORD_HUDAYFA": "test-Hudayfa-pw",
}


@pytest.fixture()
def seed_env(monkeypatch):
    for key, value in SEED_ENV.items():
        monkeypatch.setenv(key, value)


def test_normalize_username():
    assert normalize_username("  Shak ") == "shak"
    assert normalize_username("SHAK") == "shak"
    assert normalize_username(None) == ""


def test_case_variants_login_same_account(db):
    student = make_student(db, username="Shak", password="Right1")
    for variant in ("Shak", "shak", "SHAK", "sHaK", "  shak  "):
        res = client.post("/auth/login", json={"username": variant, "password": "Right1"})
        assert res.status_code == 200, f"variant {variant!r} failed"
        assert res.json()["student_id"] == student.id


def test_display_capitalization_preserved(db):
    make_student(db, username="Shak", password="Right1")
    stored = db.query(Student).filter(func.lower(Student.username) == "shak").one()
    assert stored.username == "Shak"


def test_password_stays_case_sensitive(db):
    make_student(db, username="Shak", password="Right1")
    for wrong in ("right1", "RIGHT1", "Right1 "):
        res = client.post("/auth/login", json={"username": "shak", "password": wrong})
        assert res.status_code == 401, f"wrong-case password {wrong!r} was accepted"


def test_duplicate_username_differing_case_rejected(db):
    make_student(db, username="Shak", password="Right1")
    db.add(
        Student(
            name="Imposter",
            email="imposter@test.local",
            username="shak",
            password_hash="x",
            total_xp=0,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_one_users_password_rejected_for_another(db):
    make_student(db, username="Shak", password="ShakOnly1")
    make_student(db, username="Rakib", password="RakibOnly1")
    res = client.post("/auth/login", json={"username": "Rakib", "password": "ShakOnly1"})
    assert res.status_code == 401


def test_seed_creates_all_accounts_and_each_can_log_in(db, seed_env):
    seed_users.seed(db)
    assert db.query(Student).count() == 7
    for account in seed_users.ACCOUNTS:
        res = client.post(
            "/auth/login",
            json={"username": account["username"].lower(), "password": SEED_ENV[account["env"]]},
        )
        assert res.status_code == 200, f"{account['username']} cannot log in"
        assert res.json()["is_mentor"] is account["is_mentor"]


def test_seed_is_idempotent(db, seed_env):
    seed_users.seed(db)
    hashes_first = {s.username: s.password_hash for s in db.query(Student).all()}
    seed_users.seed(db)
    assert db.query(Student).count() == 7
    hashes_second = {s.username: s.password_hash for s in db.query(Student).all()}
    assert hashes_first == hashes_second  # second run touches nothing


def test_seed_renames_legacy_accounts_preserving_data(db, seed_env):
    legacy = make_student(db, username="student1", password="old-nexus123")
    db.add(XPLedger(student_id=legacy.id, source_type="quiz", source_id=1, delta=150, description="pre-rename XP"))
    legacy.total_xp = 150
    db.commit()
    legacy_id = legacy.id

    seed_users.seed(db)

    renamed = db.query(Student).filter(func.lower(Student.username) == "shak").one()
    assert renamed.id == legacy_id
    assert renamed.username == "Shak"
    assert renamed.total_xp == 150
    assert db.query(XPLedger).filter(XPLedger.student_id == legacy_id).count() == 1

    # new credentials work, old ones are dead
    ok = client.post("/auth/login", json={"username": "shak", "password": SEED_ENV["SEED_PASSWORD_SHAK"]})
    assert ok.status_code == 200
    old_name = client.post("/auth/login", json={"username": "student1", "password": SEED_ENV["SEED_PASSWORD_SHAK"]})
    assert old_name.status_code == 401
    old_pw = client.post("/auth/login", json={"username": "shak", "password": "old-nexus123"})
    assert old_pw.status_code == 401


def test_seed_refuses_missing_password_env(db, monkeypatch):
    for key in SEED_ENV:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(SystemExit):
        seed_users.seed(db)
