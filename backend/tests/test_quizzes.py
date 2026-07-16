from conftest import auth_headers, make_client, make_student
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.routers.admin_quiz import router as admin_quiz_router
from app.routers.quizzes import router

client = make_client(router, admin_quiz_router)


def _seed_quiz(db, title="Networks 101", week_number=1, status=QUIZ_STATUS_PUBLISHED):
    quiz = Quiz(title=title, week_number=week_number, status=status)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _seed_question(db, quiz_id, correct_answer="A", correct_answers=None):
    question = Question(
        quiz_id=quiz_id,
        question_text="Which option is correct?",
        option_a="Correct",
        option_b="Wrong",
        option_c="Wrong",
        option_d="Wrong",
        correct_answer=correct_answer,
        correct_answers=correct_answers,
        explanation="A is correct.",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def test_list_quizzes_empty(db):
    student = make_student(db)
    res = client.get("/api/quizzes", headers=auth_headers(student))
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_list_quizzes_returns_published(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Hardware 101", week_number=2)
    res = client.get("/api/quizzes?week_number=2", headers=auth_headers(student))
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Hardware 101"
    assert data[0]["id"] == quiz.id


def test_list_quizzes_draft_excluded(db):
    student = make_student(db)
    _seed_quiz(db, title="Draft Quiz", week_number=1, status="draft")
    res = client.get("/api/quizzes", headers=auth_headers(student))
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_get_quiz_detail_draft_excluded(db):
    student = make_student(db)
    draft = _seed_quiz(db, title="Draft Quiz", week_number=1, status="draft")

    res = client.get(f"/api/quizzes/{draft.id}", headers=auth_headers(student))

    assert res.status_code == 404


def test_get_quiz_review_draft_excluded_even_with_attempt(db):
    student = make_student(db)
    draft = _seed_quiz(db, title="Draft With Attempt", week_number=1, status="draft")
    question = _seed_question(db, draft.id)
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=draft.id,
            answers={str(question.id): "A"},
            results=[],
            score=1,
            xp_awarded=0,
            best_score=1,
            first_attempt_xp=0,
        )
    )
    db.commit()

    res = client.get(f"/api/quizzes/{draft.id}/review/{student.id}", headers=auth_headers(student))

    assert res.status_code == 404


def test_admin_can_publish_draft_quiz(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    student = make_student(db)
    draft = _seed_quiz(db, title="Publish Me", week_number=1, status="draft")

    publish = client.patch(
        f"/api/admin/quizzes/{draft.id}",
        json={"status": "published"},
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert publish.status_code == 200
    assert publish.json()["data"]["status"] == "published"

    db.refresh(draft)
    assert draft.status == QUIZ_STATUS_PUBLISHED

    listed = client.get("/api/quizzes", headers=auth_headers(student))
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()["data"]] == [draft.id]


def test_admin_rejects_invalid_quiz_status(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    draft = _seed_quiz(db, title="Invalid Status", week_number=1, status="draft")

    res = client.patch(
        f"/api/admin/quizzes/{draft.id}",
        json={"status": "archived"},
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert res.status_code == 422


def test_get_quiz_not_found(db):
    student = make_student(db)
    res = client.get("/api/quizzes/9999", headers=auth_headers(student))
    assert res.status_code == 404


def test_submit_multi_select_requires_exact_answer_set(db):
    student = make_student(db)
    quiz = _seed_quiz(db)
    question = _seed_question(db, quiz.id, correct_answer="A", correct_answers="A,C")

    # One correct letter is not full credit on a multi-select question
    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "A"}},
        headers=auth_headers(student),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["score"] == 0
    assert data["results"][0]["is_correct"] is False

    # The exact set, in any order, is full credit
    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "C,A"}},
        headers=auth_headers(student),
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["score"] == 1
    assert data["results"][0]["is_correct"] is True


def test_list_quizzes_unauthenticated(db):
    res = client.get("/api/quizzes")
    assert res.status_code == 401


def test_each_quiz_submission_creates_new_attempt_row(db):
    from app.models.quiz import QuizAttempt

    student = make_student(db, username="retaker1")
    quiz = _seed_quiz(db, title="Retake Quiz")
    question = _seed_question(db, quiz.id)

    first = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "A"}},
        headers=auth_headers(student),
    )
    assert first.status_code == 200
    assert first.json()["data"]["is_first_attempt"] is True
    assert first.json()["data"]["xp_awarded"] == 100

    second = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "B"}},
        headers=auth_headers(student),
    )
    assert second.status_code == 200
    assert second.json()["data"]["is_first_attempt"] is False
    assert second.json()["data"]["xp_awarded"] == 0

    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == student.id, QuizAttempt.quiz_id == quiz.id)
        .order_by(QuizAttempt.id.asc())
        .all()
    )
    assert len(attempts) == 2
    assert attempts[0].score == 1
    assert attempts[1].score == 0
    # best_score carries forward on the newest row
    assert attempts[1].best_score == 1
    assert attempts[1].first_attempt_xp == 100
