"""The V2 foundation load is one logical transaction.

``seed_v2_foundation.py`` used to commit after each stage, so a failure
between stages could leave the certification hierarchy loaded with its
content missing — modules with no lessons, assessments pointing at quizzes
that were never imported. The V2 flag being off limited the blast radius, but
the half-loaded state was real. The load now validates and commits exactly
once, and rolls back to the pre-load state on any failure.
"""

import pytest

import seed_v2_foundation
from app.models.certification import (
    Certification,
    CertificationModule,
    InterviewPrompt,
    LearningResource,
    LessonV2Meta,
    ModuleAssessment,
)
from app.models.lab import LabTemplate
from app.models.quiz import Question, Quiz
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services import v2_content_loader
from app.services.v2_content_loader import ContentValidationError, load_module

COUNTED = (
    Certification, CertificationModule, LessonV2Meta, ModuleAssessment,
    LearningResource, InterviewPrompt, Quiz, Question, LabTemplate,
    ServiceDeskScenario,
)


def _census(db) -> dict:
    return {model.__name__: db.query(model).count() for model in COUNTED}


def _empty(census: dict) -> bool:
    return all(count == 0 for count in census.values())


# --------------------------------------------------------------------------- #
# Failure injected at each stage leaves nothing behind
# --------------------------------------------------------------------------- #

class _Boom(RuntimeError):
    pass


@pytest.mark.parametrize(
    "target",
    [
        "load_certifications",     # hierarchy
        "load_resources",          # lessons / resources
        "load_question_banks",     # question import
        "load_labs",               # assessment binding (practical)
        "load_service_desk_scenarios",  # Service Desk binding
    ],
)
def test_a_failure_at_any_stage_commits_nothing(db, monkeypatch, target):
    before = _census(db)
    assert _empty(before), "fixture database should start empty"

    real = getattr(v2_content_loader, target)
    calls = {"n": 0}

    def explode(*args, **kwargs):
        calls["n"] += 1
        # Let the stage do real work first, then fail, so the rollback has
        # something to undo rather than trivially succeeding.
        real(*args, **kwargs)
        raise _Boom(f"injected failure in {target}")

    monkeypatch.setattr(v2_content_loader, target, explode)

    with pytest.raises(_Boom):
        seed_v2_foundation.run(db)

    assert calls["n"] >= 1, "injected failure never fired"
    db.rollback()
    assert _census(db) == before


def test_validation_failure_rolls_the_whole_load_back(db, monkeypatch):
    """An unresolved assessment reference must not be committed."""
    before = _census(db)

    monkeypatch.setattr(
        seed_v2_foundation, "validate_loaded_content",
        lambda db_, summary: ["student-visible module 'x' has unresolved content references: y"],
    )
    with pytest.raises(ContentValidationError):
        seed_v2_foundation.run(db)

    db.rollback()
    assert _census(db) == before


def test_validation_rejects_a_load_that_produced_no_assessments(db):
    problems = seed_v2_foundation.validate_loaded_content(db, {
        "references": {"content_engine_assessments": 0, "content_engine_unresolved": []}
    })
    assert "no content-backed module assessments were loaded" in problems


def test_validation_fails_a_student_visible_module_with_a_broken_reference(db):
    """A module students can reach must be fully wired, or the load aborts."""
    load_module(db, commit=False)
    module = db.query(CertificationModule).filter_by(
        module_key="module.aplus.core1.network_services_troubleshooting"
    ).one()
    quiz_backed = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="module_quiz"
    ).one()
    quiz_backed.quiz_id = None
    db.flush()

    problems = seed_v2_foundation.validate_loaded_content(db, {
        "references": {"content_engine_assessments": 118}
    })
    assert any(quiz_backed.assessment_key in problem for problem in problems)
    db.rollback()


def test_validation_tolerates_a_module_still_being_authored(db):
    """An incomplete module is invisible to students, not a load failure.

    ``networking_fundamentals`` has lessons and quiz-less assessments but no
    practical, so the entry page never surfaces it. Blocking the load on it
    would make every future authoring step un-loadable.
    """
    load_module(db, commit=False)
    problems = seed_v2_foundation.validate_loaded_content(db, {
        "references": {"content_engine_assessments": 118}
    })
    assert problems == []
    db.rollback()


def test_validation_rejects_an_unpublished_required_service_desk_scenario(db):
    summary = seed_v2_foundation.run(db)
    assessment = db.query(ModuleAssessment).filter_by(
        assessment_key="assess.aplus.ipcfg.service_desk"
    ).one()
    db.query(ServiceDeskScenarioVersion).filter_by(
        scenario_id=assessment.service_desk_scenario_id,
        status="published",
    ).update({"status": "disabled"})
    db.flush()

    problems = seed_v2_foundation.validate_loaded_content(db, summary)

    assert any(
        "assess.aplus.ipcfg.service_desk" in problem
        and "no published scenario version" in problem
        for problem in problems
    )


# --------------------------------------------------------------------------- #
# The success path
# --------------------------------------------------------------------------- #

def test_a_successful_load_commits_everything_once(db):
    assert _empty(_census(db))
    summary = seed_v2_foundation.run(db)

    after = _census(db)
    assert not _empty(after)
    # Everything except the module that is still being authored resolved.
    assert set(summary["references"]["content_engine_unresolved"]) == {
        "assess.aplus.core1.networking_fundamentals.quick_check",
        "assess.aplus.core1.networking_fundamentals.module_quiz",
    }
    assert seed_v2_foundation.validate_loaded_content(db, summary) == []


def test_a_second_load_is_idempotent(db):
    seed_v2_foundation.run(db)
    first = _census(db)

    second_summary = seed_v2_foundation.run(db)
    assert _census(db) == first
    assert second_summary["created"] == 0


def test_dry_run_validates_and_writes_nothing(db):
    before = _census(db)
    seed_v2_foundation.run(db, dry_run=True)
    db.rollback()
    assert _census(db) == before


def test_load_module_without_commit_leaves_the_transaction_open(db):
    """The question importer must not commit behind the caller's back."""
    load_module(db, commit=False)
    assert db.query(Question).count() > 0
    db.rollback()
    assert db.query(Question).count() == 0
    assert db.query(Quiz).count() == 0
