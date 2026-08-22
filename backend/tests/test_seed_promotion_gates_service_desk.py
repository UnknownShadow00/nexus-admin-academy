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


def test_seeded_gate_4_has_no_unsatisfiable_mastery_domain_requirement(db):
    """Gate 4 previously required mastery in domains ("windows_server",
    "active_directory") that never existed in StudentDomainMastery, making the
    gate permanently unsatisfiable. Aliasing them onto the unrelated
    "security"/"procedures" domain (4.0) would let students pass this gate
    using evidence that has nothing to do with Windows Server/AD — a
    gate-bypass via domain mismatch, not a real fix. Since this phase must
    not invent new mastery-domain taxonomy, the correct minimal fix is to
    drop the unsatisfiable sub-requirement rather than mis-map it.
    """
    _seed_real_progression_config(db)
    role = db.query(Role).filter_by(name="Junior Systems Technician").one()
    gate_types = {
        row.requirement_type
        for row in db.query(PromotionGate).filter_by(role_id=role.id).all()
    }
    assert "min_mastery_by_domain" not in gate_types


def test_service_desk_gate_fails_closed_on_malformed_config(db):
    """A misconfigured min_service_desk_passes gate (unknown pack_key, or a
    missing/zero min_passed) must never silently auto-pass."""
    _seed_real_progression_config(db)
    student = make_student(db, "malformed-service-desk-gate")

    role = db.query(Role).filter_by(name="Support Technician I").one()
    db.query(PromotionGate).filter_by(
        role_id=role.id, requirement_type="min_service_desk_passes"
    ).delete()
    db.add(
        PromotionGate(
            role_id=role.id,
            requirement_type="min_service_desk_passes",
            requirement_config={"pack_key": "does-not-exist"},
        )
    )
    db.commit()

    result = check_promotion_eligibility(student.id, role.id, db)
    sd_result = next(
        item
        for item in result["requirements_missing"]
        if item["type"] == "min_service_desk_passes"
    )
    assert sd_result["met"] is False


# ---------------------------------------------------------------------------
# Phase 1B: validator + remaining trust-boundary regression coverage
# ---------------------------------------------------------------------------


def test_validate_promotion_gates_config_passes_on_real_seed_config():
    from app.services.promotion_gate_validation import validate_promotion_gates_config
    from seed import PROMOTION_GATES

    issues = validate_promotion_gates_config(
        PROMOTION_GATES,
        service_desk_pack_keys={pack.key for pack in SERVICE_DESK_PACKS},
    )
    assert issues == []


def test_validate_promotion_gates_config_catches_known_bad_configs():
    from app.services.promotion_gate_validation import validate_promotion_gates_config

    bad_gates = [
        {"role": "R", "requirement_type": "min_verified_tickets_by_difficulty", "config": {}},
        {"role": "R", "requirement_type": "not_a_real_type", "config": {}},
        {"role": "R", "requirement_type": "min_service_desk_passes", "config": {"pack_key": "nope", "min_passed": 0}},
        {"role": "R", "requirement_type": "min_mastery_by_domain", "config": {"thresholds": {"windows_server": 75}}},
        {"role": "R", "requirement_type": "min_cli_labs", "config": {"min_completed": -1}},
        {"role": "R", "requirement_type": "no_unresolved_flags", "config": {}},
        {"role": "R", "requirement_type": "no_unresolved_flags", "config": {}},
    ]
    issues = validate_promotion_gates_config(
        bad_gates, service_desk_pack_keys={pack.key for pack in SERVICE_DESK_PACKS}
    )
    assert len(issues) >= 6
    joined = " | ".join(issues)
    assert "retired requirement_type" in joined
    assert "unknown requirement_type" in joined
    assert "unknown pack_key" in joined
    assert "unknown domain" in joined
    assert "positive integer" in joined
    assert "appears 2 times" in joined


