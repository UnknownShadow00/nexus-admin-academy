from datetime import datetime, timedelta, timezone

from conftest import _Session, auth_headers, make_client, make_student
from app.models.lab import LabRun, LabTemplate
from app.models.vm_assignment import VmAssignment
from app.routers.admin_content import router as admin_content_router
from app.routers import labs
from app.routers.labs import router
from app.services import guacamole_service, proxmox_service

client = make_client(router)
admin_client = make_client(admin_content_router)


def _seed_lab(db, title="Subnetting Practice", week_number=1, is_published=True, proxmox_template_vmid=None):
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
        proxmox_template_vmid=proxmox_template_vmid,
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


def test_start_vm_backed_lab_provisions_guacamole_session(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)

    monkeypatch.setattr(labs, "SessionLocal", _Session)
    monkeypatch.setattr(proxmox_service, "clone_template", lambda template_vmid, name: 210)
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(proxmox_service, "get_vm_ip", lambda vmid: "10.0.0.25")
    monkeypatch.setattr(guacamole_service, "create_connection", lambda vm_ip, vmid: "conn-210")
    monkeypatch.setattr(guacamole_service, "get_student_token_url", lambda conn_id, lab_run_id: f"https://guac.local/{conn_id}")

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))

    assert started.status_code == 202
    data = started.json()["data"]
    assert data["status"] == "in_progress"
    assert data["vm_status"] == "provisioning"
    assert "guac_token_url" not in data

    # TestClient runs the background task before returning, so status is final
    status_res = client.get(f"/api/labs/{lab.id}/vm-status", headers=auth_headers(student))
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["vm_status"] == "ready"
    assert status_data["guac_token_url"] == "https://guac.local/conn-210"

    assignment = db.query(VmAssignment).filter(VmAssignment.lab_run_id == data["run_id"]).one()
    assert assignment.status == "running"
    assert assignment.ip_address == "10.0.0.25"
    assert assignment.guac_conn_id == "conn-210"


def test_start_vm_backed_lab_marks_assignment_failed_without_ip(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)

    monkeypatch.setattr(labs, "SessionLocal", _Session)
    monkeypatch.setattr(proxmox_service, "clone_template", lambda template_vmid, name: 211)
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(proxmox_service, "get_vm_ip", lambda vmid: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))

    assert started.status_code == 202

    status_res = client.get(f"/api/labs/{lab.id}/vm-status", headers=auth_headers(student))
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["vm_status"] == "failed"
    assert status_data["guac_token_url"] is None

    assignment = db.query(VmAssignment).filter(VmAssignment.vmid == 211).one()
    assert assignment.status == "failed"


def test_submit_vm_backed_lab_destroys_assignment(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    destroyed = []
    deleted = []
    deleted_users = []

    monkeypatch.setattr(labs, "SessionLocal", _Session)
    monkeypatch.setattr(proxmox_service, "clone_template", lambda template_vmid, name: 212)
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(proxmox_service, "get_vm_ip", lambda vmid: "10.0.0.26")
    monkeypatch.setattr(guacamole_service, "create_connection", lambda vm_ip, vmid: "conn-212")
    monkeypatch.setattr(guacamole_service, "get_student_token_url", lambda conn_id, lab_run_id: f"https://guac.local/{conn_id}")
    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid: destroyed.append(vmid))
    monkeypatch.setattr(guacamole_service, "delete_connection", lambda conn_id: deleted.append(conn_id))
    monkeypatch.setattr(guacamole_service, "delete_lab_user", lambda lab_run_id: deleted_users.append(lab_run_id))

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assert started.status_code == 202

    submitted = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"notes": "Finished the VM remediation steps."},
        headers=auth_headers(student),
    )

    assert submitted.status_code == 200
    assignment = db.query(VmAssignment).filter(VmAssignment.vmid == 212).one()
    assert assignment.status == "destroyed"
    assert assignment.destroyed_at is not None
    assert destroyed == [212]
    assert deleted == ["conn-212"]
    assert deleted_users == [assignment.lab_run_id]


