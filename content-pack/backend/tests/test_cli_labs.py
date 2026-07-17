from conftest import auth_headers, make_client, make_student

from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.xp_ledger import XPLedger
from app.routers.cli_labs import router

client = make_client(router)


def _seed_cli_lab(db):
    lab = CliLab(
        id="meet-cli-001",
        compartment_id="meet-the-cli",
        vendor_id="cisco-ios",
        title="First Contact",
        difficulty="Beginner",
        est_minutes=5,
        order_index=1,
        content={
            "id": "meet-cli-001",
            "title": "First Contact",
            "scenario": "Connect to the switch.",
            "objectives": [],
            "successCriteria": {"requiredModes": ["config"]},
        },
    )
    db.add(lab)
    db.commit()
    return lab


def test_list_cli_labs_requires_auth(db):
    _seed_cli_lab(db)

    res = client.get("/api/cli-labs")

    assert res.status_code == 401


def test_list_cli_labs_returns_completion_state(db):
    student = make_student(db)
    lab = _seed_cli_lab(db)

    res = client.get("/api/cli-labs", headers=auth_headers(student))

    assert res.status_code == 200
    rows = res.json()["data"]
    assert len(rows) == 1
    assert rows[0]["id"] == lab.id
    assert rows[0]["completed"] is False


def test_get_cli_lab_returns_content(db):
    student = make_student(db)
    lab = _seed_cli_lab(db)

    res = client.get(f"/api/cli-labs/{lab.id}", headers=auth_headers(student))

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == lab.id
    assert data["content"]["title"] == "First Contact"


def test_complete_cli_lab_awards_first_completion_xp(db):
    student = make_student(db)
    lab = _seed_cli_lab(db)

    res = client.post(
        f"/api/cli-labs/{lab.id}/complete",
        json={"commandLog": [{"cmd": "enable secret cisco", "ts": 1000}], "durationMs": 120000},
        headers=auth_headers(student),
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["completed"] is True
    assert data["xp_awarded"] == 50
    assert data["duplicate_completion"] is False

    attempt = db.query(CliLabAttempt).filter(CliLabAttempt.student_id == student.id, CliLabAttempt.lab_id == lab.id).one()
    assert attempt.command_log == [{"cmd": "enable secret [redacted]", "ts": 1000}]
    assert attempt.duration_ms == 120000

    db.refresh(student)
    assert student.total_xp == 50
    ledger = db.query(XPLedger).filter(XPLedger.student_id == student.id, XPLedger.source_type == "cli_lab").one()
    assert ledger.delta == 50


def test_complete_cli_lab_does_not_duplicate_xp(db):
    student = make_student(db)
    lab = _seed_cli_lab(db)
    headers = auth_headers(student)

    first = client.post(f"/api/cli-labs/{lab.id}/complete", json={"commandLog": [], "durationMs": 1000}, headers=headers)
    second = client.post(f"/api/cli-labs/{lab.id}/complete", json={"commandLog": [], "durationMs": 1000}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["xp_awarded"] == 0
    assert second.json()["data"]["duplicate_completion"] is True

    db.refresh(student)
    assert student.total_xp == 50
    assert db.query(XPLedger).filter(XPLedger.student_id == student.id, XPLedger.source_type == "cli_lab").count() == 1
    assert db.query(CliLabAttempt).filter(CliLabAttempt.student_id == student.id, CliLabAttempt.lab_id == lab.id).count() == 2


def test_complete_unknown_cli_lab_returns_404(db):
    student = make_student(db)

    res = client.post(
        "/api/cli-labs/missing/complete",
        json={"commandLog": [], "durationMs": 1000},
        headers=auth_headers(student),
    )

    assert res.status_code == 404
