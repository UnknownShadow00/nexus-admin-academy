"""Gate 4 (Network Support Technician → Junior Systems Technician) tests."""
from conftest import make_student
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.mastery import StudentDomainMastery
from app.models.progression import PromotionGate, Role
from app.models.ticket import Ticket, TicketSubmission
from app.services.progression_service import check_promotion_eligibility

GATE4 = [
    ("min_completed_lessons", {"module_codes": ["MOD-013"]}),
    ("min_mastery_by_domain", {"thresholds": {"3.0": 75}}),
    ("min_verified_tickets_by_difficulty", {"thresholds": {"3": 2, "4": 1}}),
    ("no_unresolved_flags", {}),
]


def _seed(db):
    role = Role(name="Junior Systems Technician", rank_order=5, description="test")
    db.add(role)
    db.flush()
    for rt, cfg in GATE4:
        db.add(PromotionGate(role_id=role.id, requirement_type=rt, requirement_config=cfg))
    module = Module(code="MOD-013", title="AD Foundations", module_order=14)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="AD", lesson_order=1, status="published")
    t3a = Ticket(title="onboarding", description="d", difficulty=3, week_number=13)
    t3b = Ticket(title="trust", description="d", difficulty=3, week_number=14)
    t4 = Ticket(title="gpo wrong ou", description="d", difficulty=4, week_number=15)
    db.add_all([lesson, t3a, t3b, t4])
    db.commit()
    return role, lesson, [t3a, t3b, t4]


def _fulfill(db, student, lesson, tickets):
    db.add(StudentLessonNote(student_id=student.id, lesson_id=lesson.id, content="n"))
    db.add(StudentDomainMastery(student_id=student.id, domain_id="3.0", mastery_percent=82))
    for t in tickets:
        db.add(TicketSubmission(student_id=student.id, ticket_id=t.id, writeup="w",
                                status="passed", final_score=8, xp_awarded=30))
    db.commit()


def test_gate4_full_pass(db):
    role, lesson, tickets = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, tickets)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]


def test_gate4_fails_missing_ad_lessons(db):
    role, lesson, tickets = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, tickets)
    db.query(StudentLessonNote).filter_by(student_id=student.id).delete()
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "min_completed_lessons" in [r["type"] for r in result["requirements_missing"]]


def test_gate4_fails_missing_difficulty4(db):
    role, lesson, tickets = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, tickets)
    sub = (db.query(TicketSubmission).join(Ticket)
           .filter(Ticket.difficulty == 4, TicketSubmission.student_id == student.id).first())
    db.delete(sub)
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "min_verified_tickets_by_difficulty" in [r["type"] for r in result["requirements_missing"]]
