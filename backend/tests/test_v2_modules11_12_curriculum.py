"""Runtime contracts for the reviewed A+ Modules 11 and 12 packages."""

from __future__ import annotations

import random
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
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.v2_progress import V2_ACTIVITY_SERVICE_DESK, V2_STATUS_PASSED
from app.services.v2_assessment_selector import select_constrained
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import (
    assessment_is_available,
    entry_view,
    launch_service_desk,
    module_view,
    resource_activity,
    service_desk_scenario_is_playable,
)
from app.services.v2_mentor_service import cohort_progress
from app.services.v2_progress_service import V2ProgressError, record_activity
from conftest import enroll_v2, make_student


MODULES = {
    "module.aplus.core2.windows_admin_cli_networking": {
        "prefix": "M11Q",
        "lessons": 6,
        "questions": {"single": 28, "multi": 4, "short_answer": 2, "free_response": 2},
        "objectives": {"1.3", "1.4", "1.5", "1.7"},
        "resources": 10,
        "required": 6,
        "service_desk": "inc2505",
        "service_desk_available": True,
    },
    "module.aplus.core2.cross_platform_app_cloud_support": {
        "prefix": "M12Q",
        "lessons": 6,
        "questions": {"single": 24, "multi": 4, "short_answer": 2, "free_response": 2},
        "objectives": {"1.8", "1.9", "1.10", "1.11"},
        "resources": 9,
        "required": 6,
        "service_desk": "sd.aplus.cross_platform.unlicensed_suite_mac",
        "service_desk_available": False,
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
    return module, lessons, assessments, quiz_assessment, questions


@pytest.mark.parametrize("module_key", MODULES)
def test_modules11_12_load_all_reviewed_relationships_and_hints(
    db, monkeypatch, module_key
):
    seed_v2_foundation.run(db)
    expected = MODULES[module_key]
    module, lessons, assessments, quiz_assessment, questions = _rows(db, module_key)
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
    assert quiz_assessment.displayed_count == 12
    assert quiz_assessment.pass_percent == 70
    assert len([row for row in assessments if row.assessment_role == "quick_check"]) == 6
    assert next(row for row in assessments if row.assessment_role == "practical").lab_template_id

    service_desk = next(row for row in assessments if row.assessment_role == "service_desk")
    assert service_desk.active is expected["service_desk_available"]
    if expected["service_desk_available"]:
        assert "auto_deactivated_reason" not in service_desk.config
    else:
        assert service_desk.config["auto_deactivated_reason"] == "no_grading_profile"
    scenario = db.get(ServiceDeskScenario, service_desk.service_desk_scenario_id)
    assert scenario.stable_key == expected["service_desk"]
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=service_desk.service_desk_scenario_id, status="published")
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

    student = make_student(db, username=f"{expected['prefix'].lower()}_service_desk")
    enroll_v2(monkeypatch, student)
    if expected["service_desk_available"]:
        assert service_desk_scenario_is_playable(db, service_desk) is True
        assert assessment_is_available(db, service_desk, student.id) is False
        first = db.query(ModuleAssessment).filter_by(
            assessment_key="assess.aplus-core1-printers-mfds.service_desk"
        ).one()
        first_module = db.get(CertificationModule, first.certification_module_id)
        record_activity(
            db,
            student_id=student.id,
            module_key=first_module.module_key,
            activity_type=V2_ACTIVITY_SERVICE_DESK,
            ref_key=first.assessment_key,
            status=V2_STATUS_PASSED,
            score=100,
            passed=True,
            commit=True,
        )
        assert assessment_is_available(db, service_desk, student.id) is True
        launch = launch_service_desk(
            db, student.id, module_key, service_desk.assessment_key
        )
        assert launch == {
            "launch_url": (
                f"/service-desk/tickets/{expected['service_desk'].upper()}"
                f"?returnTo=/learning-v2/modules/{module_key}"
                f"&v2ModuleKey={module_key}"
                f"&v2AssessmentKey={service_desk.assessment_key}"
            ),
            "scenario_title": scenario.title,
            "mode": "learning",
            "experience_mode": "guided",
        }
        assignment = db.query(ServiceDeskAssignment).filter_by(
            student_id=student.id,
            scenario_id=scenario.id,
            mode="learning",
        ).one()
        assert assignment.assigned_by == (
            f"v2_curriculum:{module_key}:{service_desk.assessment_key}"
        )
        assert assignment.is_required is True
        assert assignment.maximum_attempts == 3
    else:
        assert service_desk_scenario_is_playable(db, service_desk) is False
        assert assessment_is_available(db, service_desk, student.id) is False
        with pytest.raises(V2ProgressError, match="not available"):
            launch_service_desk(db, student.id, module_key, service_desk.assessment_key)


@pytest.mark.parametrize("module_key", MODULES)
def test_modules11_12_quiz_constraints_hold_across_randomized_selections(db, module_key):
    load_module(db, commit=True)
    expected = MODULES[module_key]
    _, _, _, assessment, questions = _rows(db, module_key)
    items = []
    for question, meta in questions:
        tags = list(question.tags or [])
        items.append(
            {
                "id": next(tag for tag in tags if str(tag).startswith(expected["prefix"])),
                "objective_codes": question_objective_codes(meta),
                "tags": tags,
                "question_type": meta.question_type,
                "question_style": next(
                    (
                        str(tag).split(":", 1)[1]
                        for tag in tags
                        if str(tag).startswith("question_style:")
                    ),
                    "",
                ),
                "category": next(
                    (
                        str(tag).split(":", 1)[1]
                        for tag in tags
                        if str(tag).startswith("category:")
                    ),
                    "",
                ),
            }
        )
    config = assessment.config
    for seed in range(50):
        selected = select_constrained(
            items,
            config["question_blueprint"],
            config["category_requirements"],
            excluded_ids=set(config["exclude_question_ids"]),
            selection_requirements=config["selection_requirements"],
            rng=random.Random(seed),
        )
        assert len(selected) == len({row["id"] for row in selected}) == 12
        assert Counter(row["quota_index"] for row in selected) == {
            index: quota["count"]
            for index, quota in enumerate(config["question_blueprint"])
        }
        for requirement in config["category_requirements"]:
            assert sum(
                row["id"] in requirement["question_ids"] for row in selected
            ) >= requirement["minimum"]
        requirements = config["selection_requirements"]
        assert sum(row["question_type"] == "multi" for row in selected) >= requirements[
            "multi_select_minimum"
        ]
        assert sum(
            any(
                label in row["question_style"]
                for label in ("scenario", "reasoning", "troubleshooting")
            )
            for row in selected
        ) >= requirements["scenario_application_or_reasoning_minimum"]
        assert max(Counter(row["category"] for row in selected).values()) <= requirements[
            "max_same_narrow_category"
        ]


@pytest.mark.parametrize("module_key", MODULES)
def test_modules11_12_resources_practical_and_explain_resolve(db, module_key):
    load_module(db, commit=True)
    expected = MODULES[module_key]
    module, lessons, assessments, _, _ = _rows(db, module_key)
    lesson_ids = [lesson.id for lesson in lessons]
    links = db.query(LearningResourceLink).filter(
        or_(
            LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids),
            LearningResourceLink.certification_module_id == module.id,
        )
    ).all()
    resources = {
        row.id: row
        for row in db.query(LearningResource).filter(
            LearningResource.id.in_({link.resource_id for link in links})
        )
    }
    assert len(resources) == expected["resources"]
    assert len(links) == expected["resources"]
    assert sum(link.is_required for link in links) == expected["required"]
    assert all(resource.title and resource.provider and resource.url for resource in resources.values())
    assert all(link.display_order > 0 for link in links)
    assert next(row for row in assessments if row.assessment_role == "practical").lab_template_id

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


