"""Phase 3A/3A.1 curriculum scaling and editorial-quality contracts."""

import pytest

from app.models.certification import (
    CertificationModule, CertificationObjective, InterviewPrompt, LessonObjective,
    LessonV2Meta, ModuleAssessment, QuestionV2Meta,
)
from app.models.quiz import Question, Quiz
from app.models.training import TrainingWeek
from app.services.objective_coverage import certification_version_coverage
from app.services.deterministic_grader import grade_free_response, grade_short_answer
from app.services.v2_content_loader import (
    ContentValidationError, LoadSummary, _apply_question_bank_editorial_approvals,
    load_module,
)
from app.services.v2_curriculum_service import (
    assessment_questions, entry_view, module_view, resource_activity,
)
from app.services.v2_progress_service import record_activity
from conftest import make_student

MODULES = {
    "module.aplus.core1.hardware_support": {
        "version": "comptia_aplus_220-1201", "objectives": {"3.4", "3.5"},
        "quiz": "A+ PC Components, Power & Safe Upgrades — Module Bank",
    },
    "module.aplus.core2.windows_support_tools": {
        "version": "comptia_aplus_220-1202", "objectives": {"1.1", "1.2", "1.6"},
        "quiz": "A+ Windows Support Tools & Client Configuration — Module Bank",
    },
    "module.aplus.core2.windows_troubleshooting": {
        "version": "comptia_aplus_220-1202", "objectives": {"3.1"},
        "quiz": "A+ Windows Performance, Startup & Application Troubleshooting — Module Bank",
    },
}


def test_batch_loads_idempotently_without_legacy_progression(db):
    weeks_before = db.query(TrainingWeek).count()
    first = load_module(db, commit=True)
    again = load_module(db, commit=True)
    assert first["created"] > 0
    assert again["created"] == 0 and again["updated"] == 0
    assert db.query(TrainingWeek).count() == weeks_before
    assert db.query(CertificationModule).filter(
        CertificationModule.module_key.in_(MODULES)
    ).count() == 3


def test_each_module_has_valid_objectives_lessons_formula_and_bank(db):
    load_module(db, commit=True)
    for key, expected in MODULES.items():
        module = db.query(CertificationModule).filter_by(module_key=key).one()
        lessons = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).all()
        assert len(lessons) == 5
        assert all("## 1. What is this?" in row.content_body for row in lessons)
        codes = {
            code for (code,) in db.query(CertificationObjective.objective_code)
            .join(LessonObjective, LessonObjective.objective_id == CertificationObjective.id)
            .join(LessonV2Meta, LessonV2Meta.id == LessonObjective.lesson_v2_meta_id)
            .filter(LessonV2Meta.certification_module_id == module.id)
        }
        assert codes == expected["objectives"]
        roles = [row.assessment_role for row in db.query(ModuleAssessment).filter_by(
            certification_module_id=module.id
        )]
        assert roles.count("quick_check") == 5
        assert {"module_quiz", "practical", "explain"} <= set(roles)
        quiz = db.query(Quiz).filter_by(title=expected["quiz"]).one()
        questions = db.query(Question).filter_by(quiz_id=quiz.id).all()
        assert len(questions) == 25
        assert len({row.fingerprint for row in questions}) == 25
        metas = db.query(QuestionV2Meta).filter(
            QuestionV2Meta.question_id.in_([row.id for row in questions])
        ).all()
        assert {row.objective_code for row in metas} <= expected["objectives"]
        assert all(row.permission_status in {"owned", "permitted"} and row.source_name for row in metas)
        if key == "module.aplus.core1.hardware_support":
            assert sum(row.permission_status == "permitted" for row in metas) == 6
            assert all(row.source_url for row in metas if row.permission_status == "permitted")
        else:
            assert all(row.permission_status == "owned" for row in metas)
        assert quiz.editorial_status == "validated"
        assert quiz.answer_keys_validated is True
        assert quiz.explanations_complete is True
        assert sum(row.question_type == "multi" for row in metas) == 2
        assert sum(row.question_type == "short_answer" for row in metas) >= 3
        assert sum(row.question_type == "free_response" for row in metas) >= 2
        assert db.query(InterviewPrompt).filter_by(certification_module_id=module.id).count() == 2


def test_entry_and_continue_are_generic_across_modules(db):
    load_module(db, commit=True)
    student = make_student(db, username="phase3a_student")
    entry = entry_view(db, student.id)
    keys = [row["module"]["key"] for row in entry["modules"]]
    assert keys == [
        "module.aplus.core1.ip_configuration",
        "module.aplus.core1.hardware_support",
        "module.aplus.core1.mobile_device_support",
        "module.aplus.core1.network_services_troubleshooting",
        "module.aplus.core1.hardware_fault_isolation",
        "module.aplus.core1.printers_mfds",
        "module.aplus.core2.windows_support_tools",
        "module.aplus.core2.windows_troubleshooting",
        "module.aplus.core2.service_desk_workflow",
    ]
    assert entry["current"]["module"]["key"] == keys[0]
    for key in keys:
        view = module_view(db, student.id, key)
        assert view["continue"]["route"].startswith(f"/learning-v2/modules/{key}/")
        assert view["progress"]["module_complete"] is False

    reference = module_view(db, student.id, keys[0])
    for lesson in reference["lessons"]:
        for resource in lesson["resources"]:
            if resource["required"]:
                resource_activity(db, student.id, keys[0], resource["key"], completed=True)
        record_activity(db, student_id=student.id, module_key=keys[0], activity_type="lesson",
                        ref_key=lesson["key"], status="completed", commit=True)
        record_activity(db, student_id=student.id, module_key=keys[0], activity_type="quick_check",
                        ref_key=lesson["quick_check"]["key"], status="passed", passed=True, commit=True)
    for assessment in reference["assessments"]:
        if assessment["role"] in {"module_quiz", "practical", "service_desk"}:
            status = "completed" if assessment["role"] == "practical" else "passed"
            record_activity(db, student_id=student.id, module_key=keys[0],
                            activity_type=assessment["role"], ref_key=assessment["key"],
                            status=status, passed=True, commit=True)
    for prompt in reference["explain_prompts"]:
        record_activity(db, student_id=student.id, module_key=keys[0], activity_type="explain",
                        ref_key=prompt["key"], status="passed", passed=True, commit=True)

    advanced = entry_view(db, student.id)
    assert advanced["modules"][0]["progress"]["module_complete"] is True
    assert advanced["current"]["module"]["key"] == "module.aplus.core1.hardware_support"


