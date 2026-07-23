from conftest import auth_headers, make_client, make_student
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.routers.admin_quiz import router as admin_quiz_router
from app.routers.quizzes import router

client = make_client(router, admin_quiz_router)


def _seed_quiz(db, title="Networks 101", week_number=1, status=QUIZ_STATUS_PUBLISHED):
    quiz = Quiz(
        title=title,
        week_number=week_number,
        status=status,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _seed_question(db, quiz_id):
    question = Question(
        quiz_id=quiz_id,
        question_text="Which option is correct?",
        option_a="Correct",
        option_b="Wrong",
        option_c="Wrong",
        option_d="Wrong",
        correct_answer="A",
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


def test_unvalidated_quiz_is_hidden_from_student_list_detail_and_submit(db):
    student = make_student(db)
    quiz = Quiz(
        title="Needs validation",
        week_number=1,
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status="needs_edit",
        answer_keys_validated=False,
        is_active=True,
    )
    db.add(quiz)
    db.flush()
    question = _seed_question(db, quiz.id)

    listed = client.get("/api/quizzes", headers=auth_headers(student))
    detail = client.get(f"/api/quizzes/{quiz.id}", headers=auth_headers(student))
    submitted = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "A"}},
        headers=auth_headers(student),
    )

    assert quiz.id not in {row["id"] for row in listed.json()["data"]}
    assert detail.status_code == 404
    assert submitted.status_code == 404


def test_get_quiz_detail_preserves_legacy_options_f_through_h(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Legacy Eight-Option Quiz", week_number=1)
    question = Question(
        quiz_id=quiz.id,
        question_text="Which legacy option is correct?",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        option_e="E",
        option_f="F",
        option_g="Correct legacy answer",
        option_h="H",
        correct_answer="G",
        explanation="The old quiz uses option G.",
    )
    db.add(question)
    quiz.question_count = 1
    db.commit()

    res = client.get(f"/api/quizzes/{quiz.id}", headers=auth_headers(student))

    assert res.status_code == 200
    payload = res.json()["data"]["questions"][0]
    assert payload["option_f"] == "F"
    assert payload["option_g"] == "Correct legacy answer"
    assert payload["option_h"] == "H"


def test_submit_quiz_scores_legacy_f_and_g_answers(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Legacy F/G Scoring", week_number=1)
    questions = [
        Question(
            quiz_id=quiz.id,
            question_text="Which option is F?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            option_e="E",
            option_f="Correct F answer",
            correct_answer="F",
        ),
        Question(
            quiz_id=quiz.id,
            question_text="Which option is G?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            option_e="E",
            option_f="F",
            option_g="Correct G answer",
            correct_answer="G",
        ),
    ]
    db.add_all(questions)
    quiz.question_count = 2
    db.commit()
    for question in questions:
        db.refresh(question)

    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={
            "student_id": student.id,
            "answers": {
                str(questions[0].id): "F",
                str(questions[1].id): "G",
            },
        },
        headers=auth_headers(student),
    )

    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["score"] == 2
    assert payload["total"] == 2
    assert [result["is_correct"] for result in payload["results"]] == [True, True]
    assert payload["results"][0]["options"]["F"] == "Correct F answer"
    assert payload["results"][1]["options"]["G"] == "Correct G answer"


def test_submit_quiz_reports_passing_attempt_with_distinct_message(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Passing Result Copy", week_number=1)
    questions = [
        Question(
            quiz_id=quiz.id,
            question_text=f"Passing threshold question {index}",
            option_a="Correct",
            option_b="Wrong",
            option_c="Wrong",
            option_d="Wrong",
            correct_answer="A",
        )
        for index in range(10)
    ]
    db.add_all(questions)
    quiz.question_count = len(questions)
    db.commit()
    for question in questions:
        db.refresh(question)

    passing = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={
            "student_id": student.id,
            "answers": {
                str(question.id): "A" if index < 7 else "B"
                for index, question in enumerate(questions)
            },
        },
        headers=auth_headers(student),
    )
    failing = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={
            "student_id": student.id,
            "answers": {str(question.id): "B" for question in questions},
        },
        headers=auth_headers(student),
    )

    assert passing.status_code == 200
    assert failing.status_code == 200
    passing_payload = passing.json()["data"]
    failing_payload = failing.json()["data"]
    assert passing_payload["score"] == 7
    assert passing_payload["total"] == 10
    assert passing_payload["passed"] is True
    assert isinstance(passing_payload["message"], str)
    assert passing_payload["message"].strip()
    assert passing_payload["message"] != failing_payload["message"]


def test_submit_quiz_reports_non_passing_attempt_with_guidance(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Non-Passing Result Copy", week_number=1)
    question = _seed_question(db, quiz.id)
    quiz.question_count = 1
    db.commit()

    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "B"}},
        headers=auth_headers(student),
    )

    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["passed"] is False
    assert isinstance(payload["message"], str)
    assert payload["message"].strip()


def test_list_quizzes_unauthenticated(db):
    res = client.get("/api/quizzes")
    assert res.status_code == 401
