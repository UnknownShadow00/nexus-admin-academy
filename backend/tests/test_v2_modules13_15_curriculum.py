"""Runtime contracts for the reviewed A+ Modules 13 through 15 packages."""

from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import or_

import seed_v2_foundation
from app.models.certification import (
    CertificationModule,
    CertificationObjective,
    InterviewPrompt,
    InterviewPromptObjective,
    LearningResource,
    LearningResourceLink,
    LessonObjective,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
    question_objective_codes,
)
from app.models.quiz import Question, Quiz
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services.objective_coverage import certification_version_coverage
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import entry_view, module_view
from app.services.v2_mentor_service import cohort_progress
from conftest import make_student


MODULES = {
    "module.aplus.core2.identity_endpoint_hardening": {
        "prefix": "M13Q",
        "lessons": 6,
        "questions": {"single": 28, "multi": 4, "short_answer": 2, "free_response": 2},
        "objectives": {"2.1", "2.2", "2.7"},
        "resources": 9,
        "resource_links": 10,
        "required": 6,
        "service_desk": "sd.aplus.security.approved_app_standard_user",
        "service_desk_available": False,
    },
    "module.aplus.core2.connected_endpoint_mobile_security": {
        "prefix": "M14Q",
        "lessons": 7,
        "questions": {"single": 28, "multi": 5, "short_answer": 3, "free_response": 2},
        "objectives": {"2.3", "2.8", "2.10", "2.11", "3.2", "3.3"},
        "resources": 10,
        "resource_links": 10,
        "required": 7,
        "service_desk": "sd.aplus.security.mobile_secure_wifi_profile",
        "service_desk_available": False,
    },
    "module.aplus.core2.threat_malware_response": {
        "prefix": "M15Q",
        "lessons": 6,
        "questions": {"single": 28, "multi": 4, "short_answer": 2, "free_response": 2},
        "objectives": {"2.4", "2.5", "2.6", "3.4"},
        "resources": 9,
        "resource_links": 9,
        "required": 6,
        "service_desk": "inc2508",
        "service_desk_available": True,
    },
}


def _rows(db, module_key):
    module = db.query(CertificationModule).filter_by(module_key=module_key).one()
    lessons = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).all()
    assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id).all()
    quiz_assessment = next(row for row in assessments if row.assessment_role == "module_quiz")
    quiz = db.get(Quiz, quiz_assessment.quiz_id)
    questions = (
        db.query(Question, QuestionV2Meta)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(Question.quiz_id == quiz.id)
        .all()
    )
    return module, lessons, assessments, questions


@pytest.mark.parametrize("module_key", MODULES)
def test_modules13_15_load_authored_content_and_explicit_quick_checks(db, module_key):
    load_module(db, commit=True)
    expected = MODULES[module_key]
    module, lessons, assessments, questions = _rows(db, module_key)

    assert len(lessons) == expected["lessons"]
    assert Counter(meta.question_type for _, meta in questions) == expected["questions"]
    assert all(question.explanation for question, _ in questions)
    assert all(meta.source_name and meta.permission_status for _, meta in questions)

    lesson_objectives = {
        code
        for (code,) in db.query(CertificationObjective.objective_code)
        .join(LessonObjective, LessonObjective.objective_id == CertificationObjective.id)
        .join(LessonV2Meta, LessonV2Meta.id == LessonObjective.lesson_v2_meta_id)
        .filter(LessonV2Meta.certification_module_id == module.id)
    }
    assert lesson_objectives == expected["objectives"]

    quick_checks = sorted(
        (row for row in assessments if row.assessment_role == "quick_check"),
        key=lambda row: row.display_order,
    )
    assert len(quick_checks) == expected["lessons"]
    lessons_by_id = {lesson.id: lesson for lesson in lessons}
    for lesson_order, quick_check in enumerate(quick_checks, 1):
        lesson = lessons_by_id[quick_check.lesson_v2_meta_id]
        expected_ids = [f"{expected['prefix']}{number:03d}" for number in range(
            (lesson_order - 1) * 4 + 1,
            lesson_order * 4 + 1,
        )]
        assert quick_check.lesson_v2_meta_id == lesson.id
        assert quick_check.displayed_count == 4
        assert quick_check.config["tags_any"] == expected_ids

    quiz = next(row for row in assessments if row.assessment_role == "module_quiz")
    assert quiz.displayed_count == 12
    assert quiz.pass_percent == 70
    assert quiz.quiz_id
    assert next(row for row in assessments if row.assessment_role == "practical").lab_template_id


