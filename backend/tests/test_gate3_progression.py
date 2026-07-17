"""Gate 3 (Support Technician II → Network Support Technician) tests.

Exercises the min_cli_labs pack_prefix path against real CliLab/CliLabAttempt
rows, plus the networking mastery, ticket-difficulty, and flag requirements.
"""
from datetime import datetime, timezone

from conftest import make_student
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.mastery import StudentDomainMastery
from app.models.progression import PromotionGate, Role
from app.models.ticket import Ticket, TicketSubmission
from app.services.progression_service import check_promotion_eligibility

GATE3 = [
    ("min_completed_lessons", {"module_codes": ["MOD-009"]}),
    ("min_mastery_by_domain", {"thresholds": {"2.0": 75}}),
    ("min_verified_tickets_by_difficulty", {"thresholds": {"3": 2, "4": 1}}),
    ("min_cli_labs", {"min_completed": 3, "pack_prefix": "dev-sw-"}),
    ("no_unresolved_flags", {}),
]


def _seed(db):
    role = Role(name="Network Support Technician", rank_order=4, description="test")
    db.add(role)
    db.flush()
    for rt, cfg in GATE3:
        db.add(PromotionGate(role_id=role.id, requirement_type=rt, requirement_config=cfg))
    module = Module(code="MOD-009", title="Addressing", module_order=10)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="IPv4", lesson_order=1, status="published")
    t3a = Ticket(title="vlan ticket", description="d", difficulty=3, week_number=10)
    t3b = Ticket(title="trunk ticket", description="d", difficulty=3, week_number=11)
    t4 = Ticket(title="relay ticket", description="d", difficulty=4, week_number=11)
    # switching pack labs (match prefix) + a non-matching pack lab
    sw_labs = [CliLab(id=f"dev-sw-act-{i:02d}", title=f"sw{i}", compartment_id="learn-switching",
                      vendor_id="cisco", content={}) for i in (1, 2, 3)]
    nf_lab = CliLab(id="dev-nf-arp-001", title="nf", compartment_id="network-foundations",
                    vendor_id="cisco", content={})
    db.add_all([lesson, t3a, t3b, t4, nf_lab, *sw_labs])
    db.commit()
    return role, lesson, [t3a, t3b, t4], sw_labs, nf_lab


def _fulfill(db, student, lesson, tickets, sw_labs, nf_lab, sw_count=3):
    db.add(StudentLessonNote(student_id=student.id, lesson_id=lesson.id, content="n"))
    db.add(StudentDomainMastery(student_id=student.id, domain_id="2.0", mastery_percent=80))
    for t in tickets:
        db.add(TicketSubmission(student_id=student.id, ticket_id=t.id, writeup="w",
                                status="passed", final_score=8, xp_awarded=30))
    for lab in sw_labs[:sw_count]:
        db.add(CliLabAttempt(student_id=student.id, lab_id=lab.id,
                             completed_at=datetime.now(timezone.utc)))
    # a completed non-switching lab that must NOT count toward the dev-sw- prefix
    db.add(CliLabAttempt(student_id=student.id, lab_id=nf_lab.id,
                         completed_at=datetime.now(timezone.utc)))
    db.commit()


def test_gate3_full_pass(db):
    role, lesson, tickets, sw, nf = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, tickets, sw, nf)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]


def test_gate3_prefix_excludes_other_packs(db):
    """Only dev-sw- labs count; the network-foundations lab must not satisfy it."""
    role, lesson, tickets, sw, nf = _seed(db)
    student = make_student(db)
    # complete only 2 switching labs + the nf lab (nf must not count → 2 < 3)
    _fulfill(db, student, lesson, tickets, sw, nf, sw_count=2)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    missing = [r["type"] for r in result["requirements_missing"]]
    assert "min_cli_labs" in missing


def test_gate3_fails_low_networking_mastery(db):
    role, lesson, tickets, sw, nf = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, tickets, sw, nf)
    db.query(StudentDomainMastery).filter_by(student_id=student.id).first().mastery_percent = 60
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "min_mastery_by_domain" in [r["type"] for r in result["requirements_missing"]]


def test_gate3_fails_missing_difficulty4(db):
    role, lesson, tickets, sw, nf = _seed(db)
    student = make_student(db)
    _fulfill(db, student, lesson, tickets, sw, nf)
    sub = (db.query(TicketSubmission).join(Ticket)
           .filter(Ticket.difficulty == 4, TicketSubmission.student_id == student.id).first())
    db.delete(sub)
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "min_verified_tickets_by_difficulty" in [r["type"] for r in result["requirements_missing"]]
