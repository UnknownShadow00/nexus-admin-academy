from conftest import auth_headers, make_client, make_student

from app.models.quiz import (
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_PURPOSE_PRACTICE,
    QUIZ_PURPOSE_REQUIRED,
    QUIZ_STATUS_PUBLISHED,
    Question,
    Quiz,
    QuizAttempt,
)
from app.routers.quizzes import router
from app.services.quiz_progression import is_quiz_passed


client = make_client(router)


def seed_quiz(db, *, required=True, count=4):
    quiz = Quiz(
        title="DHCP and APIPA Check",
        week_number=1,
        domain_id="2.0",
        lesson_id=None,
        question_count=count,
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
        explanations_complete=True,
        quiz_purpose=QUIZ_PURPOSE_REQUIRED if required else QUIZ_PURPOSE_PRACTICE,
        is_required=required,
        show_in_weekly_checklist=required,
    )
    db.add(quiz)
    db.flush()
    questions = []
    for index in range(count):
        question = Question(
            quiz_id=quiz.id,
            question_text=f"Question {index + 1}",
            option_a=f"Correct {index + 1}",
            option_b=f"Wrong {index + 1}",
            correct_answer="A",
            explanation=f"Key idea {index + 1}",
            tags=["DHCP", "APIPA"],
        )
        db.add(question)
        questions.append(question)
    db.commit()
    for question in questions:
        db.refresh(question)
    return quiz, questions


def start(student, quiz):
    return client.post(
        f"/api/quizzes/{quiz.id}/attempts",
        json={"student_id": student.id},
        headers=auth_headers(student),
    )


def test_required_assessment_is_server_owned_stable_and_resumable(db):
    student = make_student(db)
    quiz, _ = seed_quiz(db)

    first = start(student, quiz)
    resumed = start(student, quiz)

    assert first.status_code == resumed.status_code == 200
    first_data = first.json()["data"]
    resumed_data = resumed.json()["data"]
    assert first_data["purpose"] == "assessment"
    assert first_data["attempt"]["id"] == resumed_data["attempt"]["id"]
    assert first_data["questions"] == resumed_data["questions"]
    assert all("correct_answer" not in row for row in first_data["questions"])

    attempt_id = first_data["attempt"]["id"]
    question_id = str(first_data["questions"][0]["id"])
    saved = client.patch(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}",
        json={
            "student_id": student.id,
            "answers": {question_id: "A"},
            "current_position": 2,
            "revision": 0,
        },
        headers=auth_headers(student),
    )
    assert saved.status_code == 200
    restored = start(student, quiz).json()["data"]
    assert restored["attempt"]["answers"] == {question_id: "A"}
    assert restored["attempt"]["current_position"] == 2


def test_required_legacy_submit_is_wrapped_in_server_owned_snapshot(db):
    student = make_student(db)
    quiz, questions = seed_quiz(db)
    response = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(questions[0].id): "A"}},
        headers=auth_headers(student),
    )
    assert response.status_code == 200
    attempt = db.query(QuizAttempt).one()
    assert attempt.status == "submitted"
    assert attempt.question_snapshot
    assert response.json()["data"]["disclosure"] == "concepts_only"


def test_failed_assessment_withholds_key_and_duplicate_submit_is_idempotent(db):
    student = make_student(db)
    quiz, _ = seed_quiz(db)
    payload = start(student, quiz).json()["data"]
    attempt_id = payload["attempt"]["id"]
    answers = {
        str(row["id"]): next(
            option["letter"]
            for option in row["options"]
            if option["text"].startswith("Wrong")
        )
        for row in payload["questions"]
    }

    first = client.post(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}/submit",
        json={"student_id": student.id, "answers": answers},
        headers=auth_headers(student),
    )
    duplicate = client.post(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}/submit",
        json={"student_id": student.id, "answers": answers},
        headers=auth_headers(student),
    )

    assert first.status_code == duplicate.status_code == 200
    assert first.json() == duplicate.json()
    result = first.json()["data"]
    assert result["passed"] is False
    assert result["disclosure"] == "concepts_only"
    assert all(
        "correct_answer" not in row and "correct_answers" not in row
        for row in result["results"]
    )
    assert all("explanation" not in row for row in result["results"])
    assert "2.0" not in str(result)
    assert all(row["needs_review"] == ["DHCP", "APIPA"] for row in result["results"])
    assert (
        db.query(QuizAttempt).filter_by(student_id=student.id, quiz_id=quiz.id).count()
        == 1
    )
    assert is_quiz_passed(db, student.id, quiz) is False