@pytest.mark.parametrize("module_key", MODULES)
def test_modules13_15_resources_service_desk_and_explain_resolve(db, module_key):
    seed_v2_foundation.run(db)
    expected = MODULES[module_key]
    module, lessons, assessments, _ = _rows(db, module_key)
    lesson_ids = [lesson.id for lesson in lessons]
    links = db.query(LearningResourceLink).filter(
        or_(
            LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids),
            LearningResourceLink.certification_module_id == module.id,
        )
    ).all()
    resources = db.query(LearningResource).filter(
        LearningResource.id.in_({link.resource_id for link in links})
    ).all()
    assert len(resources) == expected["resources"]
    assert len(links) == expected["resource_links"]
    assert sum(link.is_required for link in links) == expected["required"]
    assert all(resource.title and resource.provider and resource.url for resource in resources)

    service_desk = next(row for row in assessments if row.assessment_role == "service_desk")
    assert service_desk.active is expected["service_desk_available"]
    scenario = db.get(ServiceDeskScenario, service_desk.service_desk_scenario_id)
    assert scenario.stable_key == expected["service_desk"]
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id, status="published")
        .one()
    )
    hints = version.definition_json["hints"]
    if expected["service_desk_available"]:
        assert len(hints) == 3
        assert all(isinstance(hint, str) and hint.strip() for hint in hints)
    else:
        assert [hint["order"] for hint in hints] == [1, 2, 3]
        assert [hint["id"] for hint in hints] == ["hint-01", "hint-02", "hint-03"]
        assert all(hint["text"].strip() for hint in hints)

    prompts = db.query(InterviewPrompt).filter_by(certification_module_id=module.id).all()
    assert len(prompts) == 4
    for prompt in prompts:
        codes = {
            code
            for (code,) in db.query(CertificationObjective.objective_code)
            .join(
                InterviewPromptObjective,
                InterviewPromptObjective.objective_id == CertificationObjective.id,
            )
            .filter(InterviewPromptObjective.interview_prompt_id == prompt.id)
        }
        assert codes and prompt.expected_concepts and prompt.rubric and prompt.rubric_version


def test_modules13_15_sequence_mentor_multi_objective_and_coverage(db):
    load_module(db, commit=True)
    student = make_student(db, username="modules13_15_flow")
    keys = [row["module"]["key"] for row in entry_view(db, student.id)["modules"]]
    module13, module14, module15 = MODULES
    assert keys[keys.index(module13) : keys.index(module13) + 3] == [module13, module14, module15]

    for module_key in MODULES:
        available = {row["module_key"] for row in cohort_progress(db, module_key)["available_modules"]}
        assert set(MODULES) <= available
        progress = module_view(db, student.id, module_key)["progress"]
        assert progress["module_complete"] is False

    _, _, _, questions = _rows(db, module14)
    integrated = next(
        meta
        for question, meta in questions
        if "M14Q028" in (question.tags or [])
    )
    assert set(question_objective_codes(integrated)) == MODULES[module14]["objectives"]

    coverage = certification_version_coverage(db, "comptia_aplus_220-1202")
    assert coverage["covered_objectives"] == 28
    assert coverage["total_objectives"] == 36
    assert {row["objective_code"] for row in coverage["uncovered"]} == {
        "2.9", "4.3", "4.4", "4.5", "4.6", "4.8", "4.9", "4.10"
    }
