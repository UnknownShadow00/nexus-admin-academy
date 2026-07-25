from conftest import make_client

from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_DRAFT, Question, Quiz
from app.routers.admin_quiz import router as admin_quiz_router

client = make_client(admin_quiz_router)


def _seed_quiz(db):
    quiz = Quiz(
        title="Editor Test Quiz",
        week_number=1,
        status=QUIZ_STATUS_DRAFT,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _seed_question(db, quiz_id, **overrides):
    defaults = dict(
        quiz_id=quiz_id,
        question_text="What port does HTTPS use?",
        option_a="443",
        option_b="80",
        option_c="21",
        option_d="25",
        correct_answer="A",
        explanation="HTTPS uses 443.",
    )
    defaults.update(overrides)
    q = Question(**defaults)
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def test_validate_draft_endpoint_is_stateless_and_matches_shared_validator(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    headers = {"X-Admin-Key": "test-admin-key"}

    res = client.post(
        "/api/admin/questions/validate",
        json={
            "question_text": "Which apply? (Select 2 answers)",
            "options": ["A", "B", "C"],
            "correct_answers": "A",
        },
        headers=headers,
    )

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["valid"] is False
    assert any("Select 2" in e["message"] for e in body["errors"])
    # Nothing was persisted — no question_id involved, no DB row created.
    assert db.query(Question).count() == 0


def test_validate_draft_endpoint_accepts_valid_question(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    headers = {"X-Admin-Key": "test-admin-key"}

    res = client.post(
        "/api/admin/questions/validate",
        json={
            "question_text": "Pick one.",
            "options": ["Yes", "No"],
            "correct_answers": "A",
        },
        headers=headers,
    )

    assert res.status_code == 200
    assert res.json()["data"]["valid"] is True


def test_update_question_auto_clears_flag_when_edit_fixes_it(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    headers = {"X-Admin-Key": "test-admin-key"}
    quiz = _seed_quiz(db)
    question = _seed_question(
        db,
        quiz.id,
        question_text="Which apply? (Select 2 answers)",
        flagged_for_review=True,
        flag_reason="Select 2 mismatch",
    )

    res = client.put(
        f"/api/admin/questions/{question.id}",
        json={"correct_answers": "A,B"},
        headers=headers,
    )

    assert res.status_code == 200
    assert res.json()["data"]["valid"] is True
    db.refresh(question)
    assert question.flagged_for_review is False
    assert question.flag_reason is None


def test_update_question_auto_flags_when_edit_breaks_it(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    headers = {"X-Admin-Key": "test-admin-key"}
    quiz = _seed_quiz(db)
    question = _seed_question(db, quiz.id)

    res = client.put(
        f"/api/admin/questions/{question.id}",
        json={"correct_answer": "H"},  # H doesn't exist as an option on this question
        headers=headers,
    )

    assert res.status_code == 200
    assert res.json()["data"]["valid"] is False
    db.refresh(question)
    assert question.flagged_for_review is True
    assert question.flag_reason
