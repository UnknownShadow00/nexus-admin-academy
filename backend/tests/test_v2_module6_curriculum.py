"""Runtime contracts for reviewed A+ Module 6 imported through the dropbox."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from pathlib import Path

import yaml
from sqlalchemy import or_

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
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services.v2_assessment_selector import select_constrained
from app.services.v2_content_loader import load_module


MODULE_KEY = "module.aplus.core1.mobile_device_support"
QUIZ_TITLE = "Module 6 Quiz — Mobile Device Support"
SCENARIO_KEY = "service_desk.aplus.mobile.intermittent_charge_mail_sync"


def _loaded_module(db):
    load_module(db, commit=True)
    return db.query(CertificationModule).filter_by(module_key=MODULE_KEY).one()


def test_module6_lessons_questions_objectives_and_editorial_hash(db):
    module = _loaded_module(db)
    lessons = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).all()
    assert len(lessons) == 6

    quick_checks = (
        db.query(ModuleAssessment)
        .filter_by(certification_module_id=module.id, assessment_role="quick_check")
        .order_by(ModuleAssessment.display_order)
        .all()
    )
    assert [row.lesson_v2_meta_id for row in quick_checks] == [
        next(lesson.id for lesson in lessons if lesson.lesson_key == key)
        for key in (
            "lesson.aplus.mobile.hardware_safe_service",
            "lesson.aplus.mobile.ports_accessories_docking",
            "lesson.aplus.mobile.connectivity_radios",
            "lesson.aplus.mobile.mdm_sync",
            "lesson.aplus.mobile.physical_power_troubleshooting",
            "lesson.aplus.mobile.connectivity_app_performance_troubleshooting",
        )
    ]

    quiz = db.query(Quiz).filter_by(title=QUIZ_TITLE).one()
    pairs = (
        db.query(Question, QuestionV2Meta)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(Question.quiz_id == quiz.id)
        .all()
    )
    assert len(pairs) == 36
    assert Counter(meta.question_type for _, meta in pairs) == {
        "single": 30,
        "multi": 4,
        "short_answer": 1,
        "free_response": 1,
    }
    by_qid = {
        next(tag for tag in question.tags if str(tag).startswith("Q")): meta
        for question, meta in pairs
    }
    expected_multi = {
        "Q006": ["1.1", "5.4"],
        "Q011": ["1.2", "1.3"],
        "Q013": ["1.2", "5.4"],
        "Q019": ["1.3", "5.4"],
        "Q026": ["1.1", "5.4"],
        "Q027": ["1.2", "5.4"],
        "Q033": ["1.3", "5.4"],
        "Q034": ["1.3", "5.4"],
        "Q036": ["1.3", "5.4"],
    }
    assert {qid: question_objective_codes(by_qid[qid]) for qid in expected_multi} == expected_multi
    short_answer = next(meta for _, meta in pairs if meta.question_type == "short_answer")
    free_response = next(meta for _, meta in pairs if meta.question_type == "free_response")
    assert short_answer.acceptable_answers
    assert free_response.expected_concepts and free_response.rubric
    assert free_response.min_concepts_for_pass == 5

    approvals_path = Path("content/questions/editorial-approvals.yaml")
    approval = next(
        row
        for row in yaml.safe_load(approvals_path.read_text())["approvals"]
        if row["filename"] == "module-aplus-core1-mobile-device-support.csv"
    )
    bank = Path("content/questions/module-aplus-core1-mobile-device-support.csv")
    assert approval["reviewed_question_count"] == 36
    assert hashlib.sha256(bank.read_bytes()).hexdigest() == approval["sha256"]
    assert quiz.editorial_status == "validated"
    assert quiz.answer_keys_validated is True
    assert quiz.explanations_complete is True


def test_module6_assessments_resources_service_desk_and_explain(db):
    module = _loaded_module(db)
    assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id).all()
    quick_checks = [row for row in assessments if row.assessment_role == "quick_check"]
    assert len(quick_checks) == 6
    assert all(row.quiz_id and row.lesson_v2_meta_id and row.displayed_count == 4 for row in quick_checks)

    module_quiz = next(row for row in assessments if row.assessment_role == "module_quiz")
    practical = next(row for row in assessments if row.assessment_role == "practical")
    service_desk = next(row for row in assessments if row.assessment_role == "service_desk")
    assert (module_quiz.displayed_count, module_quiz.pass_percent) == (12, 70)
    assert practical.lab_template_id is not None
    assert service_desk.service_desk_scenario_id is not None
    scenario = db.query(ServiceDeskScenario).filter_by(stable_key=SCENARIO_KEY).one()
    assert scenario.id == service_desk.service_desk_scenario_id
    version = db.query(ServiceDeskScenarioVersion).filter_by(
        scenario_id=scenario.id, status="published"
    ).one()
    assert list(version.definition_json["rubric_dimensions"]) == [
        "Investigation",
        "Diagnosis",
        "Remediation",
        "Verification",
        "Documentation",
    ]

    quiz = db.get(Quiz, module_quiz.quiz_id)
    pairs = (
        db.query(Question, QuestionV2Meta)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(Question.quiz_id == quiz.id, QuestionV2Meta.question_type != "free_response")
        .all()
    )
    items = [
        {
            "id": next(tag for tag in question.tags if str(tag).startswith("Q")),
            "objective_codes": question_objective_codes(meta),
            "tags": list(question.tags or []),
        }
        for question, meta in pairs
    ]
    for seed in range(20):
        selected = select_constrained(
            items,
            module_quiz.config["question_blueprint"],
            module_quiz.config["category_requirements"],
            excluded_ids=set(module_quiz.config.get("exclude_question_ids") or []),
            rng=random.Random(seed),
        )
        assert len(selected) == len({row["id"] for row in selected}) == 12
        assert Counter(row["quota_index"] for row in selected) == {0: 3, 1: 2, 2: 4, 3: 3}
        for requirement in module_quiz.config["category_requirements"]:
            assert sum(
                bool(set(row["tags"]) & set(requirement["tags_any"])) for row in selected
            ) >= requirement["minimum"]

    lesson_ids = [lesson.id for lesson in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
    links = db.query(LearningResourceLink).filter(
        or_(
            LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids),
            LearningResourceLink.certification_module_id == module.id,
        )
    ).all()
    assert len({row.resource_id for row in links}) == 10
    assert len(links) == 12
    assert any(row.lesson_v2_meta_id is None and row.certification_module_id == module.id for row in links)

    prompts = db.query(InterviewPrompt).filter_by(certification_module_id=module.id).all()
    assert len(prompts) == 4
    expected = {
        "explain.aplus.mobile.swollen_battery": {"1.1", "5.4"},
        "explain.aplus.mobile.wifi_isolation": {"1.3", "5.4"},
        "explain.aplus.mobile.mdm": {"1.3"},
        "explain.aplus.mobile.sim_esim_wifi": {"1.3"},
    }
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
        assert codes == expected[prompt.prompt_key]
        assert prompt.expected_concepts and prompt.rubric and prompt.rubric_version == "module6-explain-v1"