def test_upload_lab_evidence_rejects_oversized_file(db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    student = make_student(db)
    lab = _seed_lab(db)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.commit()

    big = b"x" * (5 * 1024 * 1024 + 1)
    res = client.post(
        f"/api/labs/{run.id}/evidence",
        files={"file": ("proof.png", big, "image/png")},
        headers=auth_headers(student),
    )

    assert res.status_code == 400
    assert "too large" in res.json()["detail"].lower()


def test_upload_lab_evidence_rejects_other_students_run(db, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    owner = make_student(db, username="owner1")
    intruder = make_student(db, username="intruder1")
    lab = _seed_lab(db)
    run = LabRun(lab_template_id=lab.id, student_id=owner.id, status="in_progress")
    db.add(run)
    db.commit()

    res = client.post(
        f"/api/labs/{run.id}/evidence",
        files={"file": ("proof.png", b"fake-image", "image/png")},
        headers=auth_headers(intruder),
    )

    assert res.status_code == 403


def test_get_student_token_url_uses_per_run_user_and_nul_encoding(monkeypatch):
    import base64

    monkeypatch.setenv("GUACAMOLE_URL", "https://guac.local/guacamole")
    monkeypatch.setenv("GUACAMOLE_ADMIN_USER", "guacadmin")
    monkeypatch.setenv("GUACAMOLE_ADMIN_PASS", "adminpass")
    monkeypatch.setenv("GUACAMOLE_DATASOURCE", "postgresql")

    calls = []

    class _Resp:
        def __init__(self, payload=None, status_code=200):
            self._payload = payload or {}
            self.status_code = status_code

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def fake_post(url, data=None, json=None, headers=None, timeout=None):
        calls.append(("POST", url, data, json))
        if url.endswith("/api/tokens"):
            if data["username"] == "guacadmin":
                return _Resp({"authToken": "ADMIN-TOKEN"})
            return _Resp({"authToken": "STUDENT-TOKEN"})
        return _Resp()

    def fake_patch(url, json=None, headers=None, timeout=None):
        calls.append(("PATCH", url, None, json))
        return _Resp()

    monkeypatch.setattr(guacamole_service.requests, "post", fake_post)
    monkeypatch.setattr(guacamole_service.requests, "patch", fake_patch)

    url = guacamole_service.get_student_token_url("42", lab_run_id=7)

    # Client URL: base64("{identifier}\0c\0{datasource}") + student (not admin) token
    expected_id = base64.b64encode(b"42\0c\0postgresql").decode()
    assert url == f"https://guac.local/guacamole/#/client/{expected_id}?token=STUDENT-TOKEN"
    assert "ADMIN-TOKEN" not in url

    # Per-lab-run user created and granted READ on only its connection
    user_creates = [c for c in calls if c[0] == "POST" and c[1].endswith("/users")]
    assert len(user_creates) == 1
    assert user_creates[0][3]["username"] == "lab-run-7"

    perm_patches = [c for c in calls if c[0] == "PATCH"]
    assert len(perm_patches) == 1
    assert perm_patches[0][1].endswith("/users/lab-run-7/permissions")
    assert perm_patches[0][3] == [{"op": "add", "path": "/connectionPermissions/42", "value": "READ"}]


def test_admin_cleanup_destroys_idle_vm_assignments(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "unit-test-admin")
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        vmid=213,
        student_id=student.id,
        lab_run_id=run.id,
        status="running",
        ip_address="10.0.0.27",
        guac_conn_id="conn-213",
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    db.add(assignment)
    db.commit()
    destroyed = []
    deleted = []
    deleted_users = []

    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid: destroyed.append(vmid))
    monkeypatch.setattr(guacamole_service, "delete_connection", lambda conn_id: deleted.append(conn_id))
    monkeypatch.setattr(guacamole_service, "delete_lab_user", lambda lab_run_id: deleted_users.append(lab_run_id))

    res = admin_client.delete("/api/admin/vms/cleanup", headers={"X-Admin-Key": "unit-test-admin"})

    assert res.status_code == 200
    assert res.json()["data"]["destroyed"] == [213]
    db.refresh(assignment)
    assert assignment.status == "destroyed"
    assert assignment.destroyed_at is not None
    assert destroyed == [213]
    assert deleted == ["conn-213"]
    assert deleted_users == [run.id]
