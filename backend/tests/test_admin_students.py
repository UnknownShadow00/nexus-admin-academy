import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import event

from app.config import load_env
from app.models.curriculum_video import CurriculumVideo
from app.models.mastery import StudentDomainMastery
from app.models.quiz import (
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_STATUS_PUBLISHED,
    Question,
    Quiz,
    QuizAttempt,
)
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.routers import admin_students
from app.services.admin_auth import verify_admin
from app.services.auth_service import create_access_token
from app.services.training_service import build_cohort_summary, build_training_progress
from conftest import make_client


@contextmanager
def configured_admin_auth():
    """verify_admin's own "not configured" check (500) runs before its
    credential checks (403); CI has neither ADMIN_API_KEY nor ADMIN_PASSWORD
    set, so tests exercising real (non-overridden) verify_admin must set one,
    matching the convention in test_admin_session.py.
    """
    previous = os.environ.get("ADMIN_API_KEY")
    os.environ["ADMIN_API_KEY"] = "unit-test-api-key"
    load_env.cache_clear()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("ADMIN_API_KEY", None)
        else:
            os.environ["ADMIN_API_KEY"] = previous
        load_env.cache_clear()


def admin_client():
    client = make_client(admin_students.router)
    client.app.dependency_overrides[verify_admin] = lambda: True
    return client


def unauthenticated_client():
    return make_client(admin_students.router)


def add_student(db, suffix, last_active_at):
    student = Student(
        name=f"Student {suffix}",
        email=f"student-{suffix}@test.local",
        username=f"student-{suffix}",
        password_hash="test-hash",
        last_active_at=last_active_at,
    )
    db.add(student)
    db.flush()
    return student


def seed_curriculum(db):
    week_one = TrainingWeek(
        week_number=1,
        display_order=1,
        title="Foundations",
        learning_goals=[],
        is_active=True,
        requires_previous_week=False,
    )
    week_two = TrainingWeek(
        week_number=2,
        display_order=2,
        title="Networking",
        learning_goals=[],
        is_active=True,
        requires_previous_week=True,
    )
    video = CurriculumVideo(
        id=10,
        video_key="cohort-foundations",
        section="Foundations",
        section_order=1,
        title="Computer Foundations",
        video_order=1,
        active=True,
    )
    quiz_one = Quiz(
        id=20,
        title="Foundations Quiz",
        question_count=2,
        week_number=1,
        domain_id="1.0",
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
        explanations_complete=True,
        is_active=True,
        is_required=True,
        show_in_weekly_checklist=True,
        show_in_practice_library=False,
    )
    quiz_two = Quiz(
        id=21,
        title="Networking Quiz",
        question_count=2,
        week_number=2,
        domain_id="2.0",
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
        explanations_complete=True,
        is_active=True,
        is_required=True,
        show_in_weekly_checklist=True,
        show_in_practice_library=False,
    )
    db.add_all([week_one, week_two, video, quiz_one, quiz_two])
    db.flush()
    for quiz in (quiz_one, quiz_two):
        for index in range(2):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    question_text=f"{quiz.title} question {index}",
                    option_a="A",
                    option_b="B",
                    option_c="C",
                    option_d="D",
                    correct_answer="A",
                    explanation="A is correct.",
                )
            )
    db.add_all(
        [
            TrainingWeekActivity(
                training_week_id=week_one.id,
                stable_id="cohort-week-1-video",
                activity_type="video",
                content_ref=str(video.id),
                display_order=1,
                is_required=True,
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_one.id,
                stable_id="cohort-week-1-quiz",
                activity_type="quiz",
                content_ref=str(quiz_one.id),
                display_order=2,
                is_required=True,
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_two.id,
                stable_id="cohort-week-2-quiz",
                activity_type="quiz",
                content_ref=str(quiz_two.id),
                display_order=1,
                is_required=True,
                metadata_json={},
            ),
        ]
    )
    db.flush()
    return video, quiz_one, quiz_two


def add_passed_attempt(db, student, quiz):
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=[],
            score=2,
            best_score=2,
            first_attempt_xp=0,
            xp_awarded=0,
        )
    )


