from datetime import UTC, datetime

from conftest import auth_headers, make_client, make_student

from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.training import TrainingWeek, TrainingWeekActivity
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


def test_network_and_switch_labs_stay_locked_until_halfway_through_network_plus(
    monkeypatch, db
):
    student = make_student(db, "network-lab-gate")
    meet_cli = _seed_cli_lab(db)
    network_lab = CliLab(
        id="dev-nf-encap-001",
        compartment_id="network-foundations",
        vendor_id="cisco-ios",
        title="Frame Foundations",
        difficulty="Beginner",
        est_minutes=8,
        order_index=1,
        content={},
    )
    switch_lab = CliLab(
        id="dev-sw-act-01",
        compartment_id="learn-switching",
        vendor_id="cisco-ios",
        title="Read the Switch Map",
        difficulty="Beginner",
        est_minutes=8,
        order_index=1,
        content={},
    )
    db.add_all([network_lab, switch_lab])
    db.commit()
    current_week = {"value": 10}
    monkeypatch.setattr(
        "app.routers.cli_labs.derive_current_week",
        lambda _student_id, _db: current_week["value"],
    )
    monkeypatch.setattr(
        "app.services.progression_service.derive_current_week",
        lambda _student_id, _db: current_week["value"],
    )

    before = client.get("/api/cli-labs", headers=auth_headers(student))
    blocked = client.get(
        f"/api/cli-labs/{switch_lab.id}", headers=auth_headers(student)
    )

    assert [row["id"] for row in before.json()["data"]] == [meet_cli.id]
    assert blocked.status_code == 403

    current_week["value"] = 11
    after = client.get("/api/cli-labs", headers=auth_headers(student))

    assert {row["id"] for row in after.json()["data"]} == {
        meet_cli.id,
        network_lab.id,
        switch_lab.id,
    }


def test_existing_cli_lab_completion_remains_visible_when_gate_moves(db):
    student = make_student(db, "existing-network-lab-progress")
    lab = CliLab(
        id="dev-sw-act-01",
        compartment_id="learn-switching",
        vendor_id="cisco-ios",
        title="Read the Switch Map",
        difficulty="Beginner",
        est_minutes=8,
        order_index=1,
        content={},
    )
    db.add(lab)
    db.flush()
    db.add(
        CliLabAttempt(
            student_id=student.id,
            lab_id=lab.id,
            completed_at=datetime.now(UTC),
            xp_awarded=50,
        )
    )
    db.commit()

    response = client.get("/api/cli-labs", headers=auth_headers(student))

    assert [row["id"] for row in response.json()["data"]] == [lab.id]
    assert response.json()["data"][0]["completed"] is True


def test_reached_required_cli_lab_bypasses_later_pack_gate(monkeypatch, db):
    student = make_student(db, "required-network-lab")
    lab = CliLab(
        id="required-network-foundations",
        compartment_id="network-foundations",
        vendor_id="cisco-ios",
        title="Required Network Foundations",
        difficulty="Beginner",
        est_minutes=8,
        order_index=1,
        content={},
    )
    week = TrainingWeek(
        week_number=9,
        display_order=9,
        title="Week 9",
        learning_goals=[],
        requires_previous_week=False,
    )
    db.add_all([lab, week])
    db.flush()
    db.add(
        TrainingWeekActivity(
            stable_id="week-9-required-network-foundations",
            training_week_id=week.id,
            activity_type="networking_lab",
            content_ref=lab.id,
            display_order=1,
            is_required=True,
            prerequisite_mode="soft",
            metadata_json={},
        )
    )
    db.commit()
    monkeypatch.setattr(
        "app.routers.cli_labs.derive_current_week",
        lambda _student_id, _db: 9,
    )

    listing = client.get("/api/cli-labs", headers=auth_headers(student))
    detail = client.get(
        f"/api/cli-labs/{lab.id}", headers=auth_headers(student)
    )
    completion = client.post(
        f"/api/cli-labs/{lab.id}/complete",
        json={"commandLog": [], "durationMs": 1000},
        headers=auth_headers(student),
    )

    assert [row["id"] for row in listing.json()["data"]] == [lab.id]
    assert detail.status_code == 200
    assert completion.status_code == 200


def test_detail_and_completion_enforce_active_network_module_gate(
    monkeypatch, db
):
    student = make_student(db, "active-network-gate")
    lab = CliLab(
        id="active-network-gate-lab",
        compartment_id="network-foundations",
        vendor_id="cisco-ios",
        title="Active Network Gate",
        difficulty="Beginner",
        est_minutes=8,
        order_index=1,
        content={},
    )
    db.add(lab)
    db.commit()
    monkeypatch.setattr(
        "app.routers.cli_labs.derive_current_week",
        lambda _student_id, _db: 11,
    )
    monkeypatch.setattr(
        "app.services.training_service.network_cli_gate_is_unlocked",
        lambda _db, _student: False,
    )

    detail = client.get(
        f"/api/cli-labs/{lab.id}", headers=auth_headers(student)
    )
    completion = client.post(
        f"/api/cli-labs/{lab.id}/complete",
        json={"commandLog": [], "durationMs": 1000},
        headers=auth_headers(student),
    )

    assert detail.status_code == 403
    assert detail.json()["code"] == "PREREQUISITE_NOT_MET"
    assert completion.status_code == 403
    assert completion.json()["code"] == "PREREQUISITE_NOT_MET"
    assert db.query(CliLabAttempt).filter_by(student_id=student.id).count() == 0


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
