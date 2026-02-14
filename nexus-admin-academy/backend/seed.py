from app.database import SessionLocal
from app.models.student import Student


def seed_students() -> None:
    students = [
        ("Alex", "alex@example.com"),
        ("Jordan", "jordan@example.com"),
        ("Sam", "sam@example.com"),
        ("Taylor", "taylor@example.com"),
        ("Riley", "riley@example.com"),
    ]

    db = SessionLocal()
    try:
        existing = {row.email for row in db.query(Student).all()}
        for name, email in students:
            if email in existing:
                continue
            db.add(Student(name=name, email=email, total_xp=0))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_students()
    print("Seed complete")
