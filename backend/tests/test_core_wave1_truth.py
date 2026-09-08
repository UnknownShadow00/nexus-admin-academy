"""Strict Wave 1 regressions: fresh in-memory DB, never production."""

import pytest
from conftest import auth_headers, make_client, make_student
from app.models.quiz import Quiz, Question, QuizAttempt
from app.models.squad_activity import SquadActivity
from app.routers.quizzes import router
from app.routers.students import router as students_router
from app.routers.admin_students import router as admin_router
from app.services.mastery_service import list_student_mastery
from app.services.quiz_progression import is_quiz_passed

client = make_client(router, students_router, admin_router)


def seed(db, total=4):
    quiz = Quiz(
        title=f"Truth quiz {total}",
        week_number=0,
        question_count=total,
        status="published",
        editorial_status="validated",
        answer_keys_validated=True,
        is_required=True,
        show_in_weekly_checklist=True,
    )
    db.add(quiz)
    db.flush()
    db.add_all(
        [
            Question(
                quiz_id=quiz.id,
                question_text=f"Question {i}",
                option_a="Correct",
                option_b="Wrong",
                correct_answer="A",
            )
            for i in range(total)
        ]
    )
    db.commit()
    return quiz


def submit(student, quiz, count):
    response = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        headers=auth_headers(student),
        json={
            "student_id": student.id,
            "answers": {
                str(q.id): "A" if i < count else "B"
                for i, q in enumerate(quiz.questions)
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.mark.parametrize(
    "count,total,percentage",
    [(4, 4, 100), (3, 4, 75), (0, 4, 0), (2, 2, 100), (3, 6, 50)],
)
def test_attempt_and_today_contract(db, count, total, percentage):
    student = make_student(db)
    quiz = seed(db, total)
    result = submit(student, quiz, count)
    activity = client.get(
        f"/api/students/{student.id}/stats", headers=auth_headers(student)
    ).json()["recent_activity"][0]
    assert activity.get("percentage") == percentage, activity
    assert result.get("percentage") == percentage, result
    for key in (
        "correct_count",
        "question_count",
        "percentage",
        "passed",
        "passing_percentage",
        "attempt_id",
        "submitted_at",
    ):
        assert result[key] == activity[key]


def test_failed_event_is_not_passed(db):
    student = make_student(db)
    submit(student, seed(db), 0)
    assert [r.activity_type for r in db.query(SquadActivity).all()] == ["quiz_failed"]


def test_latest_review_and_historical_identity(db):
    student = make_student(db)
    quiz = seed(db)
    submit(student, quiz, 0)
    submit(student, quiz, 4)
    rows = db.query(QuizAttempt).order_by(QuizAttempt.id).all()
    url = f"/api/quizzes/{quiz.id}/review/{student.id}"
    latest = client.get(url, headers=auth_headers(student)).json()["data"]
    assert latest["score"] == 4, latest
    assert latest["attempt_id"] == rows[-1].id
    historical = client.get(
        url, params={"attempt_id": rows[0].id}, headers=auth_headers(student)
    ).json()["data"]
    assert historical["attempt_id"] == rows[0].id
    assert historical["passed"] is False


def test_mixed_sizes_no_competency_number(db):
    student = make_student(db)
    submit(student, seed(db, 2), 2)
    submit(student, seed(db, 6), 6)
    diagnostics = list_student_mastery(db, student.id)
    assert all(
        row.get("metric_kind") == "legacy_internal_non_competency"
        for row in diagnostics
    ), diagnostics


def test_admin_average_has_explicit_percentage(db, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "disposable-test-key")
    student = make_student(db)
    submit(student, seed(db, 2), 2)
    submit(student, seed(db, 6), 6)
    row = client.get(
        "/api/admin/students/overview", headers={"X-Admin-Key": "disposable-test-key"}
    ).json()["data"][0]
    assert row.get("average_attempt_percentage") == 100, row


def test_pass_then_fail_and_changed_bank_preserves_earned_pass(db):
    student = make_student(db)
    quiz = seed(db)
    submit(student, quiz, 4)
    submit(student, quiz, 0)
    for i in range(5):
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=f"New {i}",
                option_a="Correct",
                option_b="Wrong",
                correct_answer="A",
            )
        )
    db.commit()
    db.expire_all()
    assert is_quiz_passed(db, student.id, quiz)
    review = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert review["question_count"] == 4
    assert review["passed"] is False
    assert review["best_attempt"]["percentage"] == 100
    assert db.query(QuizAttempt).count() == 2


