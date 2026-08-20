"""Gate 1 (Trainee → Support Technician I) evaluator tests — TB-02.

Proves the gate evaluates real stored student data and can both pass and
fail per requirement type: lessons, mastery, tickets, practical checkpoint,
CLI labs, and mentor flags.
"""
from conftest import make_student
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.mastery import StudentDomainMastery
from app.models.progression import PromotionGate, Role
from app.models.ticket import Ticket, TicketSubmission
from app.services.progression_service import check_promotion_eligibility

from datetime import datetime, timezone


GATE1 = [
    ("min_completed_lessons", {"module_codes": ["MOD-001"]}),
    ("min_mastery_by_domain", {"thresholds": {"hardware": 70}}),
    ("min_verified_tickets_by_difficulty", {"thresholds": {"1": 2}}),
    ("practical_checkpoint", {"ticket_title": "Multi-Ticket Simulation 1", "max_hints": 0, "min_score": 7}),
    ("min_cli_labs", {"min_completed": 2}),
    ("no_unresolved_flags", {}),
]


def _seed_gate(db):
    role = Role(name="Support Technician I", rank_order=2, description="test")
    db.add(role)
    db.flush()
    for req_type, config in GATE1:
        db.add(PromotionGate(role_id=role.id, requirement_type=req_type, requirement_config=config))
    db.commit()
    return role


def _seed_curriculum(db):
    module = Module(code="MOD-001", title="The Ticket Is the Job", module_order=1)
    db.add(module)
    db.flush()
    lessons = [
        Lesson(module_id=module.id, title=f"Lesson {i}", lesson_order=i, status="published")
        for i in (1, 2)
    ]
    db.add_all(lessons)
    sim = Ticket(
        title="Multi-Ticket Simulation 1",
        description="Three tickets at once.",
        difficulty=2,
        week_number=4,
    )
    easy1 = Ticket(title="DNS ticket", description="d", difficulty=1, week_number=1)
    easy2 = Ticket(title="Printer ticket", description="d", difficulty=1, week_number=1)
    db.add_all([sim, easy1, easy2])
    for lab_id in ("cli-1", "cli-2"):
        db.add(CliLab(id=lab_id, title=lab_id, compartment_id="basics", vendor_id="cisco", content={}))
    db.commit()
    return module, lessons, sim, [easy1, easy2]


def _fulfill_everything(db, student, lessons, sim, easy_tickets):
    for lesson in lessons:
        db.add(StudentLessonProgress(student_id=student.id, lesson_id=lesson.id, completed_at=datetime.now(timezone.utc)))
    db.add(StudentDomainMastery(student_id=student.id, domain_id="1.0", mastery_percent=85))
    for t in easy_tickets:
        db.add(TicketSubmission(
            student_id=student.id, ticket_id=t.id, writeup="w", status="passed",
            final_score=8, xp_awarded=20,
        ))
    db.add(TicketSubmission(
        student_id=student.id, ticket_id=sim.id, writeup="w", status="passed",
        final_score=9, xp_awarded=40,
    ))
    for lab_id in ("cli-1", "cli-2"):
        db.add(CliLabAttempt(
            student_id=student.id, lab_id=lab_id,
            completed_at=datetime.now(timezone.utc),
        ))
    db.commit()


def test_gate1_full_pass(db):
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]
    assert result["completion_percent"] == 100.0


def test_gate1_fails_on_missing_lessons(db):
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    db.query(StudentLessonProgress).filter(StudentLessonProgress.student_id == student.id).delete()
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    types = [r["type"] for r in result["requirements_missing"]]
    assert types == ["min_completed_lessons"]


def test_gate1_optional_lesson_does_not_block_promotion(db):
    """A lesson the weekly curriculum marks optional (is_required=False) must

    not silently gate promotion — only the still-required lesson has to be
    completed. Reproduces the Weeks 3-24 curriculum-quality pattern where
    wall-of-text lessons are demoted to optional Extra Practice.
    """
    from app.models.training import TrainingWeek, TrainingWeekActivity

    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    week = TrainingWeek(week_number=1, display_order=1, title="Week 1", learning_goals=[], requires_previous_week=False)
    db.add(week)
    db.flush()
    db.add(
        TrainingWeekActivity(
            training_week_id=week.id,
            stable_id="week-1-lesson-optional",
            activity_type="lesson",
            content_ref=str(lessons[1].id),
            display_order=1,
            is_required=False,
            prerequisite_mode="soft",
            metadata_json={},
        )
    )
    db.commit()

    _fulfill_everything(db, student, lessons, sim, easy)
    # The student never completes the lesson the curriculum marked optional.
    db.query(StudentLessonProgress).filter(
        StudentLessonProgress.student_id == student.id, StudentLessonProgress.lesson_id == lessons[1].id
    ).delete()
    db.commit()

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]


def test_gate1_fails_on_low_mastery(db):
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    row = db.query(StudentDomainMastery).filter_by(student_id=student.id).first()
    row.mastery_percent = 50
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert [r["type"] for r in result["requirements_missing"]] == ["min_mastery_by_domain"]


def test_gate1_fails_on_insufficient_tickets(db):
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    # remove one of the two required difficulty-1 tickets
    sub = (
        db.query(TicketSubmission)
        .join(Ticket).filter(Ticket.difficulty == 1, TicketSubmission.student_id == student.id)
        .first()
    )
    db.delete(sub)
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "min_verified_tickets_by_difficulty" in [r["type"] for r in result["requirements_missing"]]


def test_gate1_fails_on_hinted_checkpoint(db):
    """Excessive hints on the checkpoint must fail the gate once hints_used exists.
    Until TB-04 adds the column, the evaluator reads it defensively as 0, so this
    test asserts the low-score path instead (same evaluator branch)."""
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    sub = db.query(TicketSubmission).join(Ticket).filter(Ticket.id == sim.id).first()
    sub.final_score = 5  # below min_score=7
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "practical_checkpoint" in [r["type"] for r in result["requirements_missing"]]


def test_gate1_fails_on_mentor_flag(db):
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    sub = db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id).first()
    sub.admin_comment = "Redo the verification section — no evidence attached."
    sub.admin_reviewed = False
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "no_unresolved_flags" in [r["type"] for r in result["requirements_missing"]]


def test_gate1_flag_resolved_then_passes(db):
    """Remediated student can later pass: resolving the flag restores eligibility."""
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    sub = db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id).first()
    sub.admin_comment = "Fix and resubmit."
    sub.admin_reviewed = False
    db.commit()
    assert check_promotion_eligibility(student.id, role.id, db)["eligible"] is False
    sub.admin_reviewed = True  # mentor re-reviewed after remediation
    db.commit()
    assert check_promotion_eligibility(student.id, role.id, db)["eligible"] is True


def test_gate1_fails_on_missing_cli_labs(db):
    role = _seed_gate(db)
    module, lessons, sim, easy = _seed_curriculum(db)
    student = make_student(db)
    _fulfill_everything(db, student, lessons, sim, easy)
    db.query(CliLabAttempt).filter(CliLabAttempt.student_id == student.id).delete()
    db.commit()
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert "min_cli_labs" in [r["type"] for r in result["requirements_missing"]]
