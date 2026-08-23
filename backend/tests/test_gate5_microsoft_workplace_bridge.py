"""Phase 4B.1 verification: the System A/System B graduation bridge.

Proves that the graduating role's PromotionGate rows added by
sync_microsoft_workplace_foundations() actually require Microsoft Workplace
curriculum -- not merely that legacy week-24 progress or an unrelated
Service Desk pack happens to also satisfy them. Mirrors the real gate shape
written in training_curriculum_seed.py (module_codes MOD-025..MOD-029,
required_quiz week 27, min_service_desk_passes pack_key="microsoft-workplace").
"""
from datetime import datetime, timezone

from conftest import make_student
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.progression import PromotionGate, Role
from app.models.quiz import QUIZ_PURPOSE_GATE, QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.service_desk import ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services.progression_service import check_promotion_eligibility
from app.services.service_desk_progression import SERVICE_DESK_PACKS

M365_MODULE_CODES = ["MOD-025", "MOD-026", "MOD-027", "MOD-028", "MOD-029"]


def _seed(db):
    role = Role(name="Junior Infrastructure Administrator", rank_order=6, description="grad")
    db.add(role)
    db.flush()
    db.add_all(
        [
            PromotionGate(
                role_id=role.id,
                requirement_type="min_completed_lessons",
                requirement_config={"module_codes": M365_MODULE_CODES},
            ),
            PromotionGate(
                role_id=role.id,
                requirement_type="required_quiz",
                requirement_config={"week": 27},
            ),
            PromotionGate(
                role_id=role.id,
                requirement_type="min_service_desk_passes",
                requirement_config={"pack_key": "microsoft-workplace", "min_passed": 2},
            ),
        ]
    )
    lessons = []
    for index, code in enumerate(M365_MODULE_CODES):
        module = Module(code=code, title=code, module_order=25 + index)
        db.add(module)
        db.flush()
        lesson = Lesson(module_id=module.id, title=f"{code} lesson", lesson_order=1, status="published")
        db.add(lesson)
        lessons.append(lesson)
    quiz = Quiz(
        title="M365 Sign-In & MFA gate quiz",
        question_count=5,
        week_number=27,
        status=QUIZ_STATUS_PUBLISHED,
        quiz_purpose=QUIZ_PURPOSE_GATE,
        is_active=True,
        is_required=True,
        show_in_weekly_checklist=True,
        answer_keys_validated=True,
    )
    db.add(quiz)
    db.commit()
    return role, lessons, quiz


def _complete_lessons(db, student, lessons):
    for lesson in lessons:
        db.add(StudentLessonProgress(student_id=student.id, lesson_id=lesson.id, completed_at=datetime.now(timezone.utc)))
    db.commit()


def _pass_quiz(db, student, quiz):
    db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, score=5, xp_awarded=0))
    db.commit()


def _real_m365_pack():
    return next(pack for pack in SERVICE_DESK_PACKS if pack.key == "microsoft-workplace")


def _ensure_scenario(db, stable_key):
    scenario = db.query(ServiceDeskScenario).filter_by(stable_key=stable_key).first()
    if scenario is None:
        scenario = ServiceDeskScenario(stable_key=stable_key, title=stable_key, category="service_desk", difficulty=1)
        db.add(scenario)
        db.flush()
        db.add(
            ServiceDeskScenarioVersion(
                scenario_id=scenario.id,
                version_number=1,
                definition_json={"stableKey": stable_key},
                definition_hash=stable_key.ljust(64, "0")[:64],
                status="published",
                published_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    return scenario


def _published_scenario_version(db, stable_key):
    _ensure_scenario(db, stable_key)
    return (
        db.query(ServiceDeskScenarioVersion)
        .join(ServiceDeskScenario)
        .filter(ServiceDeskScenario.stable_key == stable_key, ServiceDeskScenarioVersion.status == "published")
        .order_by(ServiceDeskScenarioVersion.version_number.desc())
        .first()
    )


def _record_service_desk_pass(db, student, stable_key, *, passed=True):
    version = _published_scenario_version(db, stable_key)
    assert version is not None, f"expected a published scenario version for {stable_key}"
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
            score=90 if passed else 20,
            passed=passed,
        )
    )
    db.commit()


def test_cannot_graduate_with_no_microsoft_curriculum(db):
    """A student who has done nothing toward the Microsoft Workplace stage
    must not be eligible -- reaching any legacy week alone is not tracked by
    these gates at all, so there is nothing legacy progress could leak past."""
    role, lessons, quiz = _seed(db)
    student = make_student(db)
    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    missing_types = {r["type"] for r in result["requirements_missing"]}
    assert missing_types == {"min_completed_lessons", "required_quiz", "min_service_desk_passes"}


def test_unrelated_service_desk_pack_does_not_satisfy_the_bridge(db):
    """Passing scenarios from a different pack (e.g. starter-support) must
    not count toward the microsoft-workplace requirement."""
    role, lessons, quiz = _seed(db)
    student = make_student(db)
    _complete_lessons(db, student, lessons)
    _pass_quiz(db, student, quiz)

    starter_pack = next(pack for pack in SERVICE_DESK_PACKS if pack.key == "starter-support")
    for stable_key in starter_pack.scenario_keys:
        _record_service_desk_pass(db, student, stable_key)

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert [r["type"] for r in result["requirements_missing"]] == ["min_service_desk_passes"]
    assert result["requirements_missing"][0]["progress"]["current"] == 0


def test_failed_microsoft_scenario_does_not_satisfy_the_bridge(db):
    """A failed attempt at a real m365 scenario must not count as a pass."""
    role, lessons, quiz = _seed(db)
    student = make_student(db)
    _complete_lessons(db, student, lessons)
    _pass_quiz(db, student, quiz)

    pack = _real_m365_pack()
    for stable_key in pack.scenario_keys:
        _record_service_desk_pass(db, student, stable_key, passed=False)

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert [r["type"] for r in result["requirements_missing"]] == ["min_service_desk_passes"]


def test_another_students_pass_does_not_satisfy_the_bridge(db):
    """Service Desk passes are scoped by student_id; another student's
    completion must not leak into this student's eligibility."""
    role, lessons, quiz = _seed(db)
    student = make_student(db, "m365-bridge-student")
    other_student = make_student(db, "m365-bridge-other-student")
    _complete_lessons(db, student, lessons)
    _pass_quiz(db, student, quiz)

    pack = _real_m365_pack()
    for stable_key in pack.scenario_keys:
        _record_service_desk_pass(db, other_student, stable_key)

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is False
    assert [r["type"] for r in result["requirements_missing"]] == ["min_service_desk_passes"]


def test_satisfying_microsoft_curriculum_correctly_allows_the_gate(db):
    """The positive case: lessons + gate quiz + both real m365 Service Desk
    passes (for the same student) makes the bridge, and only the bridge,
    satisfied."""
    role, lessons, quiz = _seed(db)
    student = make_student(db)
    _complete_lessons(db, student, lessons)
    _pass_quiz(db, student, quiz)

    pack = _real_m365_pack()
    for stable_key in pack.scenario_keys:
        _record_service_desk_pass(db, student, stable_key)

    result = check_promotion_eligibility(student.id, role.id, db)
    assert result["eligible"] is True, result["requirements_missing"]
    assert result["requirements_missing"] == []
