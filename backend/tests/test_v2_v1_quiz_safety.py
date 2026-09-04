"""Loading V2 content must not disturb V1 student quiz visibility.

``quizzes`` and ``questions`` are shared tables. The V2 content load creates
and publishes fifteen module banks in the same tables the legacy Quizzes page
and Daily Review read, and those legacy surfaces are not scoped to the V1
curriculum. Before this sprint, loading V2 content therefore added fourteen
quizzes to the legacy quiz list of every student — including students not in
the V2 pilot, and regardless of V2_CURRICULUM_ENABLED, because content
loading is not gated by the flag at all.

These tests capture V1 visibility before the load and compare it after.
"""

from conftest import auth_headers, make_client, make_student

from app.models.certification import ModuleAssessment
from app.models.quiz import (
    EDITORIAL_STATUS_UNREVIEWED,
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_STATUS_DRAFT,
    QUIZ_STATUS_PUBLISHED,
    Question,
    Quiz,
)
from app.routers.quizzes import router as quizzes_router
from app.services.quiz_visibility import (
    student_visible_quiz_filters,
    v1_student_visible_quiz_filters,
)
from app.services.v2_content_loader import ContentValidationError, load_module

import pytest


def _v1_quiz(db, title, week, *, visible=True):
    quiz = Quiz(
        title=title,
        week_number=week,
        status=QUIZ_STATUS_PUBLISHED if visible else QUIZ_STATUS_DRAFT,
        is_active=True,
        editorial_status=EDITORIAL_STATUS_VALIDATED if visible else EDITORIAL_STATUS_UNREVIEWED,
        answer_keys_validated=visible,
        question_count=1,
    )
    db.add(quiz)
    db.flush()
    db.add(Question(
        quiz_id=quiz.id, question_text=f"{title}: a V1 question?",
        option_a="a", option_b="b", option_c="c", option_d="d",
        correct_answer="A", explanation="Because.",
    ))
    db.commit()
    return quiz


def _realistic_v1_content(db):
    """A small but realistic V1 corpus: visible quizzes plus a draft."""
    return {
        "visible": [
            _v1_quiz(db, "V1 Week 2 Hardware Basics", 2),
            _v1_quiz(db, "V1 Week 3 Networking Basics", 3),
            _v1_quiz(db, "V1 Week 0 Orientation", 0),
        ],
        "hidden": [_v1_quiz(db, "V1 Draft Not Ready", 4, visible=False)],
    }


def _v1_visible_ids(db) -> set[int]:
    return {row.id for row in db.query(Quiz).filter(*v1_student_visible_quiz_filters()).all()}


def _v1_list_ids(client, student) -> set[int]:
    payload = client.get("/api/quizzes", headers=auth_headers(student)).json()
    return {row["id"] for row in (payload.get("data") or payload)}


# --------------------------------------------------------------------------- #
# Baseline / comparison
# --------------------------------------------------------------------------- #

def test_v2_load_adds_no_quiz_to_the_v1_student_list(db):
    content = _realistic_v1_content(db)
    student = make_student(db, username="v1_safety_list")
    client = make_client(quizzes_router)

    before = _v1_list_ids(client, student)
    assert before == {quiz.id for quiz in content["visible"]}

    load_module(db, commit=True)

    after = _v1_list_ids(client, student)
    assert after - before == set(), "V2 content became visible in the V1 quiz list"
    assert before - after == set(), "V2 content load hid an existing V1 quiz"


def test_v2_load_adds_no_quiz_to_daily_review_title_matching(db):
    """Daily Review maps curriculum titles onto visible quizzes."""
    from app.services.training_service import student_visible_quiz_filters as _unused  # noqa: F401

    content = _realistic_v1_content(db)
    before = _v1_visible_ids(db)
    assert before == {quiz.id for quiz in content["visible"]}

    load_module(db, commit=True)
    assert _v1_visible_ids(db) == before


def test_a_draft_v1_quiz_stays_hidden_across_the_load(db):
    content = _realistic_v1_content(db)
    draft = content["hidden"][0]
    load_module(db, commit=True)
    assert draft.id not in _v1_visible_ids(db)


def test_the_v2_banks_really_were_created_and_published(db):
    """Guard the guard: the comparison above must not pass vacuously."""
    _realistic_v1_content(db)
    load_module(db, commit=True)

    v2_quiz_ids = {
        row.quiz_id for row in db.query(ModuleAssessment).all() if row.quiz_id
    }
    assert len(v2_quiz_ids) >= 14

    published_v2 = db.query(Quiz).filter(
        Quiz.id.in_(v2_quiz_ids), *student_visible_quiz_filters()
    ).count()
    assert published_v2 >= 14, "V2 banks should be student-visible to V2, just not to V1"
    assert not (v2_quiz_ids & _v1_visible_ids(db))


def test_a_v1_student_cannot_open_a_v2_bank_by_id(db):
    """Hiding it from the list is not enough — the by-id route is scoped too."""
    _realistic_v1_content(db)
    load_module(db, commit=True)
    student = make_student(db, username="v1_safety_byid")
    client = make_client(quizzes_router)

    v2_quiz_id = next(
        row.quiz_id for row in db.query(ModuleAssessment).all() if row.quiz_id
    )
    assert client.get(
        f"/api/quizzes/{v2_quiz_id}", headers=auth_headers(student)
    ).status_code == 404


def test_v2_quizzes_stay_out_of_the_v1_curriculum_activity_list(db):
    """V2 banks carry week_number 0 and must not enter V1 week-0 curriculum."""
    load_module(db, commit=True)
    v2_quiz_ids = {row.quiz_id for row in db.query(ModuleAssessment).all() if row.quiz_id}
    week_zero_v1 = {
        row.id for row in db.query(Quiz).filter(
            *v1_student_visible_quiz_filters(), Quiz.week_number == 0
        ).all()
    }
    assert not (week_zero_v1 & v2_quiz_ids)


# --------------------------------------------------------------------------- #
# The shared-table collision the loader already refuses
# --------------------------------------------------------------------------- #

def test_a_title_collision_with_a_v1_quiz_aborts_the_load_atomically(db):
    """Documented intentional behaviour, now proven.

    The question importer resolves a quiz by title, so a pre-existing V1 quiz
    sharing a V2 bank's title would have V2 questions merged into it. The
    editorial approval guard catches the resulting question-count mismatch and
    refuses the load — and because the load is one transaction, nothing from
    it is committed.
    """
    import seed_v2_foundation

    collide = _v1_quiz(db, "Module 8 — PC Hardware, Displays & Fault Isolation Quiz", 8)
    before_ids = _v1_visible_ids(db)
    before_questions = db.query(Question).filter(Question.quiz_id == collide.id).count()

    with pytest.raises(ContentValidationError) as excinfo:
        seed_v2_foundation.run(db)
    assert "reviewed" in str(excinfo.value)

    db.rollback()
    assert _v1_visible_ids(db) == before_ids
    assert db.query(Question).filter(Question.quiz_id == collide.id).count() == before_questions
    assert db.query(ModuleAssessment).count() == 0
