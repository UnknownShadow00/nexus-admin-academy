from conftest import auth_headers, make_client, make_student
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.routers.lesson_notes import router as lesson_router
from app.services.progression_service import derive_current_week


client = make_client(lesson_router)


def _seed_lessons(db):
    module = Module(code="MOD-001", title="Support Basics", module_order=1, active=True)
    db.add(module)
    db.flush()
    published = Lesson(
        module_id=module.id,
        title="Ticket Triage",
        summary="Read the ticket and identify the next safe action.",
        outcomes=["Identify the reported symptoms", "  Verify the safe next action  ", " ", None, 42],
        lesson_order=1,
        status="published",
    )
    draft = Lesson(module_id=module.id, title="Draft Lesson", lesson_order=2, status="draft")
    db.add_all([published, draft])
    db.commit()
    return module, published, draft


def test_direct_lesson_and_notes_remain_student_scoped(db):
    student = make_student(db)
    other = make_student(db, username="student2")
    module, lesson, _ = _seed_lessons(db)

    response = client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(student))
    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": lesson.id,
        "title": lesson.title,
        "summary": lesson.summary,
        "outcomes": ["Identify the reported symptoms", "Verify the safe next action"],
        "video_url": None,
        "module_code": module.code,
        "module_title": module.title,
        "related_activity_stable_id": None,
        "related_activity_week_number": None,
        "related_training_module_id": None,
        "related_activity_type": None,
        "is_orientation": False,
        "is_complete": False,
    }

    saved = client.put(
        f"/api/lessons/{lesson.id}/notes",
        json={"content": "Verify impact before changing anything."},
        headers=auth_headers(student),
    )
    assert saved.status_code == 200
    assert client.get(f"/api/lessons/{lesson.id}/notes", headers=auth_headers(student)).json()["data"]["content"] == "Verify impact before changing anything."
    assert client.get(f"/api/lessons/{lesson.id}/notes", headers=auth_headers(other)).json()["data"]["content"] == ""
    assert client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(student)).json()["data"]["is_complete"] is False

    completed = client.post(f"/api/lessons/{lesson.id}/complete", headers=auth_headers(student))
    assert completed.status_code == 200
    completed_at = completed.json()["data"]["completed_at"]
    assert client.post(f"/api/lessons/{lesson.id}/complete", headers=auth_headers(student)).json()["data"]["completed_at"] == completed_at
    assert client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(student)).json()["data"]["is_complete"] is True
    assert client.post(f"/api/lessons/{lesson.id}/complete", headers=auth_headers(other)).status_code == 409
    assert db.query(StudentLessonProgress).filter_by(student_id=other.id, lesson_id=lesson.id).first() is None


def test_direct_lesson_exposes_related_weekly_activity(db):
    student = make_student(db)
    _, lesson, _ = _seed_lessons(db)
    stable_id = "week-1-networking_lab-meet-cli-001"
    lesson.related_activity_stable_id = stable_id
    week = TrainingWeek(week_number=1, display_order=1, title="Week 1")
    db.add(week)
    db.flush()
    db.add(
        TrainingWeekActivity(
            training_week_id=week.id,
            stable_id=stable_id,
            activity_type="networking_lab",
            content_ref="meet-cli-001",
            display_order=1,
        )
    )
    db.commit()

    response = client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(student))

    assert response.status_code == 200
    assert response.json()["data"].get("related_activity_stable_id") == stable_id
    assert response.json()["data"].get("related_activity_week_number") == 1
    assert response.json()["data"].get("related_training_module_id") == "module.endpoint.support_workflow"
    assert response.json()["data"].get("related_activity_type") == "networking_lab"


def test_saving_a_note_never_completes_or_unlocks_a_lesson(db):
    student = make_student(db)
    module = Module(code="MOD-001", title="Week 1", module_order=1, active=True)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="Meaningful lesson", lesson_order=1, status="published")
    db.add(lesson)
    db.commit()

    saved = client.put(
        f"/api/lessons/{lesson.id}/notes",
        json={"content": "A useful study note."},
        headers=auth_headers(student),
    )
    assert saved.status_code == 200
    assert db.query(StudentLessonProgress).filter_by(student_id=student.id, lesson_id=lesson.id).first() is None
    assert derive_current_week(student.id, db) == 1


def test_direct_lesson_returns_empty_outcomes_list_by_default(db):
    student = make_student(db)
    module = Module(code="MOD-002", title="Hardware Basics", module_order=2, active=True)
    db.add(module)
    db.flush()
    lesson = Lesson(
        module_id=module.id,
        title="Hardware Overview",
        lesson_order=1,
        status="published",
    )
    db.add(lesson)
    db.commit()

    response = client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(student))

    assert response.status_code == 200
    assert response.json()["data"]["outcomes"] == []


def test_direct_lesson_requires_auth_and_hides_drafts(db):
    student = make_student(db)
    _, lesson, draft = _seed_lessons(db)

    assert client.get(f"/api/lessons/{lesson.id}").status_code in (401, 403)
    assert client.get(f"/api/lessons/{draft.id}", headers=auth_headers(student)).status_code == 404
