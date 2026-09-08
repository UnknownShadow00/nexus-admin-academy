from datetime import datetime, timezone

import pytest
from conftest import auth_headers, make_client, make_student
from core_wave2_fixture import seed_beginner
from app.models.learning import Lesson
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import Quiz, QuizAttempt
from app.models.training import TrainingWeekActivity
from app.routers import quizzes, training
from app.services.training_service import build_training_overview
from seed import ORIENTATION_SUMMARY


def test_orientation_teaches_every_assessed_ticket_field():
    for concept in (
        "requester",
        "device",
        "symptom",
        "impact",
        "category",
        "escalation",
        "progress notes",
        "internal",
    ):
        assert concept in ORIENTATION_SUMMARY.lower(), (
            f"Untaught before required quiz: {concept}"
        )


def test_foundational_lessons_are_required(db):
    seed_beginner(db)
    for lesson in db.query(Lesson).all():
        activity = (
            db.query(TrainingWeekActivity)
            .filter_by(activity_type="lesson", content_ref=str(lesson.id))
            .one()
        )
        assert activity.is_required, lesson.title


@pytest.mark.parametrize("quiz_id", [42, 1])
@pytest.mark.parametrize("method", ["get", "post"])
def test_direct_required_assessment_cannot_bypass_teaching(db, quiz_id, method):
    seed_beginner(db)
    student = make_student(db)
    client = make_client(quizzes.router)
    path = f"/api/quizzes/{quiz_id}"
    if method == "post":
        response = client.post(
            path + "/submit",
            headers=auth_headers(student),
            json={"student_id": student.id, "answers": {"1": "A"}},
        )
    else:
        response = client.get(path, headers=auth_headers(student))
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "PREREQUISITE_NOT_MET"
    assert response.json()["data"]["next_action_route"].startswith("/lessons/")
    assert db.query(QuizAttempt).count() == 0


def test_next_action_and_lock_identify_missing_teaching(db):
    seed_beginner(db)
    student = make_student(db)
    overview = build_training_overview(db, student)
    quiz = next(
        a for a in overview["current_module_activities"] if a["activity_type"] == "quiz"
    )
    assert quiz["status"] == "locked"
    assert quiz["prerequisite_title"] == "Welcome to Nexus: Your First Week"
    assert quiz["recovery_route"].startswith("/lessons/")


def test_completed_orientation_allows_normal_quiz_launch(db):
    seed_beginner(db)
    student = make_student(db)
    lesson = db.query(Lesson).filter_by(title="Welcome to Nexus: Your First Week").one()
    db.add(
        StudentLessonProgress(
            student_id=student.id,
            lesson_id=lesson.id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    response = make_client(quizzes.router).get(
        "/api/quizzes/42", headers=auth_headers(student)
    )
    assert response.status_code == 200


def test_locked_module_has_structured_recovery(db):
    seed_beginner(db)
    student = make_student(db)
    response = make_client(training.router).get(
        "/api/training/modules/module.endpoint.support_workflow",
        headers=auth_headers(student),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PREREQUISITE_NOT_MET"
    assert response.json()["data"]["next_action_route"].startswith("/lessons/")


def test_optional_practice_remains_available_in_future_module(db):
    seed_beginner(db)
    student = make_student(db)
    quiz = db.get(Quiz, 1)
    quiz.is_required = False
    db.query(TrainingWeekActivity).filter_by(
        activity_type="quiz", content_ref="1"
    ).update({"is_required": False})
    db.commit()
    client = make_client(quizzes.router)
    assert (
        client.get("/api/quizzes/1", headers=auth_headers(student)).status_code == 200
    )
    assert (
        client.post(
            "/api/quizzes/1/submit",
            headers=auth_headers(student),
            json={"student_id": student.id, "answers": {}},
        ).status_code
        == 200
    )


def test_earned_pass_retry_and_historical_review_survive_changed_requirements(db):
    seed_beginner(db)
    student = make_student(db)
    client = make_client(quizzes.router)
    # A historical passing snapshot predates the now-required lessons.
    attempt = QuizAttempt(
        quiz_id=1,
        student_id=student.id,
        answers={},
        xp_awarded=0,
        score=4,
        best_score=4,
        results=[
            {"question_id": i + 1, "is_correct": True, "passing_percentage": 80}
            for i in range(4)
        ],
    )
    db.add(attempt)
    db.commit()
    attempt_id = attempt.id
    assert (
        client.get("/api/quizzes/1", headers=auth_headers(student)).status_code == 200
    )
    response = client.post(
        "/api/quizzes/1/submit",
        headers=auth_headers(student),
        json={"student_id": student.id, "answers": {}},
    )
    assert response.status_code == 200
    assert response.json()["data"]["passed"] is False
    review = client.get(
        f"/api/quizzes/1/review/{student.id}?attempt_id={attempt_id}",
        headers=auth_headers(student),
    )
    assert review.status_code == 200
    assert review.json()["data"]["attempt_id"] == attempt_id
    assert review.json()["data"]["percentage"] == 100
    assert (
        db.query(QuizAttempt).filter_by(student_id=student.id, quiz_id=1).count() == 2
    )
    from app.services.quiz_progression import is_quiz_passed

    assert is_quiz_passed(db, student.id, db.get(Quiz, 1))


def test_failed_historical_review_available_while_new_submissions_locked(db):
    seed_beginner(db)
    student = make_student(db)
    db.add(
        QuizAttempt(
            quiz_id=1,
            student_id=student.id,
            answers={},
            xp_awarded=0,
            score=0,
            best_score=0,
            results=[{"question_id": i + 1, "is_correct": False} for i in range(4)],
        )
    )
    db.commit()
    client = make_client(quizzes.router)
    assert (
        client.get(
            f"/api/quizzes/1/review/{student.id}", headers=auth_headers(student)
        ).status_code
        == 200
    )
    assert (
        client.get("/api/quizzes/1", headers=auth_headers(student)).status_code == 403
    )


def test_required_mapping_cannot_be_bypassed_by_optional_quiz_flag(db):
    seed_beginner(db)
    student = make_student(db)
    db.get(Quiz, 1).is_required = False
    db.commit()
    assert (
        make_client(quizzes.router)
        .post(
            "/api/quizzes/1/submit",
            headers=auth_headers(student),
            json={"student_id": student.id, "answers": {}},
        )
        .status_code
        == 403
    )
