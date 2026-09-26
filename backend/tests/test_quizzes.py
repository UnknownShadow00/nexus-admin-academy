from datetime import UTC, datetime, timedelta

from conftest import auth_headers, make_client, make_student
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.routers.admin_quiz import router as admin_quiz_router
from app.routers.quizzes import router
from app.routers.students import router as students_router
from app.services.training_reference_seed import _load as load_training_reference
from app.services.question_validation import validate_question

client = make_client(router, admin_quiz_router)


def test_week_zero_to_two_authored_options_contain_their_answer_keys():
    for quiz in load_training_reference()["quizzes"]:
        if quiz["week_number"] > 2:
            continue
        for question in quiz["questions"]:
            result = validate_question(question)
            assert result.valid, (quiz["id"], question["question_text"], result.errors)


def test_presented_options_are_snapshotted_and_review_uses_attempt_content(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Immutable option review", week_number=0)
    quiz.question_count = 1
    question = Question(quiz_id=quiz.id, question_text="Which choice covers all causes?", option_a="Dust", option_b="Heat", option_c="Power", option_d="Software", option_e="Memory", option_f="All of the above", correct_answer="F", explanation="Several causes apply.")
    db.add(question)
    db.commit()
    detail = client.get(f"/api/quizzes/{quiz.id}", headers=auth_headers(student)).json()["data"]
    assert detail["questions"][0]["option_f"] == "All of the above"
    shown = [{"id": question.id, "options": ["F", "A", "B", "C", "D", "E"]}]
    submitted = client.post(f"/api/quizzes/{quiz.id}/submit", headers=auth_headers(student), json={"student_id": student.id, "answers": {str(question.id): "F"}, "presentation_hash": detail["presentation_hash"], "presented_questions": shown})
    assert submitted.status_code == 200, submitted.text
    result = submitted.json()["data"]
    assert result["score"] == 1
    assert result["results"][0]["presented_option_order"] == shown[0]["options"]
    assert result["results"][0]["options"]["F"] == "All of the above"
    question.option_f = "Changed after attempt"
    question.correct_answer = "A"
    db.commit()
    review = client.get(f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)).json()["data"]
    assert review["results"][0]["options"]["F"] == "All of the above"
    assert review["results"][0]["correct_answer"] == "F"
    stale = client.post(f"/api/quizzes/{quiz.id}/submit", headers=auth_headers(student), json={"student_id": student.id, "answers": {str(question.id): "F"}, "presentation_hash": detail["presentation_hash"], "presented_questions": shown})
    assert stale.status_code == 409
    assert db.query(QuizAttempt).filter_by(student_id=student.id, quiz_id=quiz.id).count() == 1


def test_correct_answer_cannot_be_hidden_or_submitted_unpresented(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Option parity", week_number=0)
    question = _seed_question(db, quiz.id)
    detail = client.get(f"/api/quizzes/{quiz.id}", headers=auth_headers(student)).json()["data"]
    base = {"student_id": student.id, "answers": {str(question.id): "A"}, "presentation_hash": detail["presentation_hash"]}
    missing = client.post(f"/api/quizzes/{quiz.id}/submit", headers=auth_headers(student), json={**base, "presented_questions": [{"id": question.id, "options": ["B", "C", "D"]}]})
    assert missing.status_code == 422
    question.correct_answer = "H"
    db.commit()
    invalid = client.post(f"/api/quizzes/{quiz.id}/submit", headers=auth_headers(student), json={"student_id": student.id, "answers": {str(question.id): "H"}})
    assert invalid.status_code == 409
    assert db.query(QuizAttempt).filter_by(student_id=student.id, quiz_id=quiz.id).count() == 0


def test_review_question_numbers_follow_the_order_presented_to_learner(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Shuffled question parity", week_number=0)
    first = _seed_question(db, quiz.id)
    second = Question(quiz_id=quiz.id, question_text="Second authored prompt", option_a="Wrong", option_b="All of the above", correct_answer="B")
    db.add(second)
    db.commit()
    detail = client.get(f"/api/quizzes/{quiz.id}", headers=auth_headers(student)).json()["data"]
    shown = [{"id": second.id, "options": ["B", "A"]}, {"id": first.id, "options": ["D", "C", "B", "A"]}]
    submitted = client.post(f"/api/quizzes/{quiz.id}/submit", headers=auth_headers(student), json={"student_id": student.id, "answers": {str(first.id): "A", str(second.id): "B"}, "presentation_hash": detail["presentation_hash"], "presented_questions": shown})
    assert submitted.status_code == 200, submitted.text
    assert [(row["question_number"], row["question_id"]) for row in submitted.json()["data"]["results"]] == [(1, second.id), (2, first.id)]
    reviewed = client.get(f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)).json()["data"]
    assert [row["question_id"] for row in reviewed["results"]] == [second.id, first.id]


def test_today_recent_quiz_scores_include_denominator_and_percentage(db):
    student = make_student(db)
    for index, (score, total) in enumerate(((17, 19), (7, 8), (4, 4), (0, 8))):
        quiz = _seed_quiz(db, title=f"Recent score {index}", week_number=0)
        quiz.question_count = total
        db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, results=[], score=score,
                           xp_awarded=0, best_score=score, first_attempt_xp=0))
        db.commit()
    stats_client = make_client(students_router)
    response = stats_client.get(f"/api/students/{student.id}/stats", headers=auth_headers(student))
    assert response.status_code == 200, response.text
    recent = [item for item in response.json()["recent_activity"] if item["type"] == "quiz"]
    assert {(item["score"], item["score_total"], item["score_percent"]) for item in recent} == {
        (17, 19, 89), (7, 8, 88), (4, 4, 100), (0, 8, 0)
    }


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


def test_get_quiz_review_returns_latest_attempt_and_preserves_older_history(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Latest Review Attempt", week_number=1)
    question = _seed_question(db, quiz.id)
    now = datetime.now(UTC)
    db.add_all(
        [
            QuizAttempt(
                student_id=student.id,
                quiz_id=quiz.id,
                answers={str(question.id): "B"},
                results=[{"question_id": question.id, "student_answer": "B", "is_correct": False}],
                score=0,
                xp_awarded=0,
                best_score=0,
                first_attempt_xp=0,
                completed_at=now - timedelta(minutes=5),
            ),
            QuizAttempt(
                student_id=student.id,
                quiz_id=quiz.id,
                answers={str(question.id): "A"},
                results=[{"question_id": question.id, "student_answer": "A", "is_correct": True}],
                score=1,
                xp_awarded=0,
                best_score=1,
                first_attempt_xp=0,
                completed_at=now,
            ),
        ]
    )
    db.commit()

    res = client.get(f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student))

    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["score"] == 1
    assert payload["results"][0]["student_answer"] == "A"
    assert db.query(QuizAttempt).filter_by(student_id=student.id, quiz_id=quiz.id).count() == 2


def test_legacy_review_without_results_uses_authored_denominator(db):
    student = make_student(db)
    quiz = _seed_quiz(db, title="Legacy Result", week_number=1)
    question = _seed_question(db, quiz.id)
    quiz.question_count = 1
    db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={str(question.id): "A"},
                       results=[], score=1, xp_awarded=0, best_score=1, first_attempt_xp=0))
    db.commit()

    response = client.get(f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student))

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


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
