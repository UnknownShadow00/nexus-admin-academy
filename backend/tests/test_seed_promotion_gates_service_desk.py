from datetime import datetime, timezone

from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.mastery import StudentDomainMastery
from app.models.progression import PromotionGate, Role
from app.models.quiz import QUIZ_PURPOSE_GATE, QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.ticket import Ticket, TicketSubmission
from app.services.progression_service import check_promotion_eligibility
from app.services.service_desk_progression import SERVICE_DESK_PACKS
from conftest import make_student
from seed import seed_promotion_gates, seed_roles, seed_service_desk_scenarios


def _seed_real_progression_config(db):
    seed_roles(db)
    seed_promotion_gates(db)
    seed_service_desk_scenarios(db)
    db.commit()


def _satisfy_other_gate_1_requirements(db, student):
    for order, code in enumerate(
        ("MOD-000", "MOD-001", "MOD-002", "MOD-003", "MOD-004")
    ):
        module = Module(code=code, title=code, module_order=order)
        db.add(module)
        db.flush()
        lesson = Lesson(
            module_id=module.id,
            title=f"{code} lesson",
            lesson_order=1,
            status="published",
        )
        db.add(lesson)
        db.flush()
        db.add(
            StudentLessonProgress(
                student_id=student.id,
                lesson_id=lesson.id,
                completed_at=datetime.now(timezone.utc),
            )
        )

    db.add_all(
        [
            StudentDomainMastery(
                student_id=student.id,
                domain_id="1.0",
                mastery_percent=85,
            ),
            StudentDomainMastery(
                student_id=student.id,
                domain_id="3.0",
                mastery_percent=85,
            ),
        ]
    )

    for index in range(9):
        lab_id = f"gate-1-cli-{index}"
        db.add(
            CliLab(
                id=lab_id,
                title=lab_id,
                compartment_id="gate-1",
                vendor_id="test",
                content={},
            )
        )
        db.flush()
        db.add(
            CliLabAttempt(
                student_id=student.id,
                lab_id=lab_id,
                completed_at=datetime.now(timezone.utc),
            )
        )

    quiz = Quiz(
        title="Gate 1 quiz",
        question_count=10,
        week_number=4,
        status=QUIZ_STATUS_PUBLISHED,
        quiz_purpose=QUIZ_PURPOSE_GATE,
        is_required=True,
        show_in_weekly_checklist=True,
        answer_keys_validated=True,
    )
    db.add(quiz)
    db.flush()
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            score=10,
            xp_awarded=0,
        )
    )
    db.commit()


def test_seeded_gate_1_uses_service_desk_passes_without_legacy_tickets(db):
    _seed_real_progression_config(db)
    student = make_student(db, "service-desk-gate-1")
    _satisfy_other_gate_1_requirements(db, student)

    role = db.query(Role).filter_by(name="Support Technician I").one()
    db.add_all(
        [
            PromotionGate(
                role_id=role.id,
                requirement_type="min_verified_tickets_by_difficulty",
                requirement_config={"thresholds": {"1": 1}},
            ),
            PromotionGate(
                role_id=role.id,
                requirement_type="practical_checkpoint",
                requirement_config={"ticket_title": "Legacy checkpoint"},
            ),
        ]
    )
    db.commit()
    seed_promotion_gates(db)
    db.commit()

    gate_types = {
        row.requirement_type
        for row in db.query(PromotionGate).filter_by(role_id=role.id).all()
    }
    assert "min_service_desk_passes" in gate_types
    assert "min_verified_tickets_by_difficulty" not in gate_types
    assert "practical_checkpoint" not in gate_types
    assert db.query(Ticket).count() == 0
    assert db.query(TicketSubmission).count() == 0

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert [item["type"] for item in result["requirements_missing"]] == [
        "min_service_desk_passes"
    ]

    starter_pack = next(
        pack for pack in SERVICE_DESK_PACKS if pack.key == "starter-support"
    )
    for stable_key in starter_pack.scenario_keys:
        version = (
            db.query(ServiceDeskScenarioVersion)
            .join(ServiceDeskScenario)
            .filter(
                ServiceDeskScenario.stable_key == stable_key,
                ServiceDeskScenarioVersion.status == "published",
            )
            .order_by(ServiceDeskScenarioVersion.version_number.desc())
            .first()
        )
        assert version is not None
        db.add(
            ServiceDeskAttempt(
                student_id=student.id,
                scenario_version_id=version.id,
                mode="simulation",
                experience_mode="assessment",
                status="completed",
                current_state={},
                current_state_hash=stable_key.ljust(64, "0")[:64],
                state_version=1,
                attempt_number=1,
                completed_at=datetime.now(timezone.utc),
                score=90,
                passed=True,
            )
        )
    db.commit()

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]
    assert result["requirements_missing"] == []
    assert db.query(Ticket).count() == 0
    assert db.query(TicketSubmission).count() == 0


def test_seeded_gate_4_mastery_aliases_resolve_to_domain_4(db):
    _seed_real_progression_config(db)
    student = make_student(db, "gate-4-mastery-aliases")
    db.add(
        StudentDomainMastery(
            student_id=student.id,
            domain_id="4.0",
            mastery_percent=75,
        )
    )
    db.commit()

    role = db.query(Role).filter_by(name="Junior Systems Technician").one()
    result = check_promotion_eligibility(student.id, role.id, db)
    mastery = next(
        item
        for item in result["requirements_met"]
        if item["type"] == "min_mastery_by_domain"
    )
    assert mastery["progress"] == {
        "windows_server": {"current": 75.0, "required": 75},
        "active_directory": {"current": 75.0, "required": 75},
    }
