"""Runtime contracts for reviewed A+ Module 5 imported through the dropbox."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from pathlib import Path

import yaml

import seed_v2_foundation
from app.models.certification import (
    CertificationModule,
    CertificationObjective,
    InterviewPrompt,
    InterviewPromptObjective,
    LearningResourceLink,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
    question_objective_codes,
)
from app.models.quiz import Question, Quiz
from app.models.service_desk import ServiceDeskScenario
from app.services.v2_assessment_selector import select_constrained


MODULE_KEY = "module.aplus.core2.service_desk_workflow"
QUIZ_TITLE = "Module 5 Quiz — Service Desk Workflow"
SCENARIO_KEY = "inc2506"


def _loaded_module(db):
    seed_v2_foundation.run(db)
    return db.query(CertificationModule).filter_by(module_key=MODULE_KEY).one()


def test_module5_components_objectives_and_editorial_hash(db):
    module = _loaded_module(db)
    lessons = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).all()
    assert len(lessons) == 6

    quiz = db.query(Quiz).filter_by(title=QUIZ_TITLE).one()
    pairs = (
        db.query(Question, QuestionV2Meta)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(Question.quiz_id == quiz.id)
        .all()
    )
    assert len(pairs) == 35
    assert Counter(meta.question_type for _, meta in pairs) == {
        "single": 29,
        "multi": 3,
        "short_answer": 2,
        "free_response": 1,
    }
    by_qid = {
        next(tag for tag in question.tags if str(tag).startswith("Q")): meta
        for question, meta in pairs
    }
    for qid in ("Q002", "Q025", "Q026"):
        assert question_objective_codes(by_qid[qid]) == ["4.1", "4.7"]
    assert by_qid["Q030"].acceptable_answers
    assert by_qid["Q031"].acceptable_answers
    assert len(by_qid["Q032"].expected_concepts) == 10

    approvals_path = Path("content/questions/editorial-approvals.yaml")
    approval = next(
        row
        for row in yaml.safe_load(approvals_path.read_text())["approvals"]
        if row["filename"] == "module-aplus-core2-service-desk-workflow.csv"
    )
    bank = Path("content/questions/module-aplus-core2-service-desk-workflow.csv")
    assert approval["reviewed_question_count"] == 35
    assert hashlib.sha256(bank.read_bytes()).hexdigest() == approval["sha256"]
    assert quiz.editorial_status == "validated"
    assert quiz.answer_keys_validated is True
    assert quiz.explanations_complete is True


def test_module5_assessments_resources_and_explain_relationships(db):
    module = _loaded_module(db)
    assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id).all()
    quick_checks = [row for row in assessments if row.assessment_role == "quick_check"]
    assert len(quick_checks) == 6
    assert all(row.quiz_id and row.lesson_v2_meta_id for row in quick_checks)

    module_quiz = next(row for row in assessments if row.assessment_role == "module_quiz")
    practical = next(row for row in assessments if row.assessment_role == "practical")
    service_desk = next(row for row in assessments if row.assessment_role == "service_desk")
    assert (module_quiz.displayed_count, module_quiz.pass_percent) == (12, 70)
    assert practical.lab_template_id is not None
    assert service_desk.service_desk_scenario_id is not None
    assert db.query(ServiceDeskScenario).filter_by(stable_key=SCENARIO_KEY).one().id == (
        service_desk.service_desk_scenario_id
    )

    quiz = db.get(Quiz, module_quiz.quiz_id)
    pairs = (
        db.query(Question, QuestionV2Meta)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(Question.quiz_id == quiz.id, QuestionV2Meta.question_type != "free_response")
        .all()
    )
    items = [
        {
            "id": str(question.id),
            "objective_codes": question_objective_codes(meta),
            "tags": list(question.tags or []),
        }
        for question, meta in pairs
    ]
    for seed in range(10):
        selected = select_constrained(
            items,
            module_quiz.config["question_blueprint"],
            module_quiz.config["category_requirements"],
            excluded_ids=set(module_quiz.config.get("exclude_question_ids") or []),
            rng=random.Random(seed),
        )
        assert len(selected) == len({row["id"] for row in selected}) == 12
        assert Counter(row["quota_index"] for row in selected) == {0: 5, 1: 4, 2: 3}
        for requirement in module_quiz.config["category_requirements"]:
            assert sum(
                bool(set(row["tags"]) & set(requirement["tags_any"])) for row in selected
            ) >= requirement["minimum"]

    lesson_ids = [
        row.id
        for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)
    ]
    links = db.query(LearningResourceLink).filter(
        LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids)
    ).all()
    assert len({row.resource_id for row in links}) == 6
    assert len(links) == 8

    prompts = db.query(InterviewPrompt).filter_by(
        certification_module_id=module.id
    ).order_by(InterviewPrompt.prompt_key).all()
    assert len(prompts) == 4
    expected = ["4.1", "4.1", "4.2", "4.7"]
    actual = []
    for prompt in prompts:
        codes = [
            code
            for (code,) in db.query(CertificationObjective.objective_code)
            .join(
                InterviewPromptObjective,
                InterviewPromptObjective.objective_id == CertificationObjective.id,
            )
            .filter(InterviewPromptObjective.interview_prompt_id == prompt.id)
        ]
        assert prompt.expected_concepts and prompt.rubric and prompt.rubric_version
        actual.append(codes[0])
    assert actual == expected
