from conftest import auth_headers, make_client, make_student
from app.models.ticket import Ticket
from app.routers.tickets import router

client = make_client(router)


def _seed_ticket(db, title="PC won't boot", week_number=1):
    ticket = Ticket(
        title=title,
        description="The PC powers on but does not POST.",
        difficulty=2,
        week_number=week_number,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def test_list_tickets_empty(db):
    student = make_student(db)
    res = client.get("/api/tickets", headers=auth_headers(student))
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_list_tickets_returns_seeded(db):
    student = make_student(db)
    ticket = _seed_ticket(db, title="No display output")
    res = client.get("/api/tickets", headers=auth_headers(student))
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "No display output"
    assert data[0]["id"] == ticket.id


def test_list_tickets_week_filter(db):
    student = make_student(db)
    _seed_ticket(db, title="Week 1 ticket", week_number=1)
    _seed_ticket(db, title="Week 2 ticket", week_number=2)
    res = client.get("/api/tickets?week_number=1", headers=auth_headers(student))
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Week 1 ticket"


def test_list_tickets_unauthenticated(db):
    res = client.get("/api/tickets")
    assert res.status_code == 401


def test_submit_rejects_evidence_owned_by_another_student(db, monkeypatch):
    from app.models.evidence import EvidenceArtifact

    ticket = _seed_ticket(db)
    owner = make_student(db, username="owner2")
    intruder = make_student(db, username="intruder2")
    artifact = EvidenceArtifact(
        student_id=owner.id,
        submission_type="ticket",
        submission_id=ticket.id,
        artifact_type="screenshot",
        storage_key="someone-elses.png",
    )
    db.add(artifact)
    db.commit()

    res = client.post(
        f"/api/tickets/{ticket.id}/submit",
        json={
            "student_id": intruder.id,
            "symptom": "Machine will not boot to the OS at all.",
            "root_cause": "Boot order was changed to PXE first.",
            "resolution": "Restored boot order to the internal SSD in firmware.",
            "verification": "Machine boots normally, user confirmed login.",
            "before_screenshot_id": artifact.id,
        },
        headers=auth_headers(intruder),
    )

    assert res.status_code == 403
    assert "does not belong" in res.json()["detail"].lower()


def test_ticket_upload_rejects_oversized_file(db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    student = make_student(db, username="uploader1")

    big = b"x" * (5 * 1024 * 1024 + 1)
    res = client.post(
        "/api/tickets/uploads",
        files={"files": ("shot.png", big, "image/png")},
        headers=auth_headers(student),
    )

    assert res.status_code == 400


def test_ticket_upload_persists_file_to_upload_dir(db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    student = make_student(db, username="uploader3")

    res = client.post(
        "/api/tickets/uploads",
        files={"files": ("shot.png", b"\x89PNG-fake-bytes", "image/png")},
        headers=auth_headers(student),
    )

    assert res.status_code == 200
    saved = res.json()["data"]["files"]
    assert len(saved) == 1
    assert (tmp_path / saved[0]).read_bytes() == b"\x89PNG-fake-bytes"


def test_evidence_upload_persists_file_and_stamps_owner(db, tmp_path, monkeypatch):
    from app.models.evidence import EvidenceArtifact
    from app.routers.evidence import router as evidence_router

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    evidence_client = make_client(evidence_router)
    ticket = _seed_ticket(db)
    student = make_student(db, username="uploader4")

    res = evidence_client.post(
        "/api/evidence/upload",
        files={"file": ("shot.png", b"\x89PNG-fake-bytes", "image/png")},
        data={"ticket_id": str(ticket.id), "artifact_type": "screenshot"},
        headers=auth_headers(student),
    )

    assert res.status_code == 200
    body = res.json()["data"]
    assert (tmp_path / body["storage_key"]).read_bytes() == b"\x89PNG-fake-bytes"
    row = db.query(EvidenceArtifact).filter(EvidenceArtifact.id == body["artifact_id"]).first()
    assert row is not None
    assert row.student_id == student.id


def test_evidence_upload_rejects_oversized_file(db, tmp_path, monkeypatch):
    from app.routers.evidence import router as evidence_router

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    evidence_client = make_client(evidence_router)
    ticket = _seed_ticket(db)
    student = make_student(db, username="uploader2")

    big = b"x" * (5 * 1024 * 1024 + 1)
    res = evidence_client.post(
        "/api/evidence/upload",
        files={"file": ("shot.png", big, "image/png")},
        data={"ticket_id": str(ticket.id), "artifact_type": "screenshot"},
        headers=auth_headers(student),
    )

    assert res.status_code == 400
    assert "too large" in res.json()["detail"].lower()
