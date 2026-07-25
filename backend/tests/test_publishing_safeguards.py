from conftest import make_client, make_student

from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_DRAFT, QUIZ_STATUS_PUBLISHED, Question, Quiz
from app.routers.admin_quiz import router as admin_quiz_router
from app.routers.quizzes import router as quizzes_router
from app.services.fsrs_service import create_cards_for_wrong_answers
from app.models.flashcard import FlashcardReview

client = make_client(quizzes_router, admin_quiz_router)


def _seed_quiz(db, status=QUIZ_STATUS_DRAFT):
    quiz = Quiz(
        title="Publishing Safeguard Quiz",
        week_number=1,
        status=status,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _seed_valid_question(db, quiz_id):
    q = Question(
        quiz_id=quiz_id,
        question_text="What port does HTTPS use?",
        option_a="443",
        option_b="80",
        option_c="21",
        option_d="25",
        correct_answer="A",
        explanation="HTTPS uses 443.",
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def _seed_flagged_question(db, quiz_id):
    q = Question(
        quiz_id=quiz_id,
        question_text="Broken question with no valid answer key",
        option_a="Only option",
        option_b="Wrong",
        option_c="Wrong",
        option_d="Wrong",
        correct_answer="A",
        flagged_for_review=True,
        flag_reason="No correct answer is recorded for this question.",
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def _seed_naturally_invalid_question(db, quiz_id):
    """Not explicitly flagged, but fails validate_question_row() — the
    guard must catch this too, not just the flagged_for_review flag."""
    q = Question(
        quiz_id=quiz_id,
        question_text="Which apply? (Select 2 answers)",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
        correct_answers=None,  # says "Select 2" but only one answer stored
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def test_publishing_quiz_with_flagged_question_is_blocked(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    quiz = _seed_quiz(db)
    _seed_valid_question(db, quiz.id)
    _seed_flagged_question(db, quiz.id)

    res = client.patch(
        f"/api/admin/quizzes/{quiz.id}",
        json={"status": "published"},
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert res.status_code == 409
    detail = res.json().get("detail") or res.json().get("error") or ""
    assert "flagged for review" in detail or "fail validation" in detail
    db.refresh(quiz)
    assert quiz.status == QUIZ_STATUS_DRAFT


def test_publishing_quiz_with_select_n_mismatch_is_blocked_even_without_explicit_flag(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    quiz = _seed_quiz(db)
    _seed_naturally_invalid_question(db, quiz.id)

    res = client.patch(
        f"/api/admin/quizzes/{quiz.id}",
        json={"status": "published"},
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert res.status_code == 409


def test_publishing_quiz_with_only_valid_questions_succeeds(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    quiz = _seed_quiz(db)
    _seed_valid_question(db, quiz.id)

    res = client.patch(
        f"/api/admin/quizzes/{quiz.id}",
        json={"status": "published"},
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert res.status_code == 200
    db.refresh(quiz)
    assert quiz.status == QUIZ_STATUS_PUBLISHED


def test_flagged_question_never_becomes_a_daily_review_card(db):
    student = make_student(db)
    quiz = _seed_quiz(db, status=QUIZ_STATUS_PUBLISHED)
    flagged = _seed_flagged_question(db, quiz.id)
    valid = _seed_valid_question(db, quiz.id)

    create_cards_for_wrong_answers(db, student.id, {flagged.id: "A", valid.id: "B"})
    db.commit()

    cards = db.query(FlashcardReview).filter(FlashcardReview.student_id == student.id).all()
    question_ids = {c.question_id for c in cards}
    assert flagged.id not in question_ids
    assert valid.id in question_ids


def test_naturally_invalid_question_never_becomes_a_daily_review_card(db):
    student = make_student(db)
    quiz = _seed_quiz(db, status=QUIZ_STATUS_PUBLISHED)
    broken = _seed_naturally_invalid_question(db, quiz.id)

    create_cards_for_wrong_answers(db, student.id, {broken.id: "A"})
    db.commit()

    cards = db.query(FlashcardReview).filter(FlashcardReview.student_id == student.id).all()
    assert cards == []