def test_no_attempts_and_foreign_attempt_selection(db):
    student = make_student(db)
    other = make_student(db, "other")
    quiz = seed(db)
    url = f"/api/quizzes/{quiz.id}/review/{student.id}"
    assert client.get(url, headers=auth_headers(student)).status_code == 404
    submit(other, quiz, 4)
    foreign_id = db.query(QuizAttempt).one().id
    submit(student, quiz, 0)
    assert (
        client.get(
            url, params={"attempt_id": foreign_id}, headers=auth_headers(student)
        ).status_code
        == 404
    )


def test_equal_timestamp_latest_tie_breaks_by_id(db):
    from datetime import datetime

    student = make_student(db)
    quiz = seed(db)
    submit(student, quiz, 4)
    submit(student, quiz, 0)
    db.query(QuizAttempt).update({"completed_at": datetime(2026, 9, 8)})
    db.commit()
    data = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert data["score"] == 0
    assert data["best_attempt"]["percentage"] == 100
    assert data["earned_pass"] is True


def test_legacy_row_without_snapshot_is_labeled_and_not_regraded(db):
    student = make_student(db)
    quiz = seed(db)
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=None,
            score=3,
            best_score=3,
            xp_awarded=0,
        )
    )
    db.commit()
    data = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert data["percentage"] == 75
    assert data["score_basis"] == "current_bank_legacy_estimate"
    assert data["review_available"] is False
    assert data["results"] == []


def test_saved_questions_survive_bank_replacement(db):
    student = make_student(db)
    quiz = seed(db)
    result = submit(student, quiz, 3)
    old_ids = [question.id for question in quiz.questions]
    for question in quiz.questions:
        question.question_text = "Edited bank text"
        question.correct_answer = "B"
    db.commit()
    data = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert data["percentage"] == 75
    assert [q["id"] for q in data["questions"]] == old_ids
    assert all(q["question_text"] != "Edited bank text" for q in data["questions"])
    assert data["results"] == result["results"]


def test_progress_and_admin_share_latest_and_best_attempts(db, monkeypatch):
    from app.services.training_service import build_training_progress
    from test_training_service import add_week, add_activity

    monkeypatch.setenv("ADMIN_API_KEY", "disposable-test-key")
    student = make_student(db)
    quiz = seed(db)
    week = add_week(db, 0)
    add_activity(db, week, "truth-required", "quiz", quiz.id, 1)
    db.commit()
    passed = submit(student, quiz, 3)
    failed = submit(student, quiz, 0)
    progress = build_training_progress(db, student)
    row = progress["assessments"][0]
    assert row["latest_attempt"]["attempt_id"] == failed["attempt_id"]
    assert row["best_attempt"]["attempt_id"] == passed["attempt_id"]
    assert row["best_attempt"]["percentage"] == 75
    assert progress["required_quizzes"]["completed"] == 1
    admin = client.get(
        f"/api/admin/students/{student.id}/training-progress",
        headers={"X-Admin-Key": "disposable-test-key"},
    ).json()["data"]
    assert admin["assessments"] == progress["assessments"]


def test_empty_current_bank_does_not_erase_saved_pass(db):
    student = make_student(db)
    quiz = seed(db)
    submit(student, quiz, 4)
    quiz.questions.clear()
    quiz.question_count = 0
    db.commit()
    assert is_quiz_passed(db, student.id, quiz)
    data = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert data["percentage"] == 100
    assert data["question_count"] == 4
    assert len(data["questions"]) == 4


def test_admin_no_attempts_are_not_zero_performance(db, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "disposable-test-key")
    make_student(db)
    seed(db)
    data = client.get(
        "/api/admin/students/overview", headers={"X-Admin-Key": "disposable-test-key"}
    ).json()["data"][0]
    assert data["average_attempt_percentage"] is None
    assert data["quiz_done"] == 0
    assert data["quiz_total"] == 1


def test_unrecoverable_legacy_total_is_not_fabricated(db):
    student = make_student(db)
    quiz = seed(db)
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=None,
            score=8,
            best_score=8,
            xp_awarded=0,
        )
    )
    db.commit()
    data = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert data["correct_count"] == 8
    assert data["percentage"] is None
    assert data["passed"] is None
    assert data["review_available"] is False


def test_legacy_best_credit_without_original_passing_row_is_preserved(db):
    from app.services.training_service import build_training_progress
    from test_training_service import add_week, add_activity

    student = make_student(db)
    quiz = seed(db)
    week = add_week(db, 0)
    add_activity(db, week, "legacy-best-credit", "quiz", quiz.id, 1)
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=None,
            score=0,
            best_score=4,
            xp_awarded=0,
        )
    )
    db.commit()
    progress = build_training_progress(db, student)
    assert progress["required_quizzes"]["completed"] == 1
    data = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    ).json()["data"]
    assert data["earned_pass"] is True
    assert data["legacy_passing_credit"] is True
    assert data["best_attempt"]["correct_count"] == 0  # never invent the lost attempt
    assert data["passed"] is False