def test_practice_teaches_but_cannot_award_required_credit(db):
    student = make_student(db)
    required_quiz, _ = seed_quiz(db)
    quiz, questions = seed_quiz(db, required=False)

    checked = client.post(
        f"/api/quizzes/{quiz.id}/practice/check",
        json={"student_id": student.id, "question_id": questions[0].id, "answer": "B"},
        headers=auth_headers(student),
    )

    assert checked.status_code == 200
    data = checked.json()["data"]
    assert data["purpose"] == "practice"
    assert data["awards_credit"] is False
    assert data["is_correct"] is False
    assert data["your_answer"] == "Wrong 1"
    assert data["correct_answer"] == "Correct 1"
    assert data["key_idea"] == "Key idea 1"
    assert db.query(QuizAttempt).count() == 0
    assert is_quiz_passed(db, student.id, required_quiz) is False

    submitted = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(questions[0].id): "A"}},
        headers=auth_headers(student),
    ).json()["data"]
    assert submitted["purpose"] == "practice"
    assert submitted["awards_credit"] is False
    assert submitted["result_label"] == "PRACTICE COMPLETE"
    assert is_quiz_passed(db, student.id, required_quiz) is False


def test_practice_completion_history_cannot_become_assessment_credit(db):
    student = make_student(db)
    required_quiz, _ = seed_quiz(db)
    practice, questions = seed_quiz(db, required=False)

    response = client.post(
        f"/api/quizzes/{practice.id}/practice/complete",
        json={
            "student_id": student.id,
            "checked_question_ids": [question.id for question in questions],
        },
        headers=auth_headers(student),
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "purpose": "practice",
        "practice_completed": True,
        "awards_credit": False,
    }
    row = (
        db.query(QuizAttempt)
        .filter_by(student_id=student.id, quiz_id=practice.id)
        .one()
    )
    assert row.status == "practice_complete"
    assert row.score == 0
    assert row.xp_awarded == 0
    assert is_quiz_passed(db, student.id, required_quiz) is False


def test_attempt_ownership_and_stale_save_are_enforced(db):
    owner = make_student(db, username="owner")
    other = make_student(db, username="other")
    quiz, _ = seed_quiz(db)
    payload = start(owner, quiz).json()["data"]
    attempt_id = payload["attempt"]["id"]

    forbidden = client.patch(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}",
        json={
            "student_id": other.id,
            "answers": {},
            "current_position": 0,
            "revision": 0,
        },
        headers=auth_headers(other),
    )
    assert forbidden.status_code == 404

    submitted = client.post(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}/submit",
        json={"student_id": owner.id, "answers": {}},
        headers=auth_headers(owner),
    )
    assert submitted.status_code == 200
    stale = client.patch(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}",
        json={
            "student_id": owner.id,
            "answers": {},
            "current_position": 0,
            "revision": 0,
        },
        headers=auth_headers(owner),
    )
    assert stale.status_code == 409


def test_older_revision_cannot_overwrite_a_newer_saved_answer(db):
    student = make_student(db)
    quiz, _ = seed_quiz(db)
    payload = start(student, quiz).json()["data"]
    attempt_id = payload["attempt"]["id"]
    question_id = str(payload["questions"][0]["id"])

    newer = client.patch(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}",
        json={
            "student_id": student.id,
            "answers": {question_id: "A"},
            "current_position": 0,
            "revision": 0,
        },
        headers=auth_headers(student),
    )
    stale = client.patch(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}",
        json={
            "student_id": student.id,
            "answers": {question_id: "B"},
            "current_position": 0,
            "revision": 0,
        },
        headers=auth_headers(student),
    )

    assert newer.status_code == 200
    assert newer.json()["data"]["revision"] == 1
    assert stale.status_code == 409
    assert start(student, quiz).json()["data"]["attempt"]["answers"] == {
        question_id: "A"
    }


def test_historical_review_uses_snapshot_after_bank_edit(db):
    student = make_student(db)
    quiz, questions = seed_quiz(db)
    payload = start(student, quiz).json()["data"]
    attempt_id = payload["attempt"]["id"]
    presentation = payload["questions"]
    answers = {
        str(row["id"]): next(
            option["letter"]
            for option in row["options"]
            if option["text"].startswith("Correct")
        )
        for row in presentation
    }
    result = client.post(
        f"/api/quizzes/{quiz.id}/attempts/{attempt_id}/submit",
        json={"student_id": student.id, "answers": answers},
        headers=auth_headers(student),
    )
    assert result.json()["data"]["passed"] is True

    questions[0].question_text = "Edited bank question"
    questions[0].option_a = "Edited answer"
    db.commit()
    review = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}?attempt_id={attempt_id}",
        headers=auth_headers(student),
    ).json()["data"]
    original = next(row for row in review["questions"] if row["id"] == questions[0].id)
    assert original["question_text"] == "Question 1"
    assert "Edited answer" not in str(review["questions"])
