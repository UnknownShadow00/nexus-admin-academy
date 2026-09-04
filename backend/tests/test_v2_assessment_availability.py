"""Availability and openability are one contract.

An assessment card that says "available" and then refuses to open is a dead
end for the student. ``_assessment_view`` used to decide availability from the
mere presence of ``quiz_id`` while opening the quiz went through the far
stricter ``student_visible_quiz_filters``. Anything blocked by editorial
review — the A+ IP Configuration bank, for one — landed in that gap.

These tests pin both halves to the same rule and prove Continue never routes
into an activity the server would refuse.
"""

import pytest
from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import CertificationModule, InterviewPrompt, ModuleAssessment
from app.models.quiz import (
    EDITORIAL_STATUS_UNREVIEWED,
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_STATUS_DRAFT,
    QUIZ_STATUS_PUBLISHED,
    Quiz,
)
from app.routers.v2_curriculum import router as curriculum_router
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import (
    assessment_is_available,
    module_view,
    quiz_is_student_visible,
)
from app.services.v2_progress_service import record_activity

MODULE = "module.aplus.core1.network_services_troubleshooting"


def _ready(db, monkeypatch):
    load_module(db, commit=True)
    student = make_student(db, username="availability_student")
    enroll_v2(monkeypatch, student)
    return student, make_client(curriculum_router)


def _module_quiz(db) -> ModuleAssessment:
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    return db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_role="module_quiz"
    ).one()


def _assessment_card(view: dict, key: str) -> dict:
    return next(item for item in view["assessments"] if item["key"] == key)


# --------------------------------------------------------------------------- #
# Availability mirrors student visibility, blocker by blocker
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "field, value",
    [
        ("status", QUIZ_STATUS_DRAFT),
        ("is_active", False),
        ("editorial_status", EDITORIAL_STATUS_UNREVIEWED),
        ("answer_keys_validated", False),
    ],
    ids=["draft", "inactive", "editorially-unvalidated", "answer-key-unvalidated"],
)
def test_a_blocked_quiz_is_never_reported_available(db, monkeypatch, field, value):
    student, _ = _ready(db, monkeypatch)
    assessment = _module_quiz(db)
    quiz = db.get(Quiz, assessment.quiz_id)
    setattr(quiz, field, value)
    db.commit()

    assert quiz_is_student_visible(db, assessment.quiz_id) is False
    assert assessment_is_available(db, assessment) is False

    card = _assessment_card(module_view(db, student.id, MODULE), assessment.assessment_key)
    assert card["available"] is False
    assert card["unavailable"]["reason"] == "This knowledge check is not available yet."


