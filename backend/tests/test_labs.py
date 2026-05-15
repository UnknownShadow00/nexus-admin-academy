from conftest import auth_headers, make_client, make_student
from app.models.lab import LabTemplate
from app.routers.labs import router

client = make_client(router)


def _seed_lab(db, title="Subnetting Practice", week_number=1, is_published=True):
    lab = LabTemplate(
        title=title,
        description="Practice exercise",
        lab_type="guided",
        difficulty=2,
        week_number=week_number,
        estimated_minutes=30,
        environment_requirements={},
        setup_instructions="Read the prompt and document your work.",
        success_criteria={"tasks": ["Complete the worksheet"]},
        required_evidence={},
        hints=["Use binary"],
        is_published=is_published,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


def test_list_labs_filters_to_published_week(db):
    student = make_student(db)
    published = _seed_lab(db, title="Published Lab", week_number=2, is_published=True)
    _seed_lab(db, title="Hidden Lab", week_number=2, is_published=False)
    _seed_lab(db, title="Other Week Lab", week_number=3, is_published=True)

    res = client.get("/api/labs?week_number=2", headers=auth_headers(student))

    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == published.id
    assert data[0]["status"] == "not_started"


def test_start_and_submit_lab_updates_run_state(db):
    student = make_student(db)
    lab = _seed_lab(db)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assert started.status_code == 200
    assert started.json()["data"]["status"] == "in_progress"

    submitted = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"notes": "Calculated the broadcast address and host range."},
        headers=auth_headers(student),
    )

    assert submitted.status_code == 200
    body = submitted.json()["data"]
    assert body["status"] == "submitted"
    assert body["notes"] == "Calculated the broadcast address and host range."


def test_get_lab_unauthenticated(db):
    lab = _seed_lab(db)
    res = client.get(f"/api/labs/{lab.id}")
    assert res.status_code == 401
