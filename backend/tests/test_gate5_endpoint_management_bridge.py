"""Phase 4B.2 graduation bridge verification."""

from datetime import datetime, timezone

from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.progression import PromotionGate, Role
from app.models.quiz import QUIZ_PURPOSE_GATE, QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.service_desk import ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services.progression_service import check_promotion_eligibility
from app.services.service_desk_progression import SERVICE_DESK_PACKS
from conftest import make_student


ENDPOINT_MODULE_CODES = ["MOD-030", "MOD-031", "MOD-032", "MOD-033", "MOD-034"]


def test_all_endpoint_guided_labs_use_the_evidence_workbench_contract():
    from app.services.training_curriculum_seed import _INTUNE_ENDPOINT_WORKBENCHES, _INTUNE_NEW_LABS

    labs = [lab for week_labs in _INTUNE_NEW_LABS.values() for lab in week_labs]
    assert len(labs) == 13
    assert set(_INTUNE_ENDPOINT_WORKBENCHES) == {lab["title"] for lab in labs}

    for lab in labs:
        workbench = _INTUNE_ENDPOINT_WORKBENCHES[lab["title"]]
        assert workbench["guidance_level"] == lab["role"]
        assert len(workbench["panels"]) >= 3
        assert len(workbench["required_inspections"]) >= 2
        assert workbench["documentation_required"] is True
        assert workbench["verification"]["label"] == "Simulated device state after action"
        if lab["role"] == "practice":
            assert workbench.get("guidance")
        else:
            assert "guidance" not in workbench

    prove = next(lab for lab in labs if lab["role"] == "prove")
    assert prove["title"] == "Diagnose the Multi-Signal Ticket"
    assert len(prove["questions"]) >= 3
    assert len(_INTUNE_ENDPOINT_WORKBENCHES[prove["title"]]["panels"]) >= 5


def _seed_bridge(db):
    role = Role(name="Junior Infrastructure Administrator", rank_order=6, description="graduating role")
    db.add(role)
    db.flush()
    db.add_all(
        [
            PromotionGate(
                role_id=role.id,
                requirement_type="min_completed_lessons",
                requirement_config={"module_codes": ENDPOINT_MODULE_CODES},
            ),
            PromotionGate(
                role_id=role.id,
                requirement_type="required_quiz",
                requirement_config={"week": 33},
            ),
            PromotionGate(
                role_id=role.id,
                requirement_type="min_service_desk_passes",
                requirement_config={"pack_key": "endpoint-management", "min_passed": 2},
            ),
        ]
    )
    lessons = []
    for index, code in enumerate(ENDPOINT_MODULE_CODES):
        module = Module(code=code, title=code, module_order=31 + index)
        db.add(module)
        db.flush()
        lesson = Lesson(module_id=module.id, title=f"{code} lesson", lesson_order=1, status="published")
        db.add(lesson)
        lessons.append(lesson)
    quiz = Quiz(
        title="Windows 11 endpoint gate quiz",
        question_count=5,
        week_number=33,
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


def _complete_endpoint_requirements(db, student, lessons, quiz):
    for lesson in lessons:
        db.add(
            StudentLessonProgress(
                student_id=student.id,
                lesson_id=lesson.id,
                completed_at=datetime.now(timezone.utc),
            )
        )
    db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, score=5, xp_awarded=0))
    pack = next(pack for pack in SERVICE_DESK_PACKS if pack.key == "endpoint-management")
    for stable_key in pack.scenario_keys:
        scenario = ServiceDeskScenario(
            stable_key=stable_key,
            title=stable_key,
            category="endpoint",
            difficulty=3,
            status="active",
        )
        db.add(scenario)
        db.flush()
        version = ServiceDeskScenarioVersion(
            scenario_id=scenario.id,
            version_number=1,
            definition_json={"stableKey": stable_key},
            definition_hash=stable_key.ljust(64, "0")[:64],
            validation_status="valid",
            status="published",
            published_at=datetime.now(timezone.utc),
        )
        db.add(version)
        db.flush()
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
                score=100,
                passed=True,
            )
        )
    db.commit()


def test_endpoint_pack_is_exactly_the_two_approved_live_scenarios():
    pack = next(pack for pack in SERVICE_DESK_PACKS if pack.key == "endpoint-management")
    assert pack.scenario_keys == ("bitlocker-recovery", "offboarding-device-reassignment")
    assert pack.required_week == 34


def test_future_graduation_requires_endpoint_content(db):
    role, _lessons, _quiz = _seed_bridge(db)
    student = make_student(db, username="endpoint-graduation-missing")

    result = check_promotion_eligibility(student.id, role.id, db)

    assert result["eligible"] is False
    assert {item["type"] for item in result["requirements_missing"]} == {
        "min_completed_lessons",
        "required_quiz",
        "min_service_desk_passes",
    }


def test_completed_endpoint_requirements_allow_the_bridge(db):
    role, lessons, quiz = _seed_bridge(db)
    student = make_student(db, username="endpoint-graduation-complete")
    _complete_endpoint_requirements(db, student, lessons, quiz)

    result = check_promotion_eligibility(student.id, role.id, db)

    assert result["eligible"] is True, result["requirements_missing"]
