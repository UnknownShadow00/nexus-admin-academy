from app.database import SessionLocal
from app.models.learning import Lesson, Module
from app.models.progression import MethodologyFramework, Role

MODULE_0 = {
    "code": "MOD-000",
    "title": "Troubleshooting Methodology",
    "description": "Learn systematic IT problem-solving and disciplined incident handling.",
    "difficulty_band": 1,
    "estimated_hours": 4,
    "unlock_threshold": 0,
    "module_order": 0,
    "lessons": [
        {
            "title": "CompTIA 6-Step Process",
            "summary": "Define, theorize, test, plan, verify, and document.",
            "outcomes": ["Can identify symptoms", "Can test theories", "Can verify fixes"],
            "lesson_order": 1,
            "estimated_minutes": 45,
        }
    ],
}

FRAMEWORK_STEPS = {
    "steps": [
        "Identify the problem",
        "Establish a theory of probable cause",
        "Test the theory",
        "Establish a plan of action and implement",
        "Verify functionality and implement preventive measures",
        "Document findings, actions, and outcomes",
    ]
}


def seed_module0() -> None:
    db = SessionLocal()
    try:
        module = db.query(Module).filter(Module.code == MODULE_0["code"]).first()
        if module is None:
            module = Module(
                code=MODULE_0["code"],
                title=MODULE_0["title"],
                description=MODULE_0["description"],
                difficulty_band=MODULE_0["difficulty_band"],
                estimated_hours=MODULE_0["estimated_hours"],
                unlock_threshold=MODULE_0["unlock_threshold"],
                module_order=MODULE_0["module_order"],
                active=True,
            )
            db.add(module)
            db.flush()

        for lesson_data in MODULE_0["lessons"]:
            lesson = (
                db.query(Lesson)
                .filter(Lesson.module_id == module.id, Lesson.lesson_order == lesson_data["lesson_order"])
                .first()
            )
            if lesson:
                continue
            db.add(
                Lesson(
                    module_id=module.id,
                    title=lesson_data["title"],
                    summary=lesson_data["summary"],
                    lesson_order=lesson_data["lesson_order"],
                    outcomes=lesson_data["outcomes"],
                    estimated_minutes=lesson_data["estimated_minutes"],
                    status="published",
                )
            )

        l1 = db.query(Role).filter(Role.rank_order == 1).first()
        framework = db.query(MethodologyFramework).filter(MethodologyFramework.name == "CompTIA 6-Step").first()
        if framework is None:
            db.add(
                MethodologyFramework(
                    name="CompTIA 6-Step",
                    description="Structured troubleshooting for support professionals",
                    steps=FRAMEWORK_STEPS,
                    required_for_role=l1.id if l1 else None,
                )
            )

        db.commit()
        print("Seeded module 0 and methodology framework")
    finally:
        db.close()


if __name__ == "__main__":
    seed_module0()

