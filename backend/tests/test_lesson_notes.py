from conftest import auth_headers, make_client, make_student
from app.models.learning import Lesson, Module
from app.routers.lesson_notes import router as lesson_router


client = make_client(lesson_router)


def _seed_lessons(db):
    module = Module(code="MOD-001", title="Support Basics", module_order=1, active=True)
    db.add(module)
    db.flush()
    published = Lesson(
        module_id=module.id,
        title="Ticket Triage",
        summary="Read the ticket and identify the next safe action.",
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
        "video_url": None,
        "module_code": module.code,
        "module_title": module.title,
        "is_orientation": False,
    }

    saved = client.put(
        f"/api/lessons/{lesson.id}/notes",
        json={"content": "Verify impact before changing anything."},
        headers=auth_headers(student),
    )
    assert saved.status_code == 200
    assert client.get(f"/api/lessons/{lesson.id}/notes", headers=auth_headers(student)).json()["data"]["content"] == "Verify impact before changing anything."
    assert client.get(f"/api/lessons/{lesson.id}/notes", headers=auth_headers(other)).json()["data"]["content"] == ""


def test_direct_lesson_requires_auth_and_hides_drafts(db):
    student = make_student(db)
    _, lesson, draft = _seed_lessons(db)

    assert client.get(f"/api/lessons/{lesson.id}").status_code in (401, 403)
    assert client.get(f"/api/lessons/{draft.id}", headers=auth_headers(student)).status_code == 404
