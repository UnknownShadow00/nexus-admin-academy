from app.database import SessionLocal
from app.models.progression import PromotionGate, Role

GATES = [
    {
        "role": "L2 Help Desk",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"1": 10, "2": 8, "3": 5}},
    },
    {
        "role": "L2 Help Desk",
        "requirement_type": "min_mastery_by_domain",
        "config": {"thresholds": {"hardware": 70, "networking": 70}},
    },
    {
        "role": "Junior SysAdmin",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"2": 10, "3": 8, "4": 5}},
    },
]


def seed_promotion_gates() -> None:
    db = SessionLocal()
    try:
        for gate in GATES:
            role = db.query(Role).filter(Role.name == gate["role"]).first()
            if not role:
                continue

            exists = (
                db.query(PromotionGate)
                .filter(
                    PromotionGate.role_id == role.id,
                    PromotionGate.requirement_type == gate["requirement_type"],
                )
                .first()
            )
            if exists:
                exists.requirement_config = gate["config"]
                continue

            db.add(
                PromotionGate(
                    role_id=role.id,
                    requirement_type=gate["requirement_type"],
                    requirement_config=gate["config"],
                )
            )
        db.commit()
        print("Seeded promotion gates")
    finally:
        db.close()


if __name__ == "__main__":
    seed_promotion_gates()

