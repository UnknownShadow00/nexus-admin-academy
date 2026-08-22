from app.models.curriculum_video import CurriculumVideo
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.routers import training

from conftest import auth_headers, make_client, make_student


def seed_training(db):
    week = TrainingWeek(
        week_number=1,
        display_order=1,
        title="Computer Basics",
        description="Learn the parts of a computer.",
        learning_goals=["Identify computer components"],
        estimated_minutes=60,
        is_active=True,
        requires_previous_week=False,
    )
    video = CurriculumVideo(
        id=10,
        video_key="computer-basics",
        section="Basics",
        section_order=1,
        title="How Computers Work",
        duration="10:00",
        url="https://example.test/video",
        exam_code="220-1201",
        job_relevance="job_critical",
        video_order=1,
        active=True,
    )
    db.add_all([week, video])
    db.flush()
    db.add(
        TrainingWeekActivity(
            training_week_id=week.id,
            stable_id="week-1-video-10",
            activity_type="video",
            content_ref="10",
            display_order=1,
            is_required=True,
            estimated_minutes=10,
            metadata_json={},
        )
    )
    db.commit()


def test_training_routes_return_only_authenticated_students_own_progress(db):
    student = make_student(db, "training-student")
    other = make_student(db, "other-student")
    seed_training(db)
    client = make_client(training.router)

    unauthorized = client.get("/api/training")
    response = client.get("/api/training", headers=auth_headers(student))
    week = client.get("/api/training/weeks/1", headers=auth_headers(student))
    module = client.get(
        "/api/training/modules/module.endpoint.support_workflow",
        headers=auth_headers(student),
    )
    progress = client.get("/api/training/progress", headers=auth_headers(student))
    spoofed = client.get(f"/api/training?student_id={other.id}", headers=auth_headers(student))

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()["data"]["current_week"]["week_number"] == 1
    assert week.status_code == 200
    assert week.json()["data"]["activities"][0]["destination_route"] == "/training/module/module.endpoint.support_workflow?activity=week-1-video-10"
    assert module.status_code == 200
    assert module.json()["data"]["stage"]["stable_id"] == "stage.endpoint_foundations"
    assert module.json()["data"]["activities"][0]["learning_role"] == "learn"
    assert progress.status_code == 200
    assert "student_id" not in response.text
    assert "other-student" not in response.text
    assert spoofed.status_code == 200


def test_locked_week_does_not_expose_activity_details(db):
    student = make_student(db, "locked-student")
    seed_training(db)
    week_two = TrainingWeek(
        week_number=2,
        display_order=2,
        title="Operating Systems",
        description="Learn operating systems.",
        learning_goals=[],
        is_active=True,
        requires_previous_week=True,
    )
    db.add(week_two)
    db.flush()
    db.add(
        TrainingWeekActivity(
            training_week_id=week_two.id,
            stable_id="hidden-future-video",
            activity_type="video",
            content_ref="10",
            display_order=1,
            is_required=True,
            metadata_json={"mentor_note": "never expose this"},
        )
    )
    db.commit()
    client = make_client(training.router)

    response = client.get("/api/training/weeks/2", headers=auth_headers(student))
    module_response = client.get(
        "/api/training/modules/module.endpoint.pc_hardware",
        headers=auth_headers(student),
    )

    assert response.status_code == 403
    assert "mentor_note" not in response.text
    assert module_response.status_code == 403
    assert "mentor_note" not in module_response.text
