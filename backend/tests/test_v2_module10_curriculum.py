"""Runtime contracts for the reviewed A+ Module 10 curriculum package."""

from __future__ import annotations

import random
from collections import Counter

from sqlalchemy import or_

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
from app.services.v2_assessment_selector import select_constrained
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import entry_view, module_view, resource_activity
from app.services.v2_mentor_service import cohort_progress
from conftest import make_student


MODULE_KEY = "module.aplus.core1.virtualization_cloud_foundations"


def _rows(db):
    module = db.query(CertificationModule).filter_by(module_key=MODULE_KEY).one()
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


def test_module10_loads_reviewed_lessons_questions_and_assessments(db):
    load_module(db, commit=True)
    module, lessons, assessments, quiz_assessment, questions = _rows(db)
    assert module.display_order == 9
    assert len(lessons) == 5
    lesson_objectives = {
        code
        for (code,) in db.query(CertificationObjective.objective_code)
        .join(LessonObjective, LessonObjective.objective_id == CertificationObjective.id)
        .join(LessonV2Meta, LessonV2Meta.id == LessonObjective.lesson_v2_meta_id)
        .filter(LessonV2Meta.certification_module_id == module.id)
    }
    assert lesson_objectives == {"4.1", "4.2"}
    assert Counter(meta.question_type for _, meta in questions) == {
        "single": 24,
        "multi": 3,
        "short_answer": 2,
        "free_response": 1,
    }
    assert all(question.explanation for question, _ in questions)
    assert all(meta.source_name and meta.permission_status for _, meta in questions)
    assert sum(len(question_objective_codes(meta)) > 1 for _, meta in questions) == 1
    assert quiz_assessment.displayed_count == 12
    assert quiz_assessment.pass_percent == 70
    assert len([row for row in assessments if row.assessment_role == "quick_check"]) == 5
    assert next(row for row in assessments if row.assessment_role == "practical").lab_template_id
    assert not any(row.assessment_role == "service_desk" for row in assessments)


def test_module10_quiz_constraints_hold_across_randomized_selections(db):
    load_module(db, commit=True)
    _, _, _, assessment, questions = _rows(db)
    items = []
    for question, meta in questions:
        tags = list(question.tags or [])
        items.append(
            {
                "id": next(tag for tag in tags if str(tag).startswith("M10Q")),
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
        assert Counter(row["quota_index"] for row in selected) == {
            index: quota["count"]
            for index, quota in enumerate(config["question_blueprint"])
        }
        for requirement in config["category_requirements"]:
            assert sum(row["id"] in requirement["question_ids"] for row in selected) >= requirement["minimum"]
        requirements = config["selection_requirements"]
        assert sum(row["question_type"] == "multi" for row in selected) >= requirements["multi_select_minimum"]
        assert sum(
            any(
                label in row["question_style"]
                for label in ("scenario", "reasoning", "troubleshooting")
            )
            for row in selected
        ) >= requirements["scenario_application_or_reasoning_minimum"]
        assert max(Counter(row["category"] for row in selected).values()) <= requirements["max_same_narrow_category"]


def test_module10_resources_practical_and_explain_resolve(db):
    load_module(db, commit=True)
    module, lessons, assessments, _, _ = _rows(db)
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
    assert len(resources) == 7
    assert len(links) == 8
    assert sum(link.is_required for link in links) == 5
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


def test_module10_sequence_mentor_visibility_and_resource_mastery_separation(db):
    load_module(db, commit=True)
    student = make_student(db, username="module10_flow")
    keys = [row["module"]["key"] for row in entry_view(db, student.id)["modules"]]
    module9 = keys.index("module.aplus.core1.printers_mfds")
    assert keys[module9 : module9 + 2] == ["module.aplus.core1.printers_mfds", MODULE_KEY]

    cohort = cohort_progress(db, MODULE_KEY)
    assert MODULE_KEY in {row["module_key"] for row in cohort["available_modules"]}
    assert cohort["students"][0]["practical"]["status"] is None
    assert cohort["students"][0]["service_desk"] is None
    assert cohort["students"][0]["explain_status"] == "not_started"

    before = module_view(db, student.id, MODULE_KEY)["progress"]
    module_resource = module_view(db, student.id, MODULE_KEY)["module_resources"][0]
    resource_activity(db, student.id, MODULE_KEY, module_resource["key"], opened=True)
    required = next(
        resource
        for lesson in module_view(db, student.id, MODULE_KEY)["lessons"]
        for resource in lesson["resources"]
        if resource["required"]
    )
    resource_activity(db, student.id, MODULE_KEY, required["key"], opened=True)
    after = module_view(db, student.id, MODULE_KEY)["progress"]
    assert before["resources"]["required_completed"] == 0
    assert after["resources"]["required_completed"] == 0
    assert after["module_complete"] is False