@contextmanager
def count_queries(engine):
    count = 0

    def before_cursor_execute(*_):
        nonlocal count
        count += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield lambda: count
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def test_admin_cohort_summary_and_student_training_progress(db):
    now = datetime.now(timezone.utc)
    recent = add_student(db, "recent", now - timedelta(hours=2))
    stale = add_student(db, "stale", now - timedelta(days=5))
    never_active = add_student(db, "never", None)
    video, quiz_one, quiz_two = seed_curriculum(db)

    db.add(VideoWatch(student_id=recent.id, video_key=video.video_key))
    add_passed_attempt(db, recent, quiz_one)
    add_passed_attempt(db, recent, quiz_two)
    db.add(VideoWatch(student_id=stale.id, video_key=video.video_key))
    add_passed_attempt(db, never_active, quiz_two)
    db.add_all(
        [
            StudentDomainMastery(
                student_id=recent.id,
                domain_id="1.0",
                quiz_score_total=9,
                quiz_attempts=1,
                ticket_score_total=0,
                ticket_attempts=0,
                mastery_percent=30,
            ),
            StudentDomainMastery(
                student_id=recent.id,
                domain_id="2.0",
                quiz_score_total=8,
                quiz_attempts=1,
                ticket_score_total=0,
                ticket_attempts=0,
                mastery_percent=26.7,
            ),
        ]
    )
    db.commit()

    client = admin_client()
    response = client.get("/api/admin/students/cohort-summary")
    detail = client.get(f"/api/admin/students/{recent.id}/training-progress")

    assert response.status_code == 200
    summaries = {
        item["student_id"]: item for item in response.json()["data"]
    }
    assert summaries[recent.id]["current_week"] == {
        "week_number": 2,
        "status": "complete",
    }
    assert summaries[recent.id]["overall_percent"] == 100
    assert summaries[recent.id]["is_at_risk"] is False
    assert summaries[stale.id]["current_week"] == {
        "week_number": 1,
        "status": "in_progress",
    }
    assert summaries[stale.id]["overall_percent"] == 33
    assert summaries[stale.id]["is_at_risk"] is True
    assert summaries[never_active.id]["current_week"] == {
        "week_number": 1,
        "status": "in_progress",
    }
    assert summaries[never_active.id]["overall_percent"] == 33
    assert summaries[never_active.id]["is_at_risk"] is True

    assert detail.status_code == 200
    payload = detail.json()["data"]
    assert [
        (week["week_number"], week["completion_percent"])
        for week in payload["weekly_roadmap"]
    ] == [(1, 100), (2, 100)]
    assert payload["skills"] == [
        {
            "domain_id": "1.0",
            "domain_name": "Hardware",
            "mastery_percent": 30.0,
            "quiz_attempts": 1,
            "ticket_attempts": 0,
        },
        {
            "domain_id": "2.0",
            "domain_name": "Networking",
            "mastery_percent": 26.7,
            "quiz_attempts": 1,
            "ticket_attempts": 0,
        },
    ]


def test_cohort_endpoints_reject_no_credentials_and_student_jwt(db):
    with configured_admin_auth():
        client = unauthenticated_client()

        no_creds_summary = client.get("/api/admin/students/cohort-summary")
        no_creds_detail = client.get("/api/admin/students/1/training-progress")
        assert no_creds_summary.status_code == 403
        assert no_creds_detail.status_code == 403

        student_token = create_access_token({"sub": "1", "name": "Student", "is_mentor": False})
        headers = {"Authorization": f"Bearer {student_token}"}
        student_summary = client.get("/api/admin/students/cohort-summary", headers=headers)
        student_detail = client.get("/api/admin/students/1/training-progress", headers=headers)
        assert student_summary.status_code == 403
        assert student_detail.status_code == 403


def test_admin_student_training_progress_returns_404(db):
    response = admin_client().get("/api/admin/students/999/training-progress")

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found"


def test_cohort_summary_matches_authoritative_per_student_progress(db):
    """build_cohort_summary re-derives completion rules in bulk (to avoid the
    N+1 pattern _TrainingContext's per-student queries would cause at cohort
    scale), instead of calling build_training_progress per student. That is a
    deliberate duplication of quiz/ticket/lab/capstone/service-desk completion
    logic and week-locking rules across two code paths. This test pins the two
    paths together: if a future change to one set of rules (e.g. the quiz pass
    threshold) is not mirrored in the other, this test fails instead of the
    drift going unnoticed.
    """
    now = datetime.now(timezone.utc)
    student_a = add_student(db, "parity-a", now)
    student_b = add_student(db, "parity-b", now - timedelta(days=10))
    video, quiz_one, quiz_two = seed_curriculum(db)
    db.add(VideoWatch(student_id=student_a.id, video_key=video.video_key))
    add_passed_attempt(db, student_a, quiz_one)
    db.commit()

    for student in (student_a, student_b):
        [summary] = build_cohort_summary(db, [student])
        authoritative = build_training_progress(db, student)

        assert summary["current_week"]["week_number"] == authoritative["current_week"]["week_number"]
        assert summary["current_week"]["status"] == authoritative["current_week"]["status"]
        assert summary["overall_percent"] == authoritative["overall_training"]["percent"]


def test_cohort_summary_query_count_does_not_scale_with_student_count(db):
    seed_curriculum(db)
    for index in range(3):
        add_student(db, str(index), None)
    db.commit()
    engine = db.get_bind()
    students = db.query(Student).order_by(Student.id.asc()).all()

    with count_queries(engine) as first_count:
        build_cohort_summary(db, students)
    three_student_queries = first_count()

    for index in range(3, 8):
        add_student(db, str(index), None)
    db.commit()
    students = db.query(Student).order_by(Student.id.asc()).all()
    with count_queries(engine) as second_count:
        build_cohort_summary(db, students)
    eight_student_queries = second_count()

    assert three_student_queries == eight_student_queries
    assert eight_student_queries <= 10