def test_modules10_12_sequence_mentor_visibility_and_resource_mastery_separation(db):
    load_module(db, commit=True)
    student = make_student(db, username="modules11_12_flow")
    keys = [row["module"]["key"] for row in entry_view(db, student.id)["modules"]]
    module10 = "module.aplus.core1.virtualization_cloud_foundations"
    module11, module12 = MODULES
    assert keys.index(module10) < keys.index(module11)
    assert keys[keys.index(module11) : keys.index(module11) + 2] == [module11, module12]

    for module_key in MODULES:
        cohort = cohort_progress(db, module_key)
        available = {row["module_key"] for row in cohort["available_modules"]}
        assert set(MODULES) <= available
        assert cohort["students"][0]["practical"]["status"] is None
        assert cohort["students"][0]["service_desk"] is None
        assert cohort["students"][0]["explain_status"] == "not_started"

    module_key = module11
    before = module_view(db, student.id, module_key)["progress"]
    required = next(
        resource
        for lesson in module_view(db, student.id, module_key)["lessons"]
        for resource in lesson["resources"]
        if resource["required"]
    )
    resource_activity(db, student.id, module_key, required["key"], opened=True)
    after = module_view(db, student.id, module_key)["progress"]
    assert before["resources"]["required_completed"] == 0
    assert after["resources"]["required_completed"] == 0
    assert after["module_complete"] is False