def test_a_valid_published_quiz_is_available(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    assessment = _module_quiz(db)
    quiz = db.get(Quiz, assessment.quiz_id)
    quiz.status = QUIZ_STATUS_PUBLISHED
    quiz.is_active = True
    quiz.editorial_status = EDITORIAL_STATUS_VALIDATED
    quiz.answer_keys_validated = True
    db.commit()

    assert assessment_is_available(db, assessment) is True
    card = _assessment_card(module_view(db, student.id, MODULE), assessment.assessment_key)
    assert card["available"] is True
    assert card["unavailable"] is None


def test_a_missing_quiz_id_is_still_unavailable(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    assessment = _module_quiz(db)
    assessment.quiz_id = None
    db.commit()
    assert assessment_is_available(db, assessment) is False


def test_the_blocked_reason_is_safe_for_students(db, monkeypatch):
    """A student is never told a bank is awaiting editorial approval."""
    student, _ = _ready(db, monkeypatch)
    assessment = _module_quiz(db)
    quiz = db.get(Quiz, assessment.quiz_id)
    quiz.editorial_status = EDITORIAL_STATUS_UNREVIEWED
    db.commit()

    card = _assessment_card(module_view(db, student.id, MODULE), assessment.assessment_key)
    blob = str(card).lower()
    for leaked in ("editorial", "approval", "answer_key", "unreviewed", "draft"):
        assert leaked not in blob


# --------------------------------------------------------------------------- #
# Continue must never point at a dead end
# --------------------------------------------------------------------------- #

def _finish_everything_before_the_module_quiz(db, student):
    view = module_view(db, student.id, MODULE)
    for lesson in view["lessons"]:
        for resource in lesson["resources"]:
            if resource["required"]:
                from app.services.v2_curriculum_service import resource_activity
                resource_activity(db, student.id, MODULE, resource["key"], opened=True, completed=True)
        record_activity(
            db, student_id=student.id, module_key=MODULE,
            activity_type="lesson", ref_key=lesson["key"], status="completed", commit=True,
        )
        if lesson["quick_check"]:
            record_activity(
                db, student_id=student.id, module_key=MODULE,
                activity_type="quick_check", ref_key=lesson["quick_check"]["key"],
                status="passed", commit=True,
            )


def test_continue_skips_an_unopenable_module_quiz(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    assessment = _module_quiz(db)
    quiz = db.get(Quiz, assessment.quiz_id)
    quiz.editorial_status = EDITORIAL_STATUS_UNREVIEWED
    db.commit()
    _finish_everything_before_the_module_quiz(db, student)

    resolved = module_view(db, student.id, MODULE)["continue"]
    # The next still-open activity is the practical, not the blocked quiz.
    assert resolved["kind"] == "practical"
    assert resolved["available"] is True


def test_continue_never_routes_to_an_unavailable_activity(db, monkeypatch):
    """Whatever Continue picks, the student must be able to open it."""
    student, _ = _ready(db, monkeypatch)
    for assessment in db.query(ModuleAssessment).filter(
        ModuleAssessment.quiz_id.isnot(None)
    ).all():
        quiz = db.get(Quiz, assessment.quiz_id)
        quiz.editorial_status = EDITORIAL_STATUS_UNREVIEWED
        db.commit()
    _finish_everything_before_the_module_quiz(db, student)

    view = module_view(db, student.id, MODULE)
    resolved = view["continue"]
    assert resolved["kind"] not in {"quick_check", "module_quiz"}
    # Every quiz-backed card is reported unavailable, and Continue picked
    # something else entirely rather than one of them.
    blocked_keys = {
        item["key"] for item in view["assessments"] if item["available"] is False
    }
    assert blocked_keys
    assert all(key not in resolved["route"] for key in blocked_keys)


def test_continue_blocks_safely_when_nothing_openable_remains(db, monkeypatch):
    """The terminal case: every remaining activity is blocked.

    Continue must not invent a route into any of them — it points back at the
    module and carries the same safe, non-diagnostic explanation.
    """
    student, _ = _ready(db, monkeypatch)
    for assessment in db.query(ModuleAssessment).all():
        if assessment.quiz_id:
            db.get(Quiz, assessment.quiz_id).editorial_status = EDITORIAL_STATUS_UNREVIEWED
        else:
            # Retire the non-quiz activities so only blocked work is left.
            assessment.active = False
    # Explain prompts live outside ModuleAssessment; retire them too.
    for prompt in db.query(InterviewPrompt).all():
        prompt.active = False
    db.commit()
    _finish_everything_before_the_module_quiz(db, student)

    resolved = module_view(db, student.id, MODULE)["continue"]
    assert resolved["kind"] == "blocked"
    assert resolved["available"] is False
    assert resolved["route"] == f"/learning-v2/modules/{MODULE}"
    assert resolved["unavailable"]["reason"] == "This knowledge check is not available yet."


def test_opening_the_blocked_quiz_over_http_is_refused_consistently(db, monkeypatch):
    """The card and the endpoint agree: both say unavailable."""
    student, client = _ready(db, monkeypatch)
    assessment = _module_quiz(db)
    quiz = db.get(Quiz, assessment.quiz_id)
    quiz.editorial_status = EDITORIAL_STATUS_UNREVIEWED
    db.commit()

    card = _assessment_card(
        client.get(f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student)).json()["data"],
        assessment.assessment_key,
    )
    assert card["available"] is False

    opened = client.get(
        f"/api/v2/curriculum/modules/{MODULE}/assessments/{assessment.assessment_key}",
        headers=auth_headers(student),
    )
    assert opened.status_code == 404
    assert opened.json()["detail"] == "This knowledge check is not available."


def test_quick_check_cards_carry_the_availability_contract(db, monkeypatch):
    student, _ = _ready(db, monkeypatch)
    view = module_view(db, student.id, MODULE)
    quick_checks = [lesson["quick_check"] for lesson in view["lessons"] if lesson["quick_check"]]
    assert quick_checks, "module fixture should have at least one quick check"
    for card in quick_checks:
        assert card["available"] is True
        assert card["unavailable"] is None
        assert card["question_count"]
        assert card["role"] == "quick_check"
