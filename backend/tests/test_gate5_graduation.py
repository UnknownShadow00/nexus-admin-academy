"""Gate 5 (graduation → Junior Infrastructure Administrator) tests."""
from datetime import datetime, timezone

from conftest import make_student
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.progression import PromotionGate, Role
from app.models.ticket import Ticket, TicketSubmission
from app.services.progression_service import check_promotion_eligibility

GATE5 = [
    ("min_completed_lessons", {"module_codes": ["MOD-023"]}),
    ("min_verified_tickets_by_difficulty", {"thresholds": {"4": 1, "5": 1}}),
    ("practical_checkpoint", {"ticket_title": "Multi-Ticket Simulation 3", "max_hints": 1, "min_score": 7}),
    ("no_unresolved_flags", {}),
]


def _seed(db):
    role = Role(name="Junior Infrastructure Administrator", rank_order=6, description="grad")
    db.add(role)
    db.flush()
    for rt, cfg in GATE5:
        db.add(PromotionGate(role_id=role.id, requirement_type=rt, requirement_config=cfg))
    module = Module(code="MOD-023", title="Integrated Ops", module_order=24)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="Mixed Queue", lesson_order=1, status="published")
    t4 = Ticket(title="entra lockout", description="d", difficulty=4, week_number=21)
    sim3 = Ticket(title="Multi-Ticket Simulation 3 — the infrastructure shift",
                  description="d", difficulty=5, week_number=23)
    db.add_all([lesson, t4, sim3])
    db.commit()
    return role, lesson, t4, sim3


def _fulfill(db, student, lesson, t4, sim3, sim_hints=1, sim_score=8):
    db.add(StudentLessonProgress(student_id=student.id, lesson_id=lesson.id, completed_at=datetime.now(timezone.utc)))
    db.add(TicketSubmission(student_id=student.id, ticket_id=t4.id, writeup="w",
                            status="passed", final_score=8, xp_awarded=40))
    db.add(TicketSubmission(student_id=student.id, ticket_id=sim3.id, writeup="w",
                            status="passed", final_score=sim_score, xp_awarded=80,
                            hints_used=sim_hints))
    db.commit()


def test_gate5_graduation_pass(db):
    role, lesson, t4, sim3 = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, t4, sim3)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]


def test_gate5_sim3_substring_title_matches(db):
    """The config's short title must match the seeded ticket's full title."""
    role, lesson, t4, sim3 = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, t4, sim3, sim_hints=0, sim_score=9)
    result = check_promotion_eligibility(student.id, role.id, db)
    missing = [r["type"] for r in result.get("requirements_missing", [])]
    assert "practical_checkpoint" not in missing


def test_gate5_fails_on_sim3_hints(db):
    role, lesson, t4, sim3 = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, t4, sim3, sim_hints=2, sim_score=10)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "practical_checkpoint" in [r["type"] for r in result["requirements_missing"]]
