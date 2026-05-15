from conftest import auth_headers, make_client, make_student
from app.models.capstone import CapstoneTemplate
from app.routers.admin_content import router as admin_content_router
from app.routers.capstones import router

client = make_client(router, admin_content_router)


def _seed_capstone(db, title="Hardware Capstone", week_number=4, is_published=True):
    capstone = CapstoneTemplate(
        title=title,
        description="Document a troubleshooting scenario.",
        week_number=week_number,
        is_published=is_published,
        requirements={"skills": ["Apply a systematic methodology"]},
        deliverables={"items": ["Write up your analysis"]},
        estimated_hours=3,
        rubric={"technical_accuracy": "Correct troubleshooting logic"},
    )
    db.add(capstone)
    db.commit()
    db.refresh(capstone)
    return capstone


def test_list_capstones_filters_to_published_week(db):
    student = make_student(db)
    published = _seed_capstone(db, title="Published Capstone", week_number=4, is_published=True)
    _seed_capstone(db, title="Hidden Capstone", week_number=4, is_published=False)
    _seed_capstone(db, title="Other Week Capstone", week_number=8, is_published=True)

    res = client.get("/api/capstones?week_number=4", headers=auth_headers(student))

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == published.id
    assert data[0]["status"] == "not_started"


def test_start_and_submit_capstone_updates_run_state(db):
    student = make_student(db)
    capstone = _seed_capstone(db)

    started = client.post(f"/api/capstones/{capstone.id}/start", headers=auth_headers(student))
    assert started.status_code == 200
    assert started.json()["data"]["status"] == "in_progress"

    submitted = client.post(
        f"/api/capstones/{capstone.id}/submit",
        json={"notes": "Completed the hardware write-up and troubleshooting reflection."},
        headers=auth_headers(student),
    )

    assert submitted.status_code == 200
    body = submitted.json()["data"]
    assert body["status"] == "submitted"
    assert body["notes"] == "Completed the hardware write-up and troubleshooting reflection."


def test_admin_created_published_capstone_is_student_visible(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    student = make_student(db)

    created = client.post(
        "/api/admin/capstones/templates",
        json={
            "title": "Published Admin Capstone",
            "description": "Visible project",
            "week_number": 6,
            "is_published": True,
            "requirements": {"skills": ["Troubleshoot"]},
            "deliverables": {"items": ["Write-up"]},
            "estimated_hours": 2,
            "rubric": {"technical_accuracy": "Accurate"},
        },
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert created.status_code == 200
    capstone_id = created.json()["data"]["capstone_template_id"]

    listed = client.get("/api/capstones?week_number=6", headers=auth_headers(student))

    assert listed.status_code == 200
    data = listed.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == capstone_id
    assert data[0]["week_number"] == 6


def test_admin_can_publish_existing_capstone(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    student = make_student(db)
    capstone = _seed_capstone(db, title="Draft Admin Capstone", week_number=7, is_published=False)

    updated = client.put(
        f"/api/admin/capstones/templates/{capstone.id}",
        json={"is_published": True, "week_number": 7},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["is_published"] is True

    listed = client.get("/api/capstones?week_number=7", headers=auth_headers(student))
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()["data"]] == [capstone.id]


def test_get_capstone_unauthenticated(db):
    capstone = _seed_capstone(db)
    res = client.get(f"/api/capstones/{capstone.id}")
    assert res.status_code == 401
