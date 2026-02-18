from app.database import SessionLocal
from app.models.progression import Role

ROLES = [
    {"name": "L1 Help Desk", "rank_order": 1, "description": "Entry support analyst"},
    {"name": "L2 Help Desk", "rank_order": 2, "description": "Escalation support analyst"},
    {"name": "Junior SysAdmin", "rank_order": 3, "description": "Junior systems administrator"},
    {"name": "SysAdmin", "rank_order": 4, "description": "Systems administrator"},
    {"name": "Network Admin", "rank_order": 5, "description": "Network administrator"},
]


def seed_roles() -> None:
    db = SessionLocal()
    try:
        for role in ROLES:
            exists = db.query(Role).filter(Role.name == role["name"]).first()
            if exists:
                continue
            db.add(Role(**role))
        db.commit()
        print("Seeded roles")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()