def test_objective_coverage_after_batch_is_transparent(db):
    load_module(db, commit=True)
    core1 = certification_version_coverage(db, "comptia_aplus_220-1201")
    core2 = certification_version_coverage(db, "comptia_aplus_220-1202")
    assert {row["objective_code"] for row in core1["covered"]} == {
        "1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6",
        "2.7", "2.8", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7",
        "3.8", "5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7",
    }
    assert {row["objective_code"] for row in core2["covered"]} == {
        "1.1", "1.2", "1.6", "3.1", "4.1", "4.2", "4.7"
    }
    assert {row["objective_code"] for row in core1["uncovered"]} == {"4.1", "4.2"}
    assert {row["objective_code"] for row in core2["uncovered"]} == {
        "2.1", "2.4", "2.7", "3.2", "3.4"
    }


def test_quick_checks_are_lesson_filtered_and_module_quizzes_follow_blueprints(db):
    load_module(db, commit=True)
    student = make_student(db, username="phase3a_editorial_student")
    for module_key in MODULES:
        module = db.query(CertificationModule).filter_by(module_key=module_key).one()
        assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id).all()
        for assessment in assessments:
            if assessment.assessment_role != "quick_check":
                continue
            payload = assessment_questions(db, student.id, module_key, assessment.assessment_key)
            assert len(payload["questions"]) == assessment.displayed_count
            allowed = set((assessment.config or {}).get("tags_any") or [])
            selected = db.query(Question).filter(Question.id.in_([q["id"] for q in payload["questions"]])).all()
            assert allowed and all(allowed.intersection(question.tags or []) for question in selected)

    expected_objectives = {
        "module.aplus.core1.hardware_support": {"3.4": 9, "3.5": 3},
        "module.aplus.core2.windows_support_tools": {"1.1": 3, "1.2": 5, "1.6": 4},
    }
    for module_key, expected in expected_objectives.items():
        payload = assessment_questions(db, student.id, module_key, f"assess.aplus.{'hardware' if 'hardware' in module_key else 'wintools'}.module_quiz")
        metas = db.query(QuestionV2Meta).filter(QuestionV2Meta.question_id.in_([q["id"] for q in payload["questions"]])).all()
        counts = {code: sum(meta.objective_code == code for meta in metas) for code in expected}
        assert counts == expected

    triage = assessment_questions(db, student.id, "module.aplus.core2.windows_troubleshooting", "assess.aplus.wintriage.module_quiz")
    selected = db.query(Question).filter(Question.id.in_([q["id"] for q in triage["questions"]])).all()
    groups = [
        {"method", "scope", "escalation", "reproduce"}, {"performance", "task-manager", "disk"},
        {"startup", "post", "bsod", "shutdown", "safe-mode", "driver"},
        {"crash", "application", "reliability", "event-viewer", "isolation"},
        {"verification", "documentation"},
    ]
    assert all(any(group.intersection(question.tags or []) for question in selected) for group in groups)


def test_short_answer_variants_and_explain_aliases_are_fair():
    for response, accepted in (
        ("MSINFO32.EXE", ["msinfo32", "msinfo32.exe", "system information"]),
        ("netstat -a -n -o", ["netstat -ano", "netstat /ano", "netstat -a -n -o"]),
        ("PERFMON.EXE /REL", ["Reliability Monitor", "perfmon.exe /rel"]),
        ("taskmgr.exe", ["Task Manager", "taskmgr.exe"]),
    ):
        assert grade_short_answer(response, accepted)["passed"] is True
    concepts = [
        {"concept": "active network profile", "aliases": ["Public profile"]},
        {"concept": "proxy configuration", "aliases": ["Windows proxy"]},
    ]
    assert grade_free_response(
        "I would inspect the Public profile and Windows proxy before changing anything.",
        concepts, partial_credit=False,
    )["passed"] is True
    ambiguous = grade_free_response(
        "I would inspect the Public profile and then investigate the application safely.",
        concepts, partial_credit=False,
    )
    assert ambiguous["status"] == "needs_review" and ambiguous["passed"] is None


def test_editorial_approval_rejects_changed_bank_bytes(db, tmp_path):
    questions = tmp_path / "questions"
    questions.mkdir()
    (questions / "changed.csv").write_text("changed after review\n", encoding="utf-8")
    (questions / "editorial-approvals.yaml").write_text(
        "approvals:\n  - filename: changed.csv\n    quiz_title: Reviewed bank\n"
        "    sha256: 0000000000000000000000000000000000000000000000000000000000000000\n"
        "    reviewed_question_count: 1\n    editorial_status: validated\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentValidationError, match="changed after editorial approval"):
        _apply_question_bank_editorial_approvals(db, str(questions), LoadSummary())
