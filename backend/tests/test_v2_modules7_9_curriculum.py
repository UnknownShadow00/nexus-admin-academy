"""Runtime contracts for the reviewed A+ Modules 7–9 curriculum batch."""

from __future__ import annotations

import random
from collections import Counter

from sqlalchemy import or_

import seed_v2_foundation
from app.models.certification import (
    CertificationModule,
    CertificationDomain,
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
from app.services.service_desk_objectives import objective_definition
from app.services.v2_assessment_selector import select_constrained
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import entry_view, module_view, resource_activity
from app.services.v2_mentor_service import cohort_progress
from conftest import make_student


MODULES = {
    "module.aplus.core1.network_services_troubleshooting": {
        "order": 6,
        "domain": "2.0",
        "objectives": {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "5.5"},
        "lessons": 7,
        "questions": {"single": 32, "multi": 4, "short_answer": 2, "free_response": 2},
        "resources": (12, 8, 4),
        "scenario": "service_desk.aplus.network.loading_dock_wifi",
        "service_desk_available": False,
    },
    "module.aplus.core1.hardware_fault_isolation": {
        "order": 7,
        "domain": "3.0",
        "objectives": {"3.1", "3.2", "3.3", "3.6", "5.1", "5.2", "5.3"},
        "lessons": 6,
        "questions": {"single": 29, "multi": 3, "short_answer": 2, "free_response": 2},
        "resources": (15, 12, 3),
        "scenario": "service_desk.aplus.hardware.render_shutdown",
        "service_desk_available": False,
    },
    "module.aplus.core1.printers_mfds": {
        "order": 8,
        "domain": "3.0",
        "objectives": {"3.7", "3.8", "5.6"},
        "lessons": 5,
        "questions": {"single": 24, "multi": 3, "short_answer": 2, "free_response": 1},
        "resources": (12, 6, 9),
        "scenario": "inc2504",
        "service_desk_available": True,
    },
}


def _module_rows(db, module_key):
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


def test_modules7_9_load_with_reviewed_relationships_and_assessments(db):
    seed_v2_foundation.run(db)
    for module_key, expected in MODULES.items():
        module, lessons, assessments, quiz_assessment, questions = _module_rows(db, module_key)
        assert module.display_order == expected["order"]
        assert db.get(CertificationDomain, module.certification_domain_id).domain_key == expected["domain"]
        assert len(lessons) == expected["lessons"]
        lesson_objectives = {
            code
            for (code,) in db.query(CertificationObjective.objective_code)
            .join(LessonObjective, LessonObjective.objective_id == CertificationObjective.id)
            .join(LessonV2Meta, LessonV2Meta.id == LessonObjective.lesson_v2_meta_id)
            .filter(LessonV2Meta.certification_module_id == module.id)
        }
        assert lesson_objectives == expected["objectives"]
        assert Counter(meta.question_type for _, meta in questions) == expected["questions"]
        assert all(meta.source_name and meta.permission_status for _, meta in questions)
        assert all(question.explanation for question, _ in questions)
        assert all(question_objective_codes(meta) for _, meta in questions)
        assert sum(len(question_objective_codes(meta)) > 1 for _, meta in questions) > 0
        assert quiz_assessment.displayed_count == 12
        assert quiz_assessment.pass_percent == 70
        assert len([row for row in assessments if row.assessment_role == "quick_check"]) == len(lessons)
        assert all(
            row.quiz_id and row.lesson_v2_meta_id
            for row in assessments
            if row.assessment_role == "quick_check"
        )
        assert next(row for row in assessments if row.assessment_role == "practical").lab_template_id
        assert next(row for row in assessments if row.assessment_role == "service_desk").service_desk_scenario_id


def test_modules7_9_quiz_constraints_hold_across_randomized_selections(db):
    load_module(db, commit=True)
    for module_key in MODULES:
        _, _, _, assessment, questions = _module_rows(db, module_key)
        items = []
        for question, meta in questions:
            tags = list(question.tags or [])
            items.append(
                {
                    "id": next(tag for tag in tags if str(tag).startswith("M")),
                    "objective_codes": question_objective_codes(meta),
                    "tags": tags,
                    "question_type": meta.question_type,
                    "question_style": next(
                        (str(tag).split(":", 1)[1] for tag in tags if str(tag).startswith("question_style:")),
                        "",
                    ),
                    "category": next(
                        (str(tag).split(":", 1)[1] for tag in tags if str(tag).startswith("category:")),
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
            assert not ({row["id"] for row in selected} & set(config["exclude_question_ids"]))


def test_modules7_9_resources_practicals_service_desk_and_explain_resolve(db):
    seed_v2_foundation.run(db)
    for module_key, expected in MODULES.items():
        module, lessons, assessments, _, _ = _module_rows(db, module_key)
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
        total, required, optional = expected["resources"]
        assert len(resources) == total
        assert sum(link.is_required for link in links) == required
        assert sum(not link.is_required for link in links) == optional
        assert all(resource.title and resource.provider and resource.url for resource in resources.values())
        assert all(link.display_order > 0 for link in links)

        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=expected["scenario"]).one()
        version = db.query(ServiceDeskScenarioVersion).filter_by(
            scenario_id=scenario.id, status="published"
        ).one()
        service_desk = next(
            row for row in assessments if row.assessment_role == "service_desk"
        )
        assert service_desk.active is expected["service_desk_available"]
        if expected["service_desk_available"]:
            objective = objective_definition(
                scenario.stable_key, version.definition_json
            )
            assert objective is not None
            assert {category.name for category in objective.categories} == {
                "investigation",
                "diagnosis",
                "remediation",
                "verification",
                "documentation",
            }
        else:
            assert set(version.definition_json["rubric_dimensions"]) == {
                "Investigation",
                "Diagnosis",
                "Remediation",
                "Verification",
                "Documentation",
            }
            assert version.definition_json["successful_professional_outcomes"]

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


def test_student_sequence_advances_from_module6_through_modules7_9(db):
    load_module(db, commit=True)
    student = make_student(db, username="modules7_9_sequence")
    keys = [row["module"]["key"] for row in entry_view(db, student.id)["modules"]]
    sequence = [
        "module.aplus.core1.mobile_device_support",
        "module.aplus.core1.network_services_troubleshooting",
        "module.aplus.core1.hardware_fault_isolation",
        "module.aplus.core1.printers_mfds",
    ]
    start = keys.index(sequence[0])
    assert keys[start : start + 4] == sequence


def test_new_modules_are_mentor_visible_and_opening_resources_is_not_mastery(db):
    load_module(db, commit=True)
    student = make_student(db, username="modules7_9_mentor")
    module_key = "module.aplus.core1.network_services_troubleshooting"
    cohort = cohort_progress(db, module_key)
    available = {row["module_key"] for row in cohort["available_modules"]}
    assert set(MODULES) <= available
    assert cohort["students"][0]["practical"] is not None
    assert cohort["students"][0]["practical"]["status"] is None
    assert cohort["students"][0]["service_desk"] is not None
    assert cohort["students"][0]["service_desk"]["status"] is None
    assert cohort["students"][0]["explain_status"] == "not_started"

    before = module_view(db, student.id, module_key)["progress"]
    module_resource = module_view(db, student.id, module_key)["module_resources"][0]
    assert module_resource["required"] is False
    resource_activity(db, student.id, module_key, module_resource["key"], opened=True)
    first_required = next(
        resource
        for lesson in module_view(db, student.id, module_key)["lessons"]
        for resource in lesson["resources"]
        if resource["required"]
    )
    resource_activity(db, student.id, module_key, first_required["key"], opened=True)
    after = module_view(db, student.id, module_key)["progress"]
    assert before["resources"]["required_completed"] == 0
    assert after["resources"]["required_completed"] == 0
    assert after["module_complete"] is False
