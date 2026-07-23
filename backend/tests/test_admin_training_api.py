from app.models.command_reference import CommandReference
from app.models.curriculum_video import CurriculumVideo
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_PUBLISHED, Quiz
from app.models.training import TrainingWeek
from app.routers import admin_training
from app.services.admin_auth import verify_admin

from conftest import make_client


def admin_client():
    client = make_client(admin_training.router)
    client.app.dependency_overrides[verify_admin] = lambda: True
    return client


def add_week(db):
    week = TrainingWeek(
        week_number=1,
        display_order=1,
        title="Computer Basics",
        description="Start here.",
        learning_goals=[],
        is_active=True,
        requires_previous_week=False,
    )
    db.add(week)
    db.commit()
    db.refresh(week)
    return week


def test_admin_can_add_existing_activity_and_validate(db):
    week = add_week(db)
    video = CurriculumVideo(
        video_key="admin-video",
        section="Basics",
        section_order=1,
        title="Computer Basics",
        video_order=1,
        active=True,
    )
    db.add(video)
    quiz = Quiz(
        title="Computer Basics Quiz",
        question_count=0,
        week_number=1,
        domain_id="1.0",
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
        is_active=True,
    )
    db.add(quiz)
    db.commit()
    client = admin_client()

    response = client.post(
        f"/api/admin/training/weeks/{week.id}/activities",
        json={
            "stable_id": "week-1-video-admin",
            "activity_type": "video",
            "content_ref": str(video.id),
            "is_required": True,
            "metadata_json": {
                "quiz_id": quiz.id,
                "quiz_mapping_basis": "topic_group",
                "quiz_mapping_confidence": "Strong topical",
                "quiz_mapping_evidence": "Reviewed test mapping.",
            },
        },
    )
    validation = client.get("/api/admin/training/validation")

    assert response.status_code == 201
    assert response.json()["data"]["content_ref"] == str(video.id)
    assert validation.status_code == 200
    assert validation.json()["data"]["valid"] is True

    options = client.get("/api/admin/training/quiz-options")
    assert options.status_code == 200
    assert options.json()["data"] == [{"id": quiz.id, "title": quiz.title, "week_number": 1}]


def test_admin_rejects_broken_reference_and_required_untracked_activity(db):
    week = add_week(db)
    command = CommandReference(command="ipconfig", description="Show IP configuration")
    db.add(command)
    db.commit()
    client = admin_client()

    broken = client.post(
        f"/api/admin/training/weeks/{week.id}/activities",
        json={"stable_id": "broken", "activity_type": "guided_lab", "content_ref": "999", "is_required": True},
    )
    untracked = client.post(
        f"/api/admin/training/weeks/{week.id}/activities",
        json={"stable_id": "command", "activity_type": "command_exercise", "content_ref": str(command.id), "is_required": True},
    )
    missing_prerequisite = client.post(
        f"/api/admin/training/weeks/{week.id}/activities",
        json={
            "stable_id": "missing-prerequisite",
            "activity_type": "command_exercise",
            "content_ref": str(command.id),
            "is_required": False,
            "prerequisite_activity_id": 999,
        },
    )

    assert broken.status_code == 400
    assert untracked.status_code == 400
    assert missing_prerequisite.status_code == 400


def test_student_auth_cannot_access_admin_training_api(db):
    add_week(db)
    response = make_client(admin_training.router).get("/api/admin/training/weeks")
    assert response.status_code in {403, 500}