def test_seed_promotion_gates_prunes_orphaned_rows_not_just_retired_types(db):
    """Regression for a real production incident: a min_mastery_by_domain row
    for Junior Systems Technician (windows_server/active_directory
    thresholds) was removed from PROMOTION_GATES by an earlier commit, but
    seed_promotion_gates only ever deleted the two ticket-based retired
    types by name — so the orphaned row survived every re-seed and kept
    Gate 4 permanently unsatisfiable in production even after the fix
    shipped. seed_promotion_gates must prune any row whose (role,
    requirement_type) pair is no longer in PROMOTION_GATES at all, not just
    rows of the two named-retired types.
    """
    _seed_real_progression_config(db)
    role = db.query(Role).filter_by(name="Junior Systems Technician").one()
    db.add(
        PromotionGate(
            role_id=role.id,
            requirement_type="min_mastery_by_domain",
            requirement_config={"thresholds": {"windows_server": 75, "active_directory": 75}},
        )
    )
    db.commit()

    seed_promotion_gates(db)
    db.commit()

    gate_types = {
        row.requirement_type
        for row in db.query(PromotionGate).filter_by(role_id=role.id).all()
    }
    assert "min_mastery_by_domain" not in gate_types


def test_no_retired_ticket_requirement_type_in_any_active_seeded_gate(db):
    _seed_real_progression_config(db)
    active_types = {
        row.requirement_type for row in db.query(PromotionGate).all()
    }
    assert "min_verified_tickets_by_difficulty" not in active_types
    assert "practical_checkpoint" not in active_types


def test_seed_promotion_gates_is_idempotent(db):
    _seed_real_progression_config(db)
    before = sorted(
        (row.role_id, row.requirement_type, row.requirement_config)
        for row in db.query(PromotionGate).all()
    )

    seed_promotion_gates(db)
    db.commit()

    after = sorted(
        (row.role_id, row.requirement_type, row.requirement_config)
        for row in db.query(PromotionGate).all()
    )
    assert before == after


