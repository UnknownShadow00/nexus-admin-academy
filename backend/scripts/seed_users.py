import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, get_db
from app.models.student import Student
from app.services.auth_service import hash_password


ACCOUNTS = [
    {"username": "mentor1", "name": "Mentor One", "email": "mentor1@nexus.local", "password_env": "SEED_PASSWORD_MENTOR1", "is_mentor": True},
    {"username": "student1", "name": "Student One", "email": "student1@nexus.local", "password_env": "SEED_PASSWORD_STUDENT1", "is_mentor": False},
    {"username": "student2", "name": "Student Two", "email": "student2@nexus.local", "password_env": "SEED_PASSWORD_STUDENT2", "is_mentor": False},
    {"username": "student3", "name": "Student Three", "email": "student3@nexus.local", "password_env": "SEED_PASSWORD_STUDENT3", "is_mentor": False},
    {"username": "student4", "name": "Student Four", "email": "student4@nexus.local", "password_env": "SEED_PASSWORD_STUDENT4", "is_mentor": False},
    {"username": "student5", "name": "Student Five", "email": "student5@nexus.local", "password_env": "SEED_PASSWORD_STUDENT5", "is_mentor": False},
]


def load_passwords() -> dict[str, str]:
    passwords = {}
    missing = []
    for account in ACCOUNTS:
        env_name = account["password_env"]
        value = os.getenv(env_name, "").strip()
        if value:
            passwords[account["username"]] = value
        else:
            missing.append(env_name)
    if missing:
        print("Refusing to seed: missing password environment variables:")
        for env_name in missing:
            print(f"  - {env_name}")
        sys.exit(1)
    return passwords


def main() -> None:
    passwords = load_passwords()
    _ = engine
    db = next(get_db())
    try:
        for account in ACCOUNTS:
            existing = db.query(Student).filter(Student.username == account["username"]).first()
            if existing:
                print(f"Skipped: {account['username']}")
                continue

            db.add(
                Student(
                    username=account["username"],
                    name=account["name"],
                    email=account["email"],
                    password_hash=hash_password(passwords[account["username"]]),
                    is_mentor=account["is_mentor"],
                )
            )
            db.commit()
            print(f"Created: {account['username']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
