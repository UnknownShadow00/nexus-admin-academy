"""Seed the fixed cohort accounts.

Passwords come from backend/.env (SEED_PASSWORD_<NAME>) — never hardcoded
here; the script refuses to run with any of them missing. Legacy accounts
(mentor1, student1..student5) are renamed in place, so each student's id —
and therefore every FK-linked row (XP, quiz attempts, ticket submissions,
evidence, streaks...) — is preserved. Idempotent: safe to run repeatedly.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.config import load_env
from app.database import engine, get_db
from app.models.student import Student
from app.services.auth_service import hash_password, normalize_username

# username = preferred display capitalization (login is case-insensitive).
ACCOUNTS = [
    {"username": "Mentor", "env": "SEED_PASSWORD_MENTOR", "is_mentor": True, "legacy": "mentor1"},
    {"username": "Shak", "env": "SEED_PASSWORD_SHAK", "is_mentor": False, "legacy": "student1"},
    {"username": "Rakib", "env": "SEED_PASSWORD_RAKIB", "is_mentor": False, "legacy": "student2"},
    {"username": "Ahmed", "env": "SEED_PASSWORD_AHMED", "is_mentor": False, "legacy": "student3"},
    {"username": "Emran", "env": "SEED_PASSWORD_EMRAN", "is_mentor": False, "legacy": "student4"},
    {"username": "Walo", "env": "SEED_PASSWORD_WALO", "is_mentor": False, "legacy": "student5"},
    {"username": "Hudayfa", "env": "SEED_PASSWORD_HUDAYFA", "is_mentor": False, "legacy": None},
]


def _password_for(account: dict) -> str:
    value = os.getenv(account["env"])
    if not value:
        sys.exit(f"ERROR: {account['env']} is not set in backend/.env — refusing to seed without a real password.")
    return value


def _rank_one_role_id(db) -> int | None:
    from app.models.progression import Role

    role = db.query(Role).filter(Role.rank_order == 1).first()
    return role.id if role else None


def seed(db) -> None:
    for account in ACCOUNTS:
        target = normalize_username(account["username"])

        existing = db.query(Student).filter(func.lower(Student.username) == target).first()
        if existing:
            print(f"Skipped (exists): {account['username']}")
            continue

        legacy = None
        if account["legacy"]:
            legacy = db.query(Student).filter(func.lower(Student.username) == account["legacy"]).first()
        if legacy:
            legacy.username = account["username"]
            legacy.name = account["username"]
            legacy.email = f"{target}@nexus.local"
            legacy.password_hash = hash_password(_password_for(account))
            legacy.is_mentor = account["is_mentor"]
            db.commit()
            print(f"Renamed: {account['legacy']} -> {account['username']} (id={legacy.id}, linked data preserved)")
            continue

        student = Student(
            username=account["username"],
            name=account["username"],
            email=f"{target}@nexus.local",
            password_hash=hash_password(_password_for(account)),
            is_mentor=account["is_mentor"],
            total_xp=0,
            current_role_id=_rank_one_role_id(db),
        )
        db.add(student)
        db.commit()
        print(f"Created: {account['username']}")


def main() -> None:
    load_env()
    _ = engine
    db = next(get_db())
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