def test_cross_student_service_desk_pass_does_not_satisfy_another_students_gate(db):
    _seed_real_progression_config(db)
    other_student = make_student(db, "other-student-with-passes")
    target_student = make_student(db, "student-with-no-passes")

    role = db.query(Role).filter_by(name="Support Technician I").one()
    starter_pack = next(pack for pack in SERVICE_DESK_PACKS if pack.key == "starter-support")
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
        db.add(
            ServiceDeskAttempt(
                student_id=other_student.id,
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

    result = check_promotion_eligibility(target_student.id, role.id, db)
    sd_result = next(
        item
        for item in (result["requirements_met"] + result["requirements_missing"])
        if item["type"] == "min_service_desk_passes"
    )
    assert sd_result["met"] is False
    assert sd_result["progress"]["current"] == 0


def test_historical_ticket_data_does_not_affect_service_desk_gate_or_module_mastery(db):
    _seed_real_progression_config(db)
    student = make_student(db, "student-with-legacy-tickets")

    ticket = Ticket(title="legacy", description="d", difficulty=1, week_number=1)
    db.add(ticket)
    db.flush()
    db.add(
        TicketSubmission(
            student_id=student.id,
            ticket_id=ticket.id,
            writeup="w",
            status="passed",
            final_score=10,
            xp_awarded=30,
        )
    )
    db.commit()

    role = db.query(Role).filter_by(name="Support Technician I").one()
    result = check_promotion_eligibility(student.id, role.id, db)
    sd_result = next(
        item
        for item in (result["requirements_met"] + result["requirements_missing"])
        if item["type"] == "min_service_desk_passes"
    )
    assert sd_result["met"] is False
    assert sd_result["progress"]["current"] == 0

    from app.services.progression_service import get_module_mastery

    module = Module(code="MOD-TEST-LEGACY", title="legacy module", module_order=99)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="legacy lesson", lesson_order=1, status="published")
    db.add(lesson)
    db.flush()
    ticket.lesson_id = lesson.id
    db.commit()

    assert get_module_mastery(student.id, module.id, db) == 0.0


# Mirrors the alias map in progression_service._check_mastery_requirement.
_MASTERY_DOMAIN_ALIASES = {
    "hardware": "1.0",
    "networking": "2.0",
    "software_troubleshooting": "3.0",
    "security": "4.0",
    "procedures": "4.0",
}


def _satisfy_every_requirement_on_gate(db, student, role):
    """Build the minimum real evidence needed to clear every requirement
    currently seeded for `role`, driven entirely from the live PromotionGate
    rows rather than a hardcoded per-gate fixture — proves the *actual*
    seeded config is satisfiable, not a hand-picked stand-in for it."""
    module_counter = 1000
    lab_counter = 0
    for gate in db.query(PromotionGate).filter_by(role_id=role.id).all():
        cfg = gate.requirement_config or {}
        if gate.requirement_type == "required_quiz":
            week = cfg["week"]
            quiz = Quiz(
                title=f"Satisfiability check quiz week {week}",
                question_count=10,
                week_number=week,
                status=QUIZ_STATUS_PUBLISHED,
                quiz_purpose=QUIZ_PURPOSE_GATE,
                is_required=True,
                show_in_weekly_checklist=True,
                answer_keys_validated=True,
            )
            db.add(quiz)
            db.flush()
            db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, score=10, xp_awarded=0))

        elif gate.requirement_type == "min_completed_lessons":
            for code in cfg["module_codes"]:
                module_counter += 1
                module = Module(code=code, title=code, module_order=module_counter)
                db.add(module)
                db.flush()
                lesson = Lesson(module_id=module.id, title=f"{code} lesson", lesson_order=1, status="published")
                db.add(lesson)
                db.flush()
                db.add(
                    StudentLessonProgress(
                        student_id=student.id, lesson_id=lesson.id, completed_at=datetime.now(timezone.utc)
                    )
                )

        elif gate.requirement_type == "min_mastery_by_domain":
            for domain, required in cfg["thresholds"].items():
                resolved = _MASTERY_DOMAIN_ALIASES.get(str(domain).lower(), str(domain))
                existing = (
                    db.query(StudentDomainMastery)
                    .filter_by(student_id=student.id, domain_id=resolved)
                    .first()
                )
                if existing:
                    existing.mastery_percent = max(existing.mastery_percent, required + 5)
                else:
                    db.add(
                        StudentDomainMastery(
                            student_id=student.id, domain_id=resolved, mastery_percent=required + 5
                        )
                    )

        elif gate.requirement_type == "min_service_desk_passes":
            pack = next(p for p in SERVICE_DESK_PACKS if p.key == cfg["pack_key"])
            for stable_key in pack.scenario_keys[: cfg["min_passed"]]:
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
                assert version is not None, f"missing published scenario version for {stable_key}"
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

        elif gate.requirement_type == "min_cli_labs":
            prefix = cfg.get("pack_prefix") or "satisfiability-check-"
            for _ in range(cfg["min_completed"]):
                lab_counter += 1
                lab_id = f"{prefix}{lab_counter}"
                db.add(CliLab(id=lab_id, title=lab_id, compartment_id="test", vendor_id="test", content={}))
                db.flush()
                db.add(
                    CliLabAttempt(student_id=student.id, lab_id=lab_id, completed_at=datetime.now(timezone.utc))
                )

        elif gate.requirement_type == "no_unresolved_flags":
            pass

        else:
            raise AssertionError(f"unhandled requirement_type {gate.requirement_type!r} in satisfiability check")

    db.commit()


def test_every_seeded_gate_is_satisfiable(db):
    """Success criterion #3: every active seeded gate must be satisfiable.
    Builds real evidence for every requirement row actually seeded for each
    of the five promotion roles and confirms eligibility flips to True."""
    _seed_real_progression_config(db)
    for role_name in (
        "Support Technician I",
        "Support Technician II",
        "Network Support Technician",
        "Junior Systems Technician",
        "Junior Infrastructure Administrator",
    ):
        role = db.query(Role).filter_by(name=role_name).one()
        student = make_student(db, f"satisfiability-{role_name}".replace(" ", "-").lower())
        _satisfy_every_requirement_on_gate(db, student, role)

        result = check_promotion_eligibility(student.id, role.id, db)
        assert result["eligible"] is True, f"{role_name}: {result['requirements_missing']}"
