from datetime import datetime, timedelta, timezone
import importlib
import time

from conftest import auth_headers, make_client, make_student
from app.models.lab import LabRun, LabTemplate
from app.models.vm_assignment import VmAssignment
from app.routers.admin_content import router as admin_content_router
from app.routers.labs import router
from app.services import guacamole_service, proxmox_service
from sqlalchemy.orm import sessionmaker

labs_module = importlib.import_module("app.routers.labs")
provision_worker = labs_module._provision_vm_task

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


def test_submit_structured_lab_uses_server_authoritative_grading(db):
    student = make_student(db)
    questions = [
        {
            "id": "component",
            "prompt": "Which component stores data?",
            "context": None,
            "type": "single_choice",
            "options": [{"id": "ssd", "label": "SSD"}, {"id": "ram", "label": "RAM"}],
            "correct": ["ssd"],
            "explanation": "An SSD provides persistent storage.",
        },
        {
            "id": "connectors",
            "prompt": "Select the board power connector.",
            "context": None,
            "type": "multi_choice",
            "options": [{"id": "atx", "label": "24-pin ATX"}, {"id": "sata", "label": "SATA power"}],
            "correct": ["atx"],
            "explanation": "The 24-pin ATX connector powers the motherboard.",
        },
    ]
    structured = LabTemplate(
        title="Structured hardware check",
        description="Deterministic questions",
        lab_type="structured_identification",
        difficulty=1,
        week_number=1,
        is_published=True,
        environment_requirements={},
        success_criteria={"questions": questions},
        required_evidence={},
        hints={},
    )
    break_fix = LabTemplate(
        id=5,
        title="AD Break-Fix",
        description="Real lab regression guard",
        lab_type="break_fix",
        difficulty=4,
        week_number=15,
        is_published=True,
        environment_requirements={},
        success_criteria={"tasks": ["Repair AD"]},
        required_evidence={},
        hints={},
    )
    db.add_all([structured, break_fix])
    db.commit()

    before_submit = client.get(f"/api/labs/{structured.id}", headers=auth_headers(student))
    assert before_submit.status_code == 200
    for question in before_submit.json()["data"]["questions"]:
        assert "correct" not in question
        assert "explanation" not in question

    correct = client.post(
        f"/api/labs/{structured.id}/submit",
        json={"notes": "Completed.", "answers": {"component": ["ssd"], "connectors": ["atx"]}},
        headers=auth_headers(student),
    )
    assert correct.status_code == 200
    returned_questions = correct.json()["data"]["questions"]
    assert [q["id"] for q in returned_questions] == [q["id"] for q in questions]
    for question in returned_questions:
        assert "correct" not in question
        assert "explanation" not in question
    for question in correct.json()["data"]["success_criteria"]["questions"]:
        assert "correct" not in question
        assert "explanation" not in question
    assert correct.json()["data"]["structured_feedback"]["score_pct"] == 100
    db.expire_all()
    correct_run = db.query(LabRun).filter_by(lab_template_id=structured.id, student_id=student.id).one()
    assert correct_run.final_score == 100
    assert [item["correct"] for item in correct_run.structured_feedback["questions"]] == [True, True]

    wrong = client.post(
        f"/api/labs/{structured.id}/submit",
        json={"answers": {"component": ["ram"], "connectors": ["atx"]}},
        headers=auth_headers(student),
    )
    assert wrong.status_code == 200
    db.expire_all()
    wrong_run = db.query(LabRun).filter_by(lab_template_id=structured.id, student_id=student.id).one()
    assert wrong_run.final_score == 50
    assert [item["correct"] for item in wrong_run.structured_feedback["questions"]] == [False, True]

    missing_answers = client.post(f"/api/labs/{structured.id}/submit", json={"notes": "No answers"}, headers=auth_headers(student))
    assert missing_answers.status_code == 400

    self_attested = client.post("/api/labs/5/submit", json={"notes": "Fixed the account."}, headers=auth_headers(student))
    assert self_attested.status_code == 200
    db.expire_all()
    break_fix_run = db.query(LabRun).filter_by(lab_template_id=5, student_id=student.id).one()
    assert break_fix_run.final_score == 10
    assert break_fix_run.structured_feedback is None


def test_structured_cli_lab_requires_the_configured_commands(db):
    student = make_student(db)
    lab = LabTemplate(
        title="Windows CLI diagnosis",
        description="Use commands before choosing a diagnosis.",
        lab_type="structured_cli",
        difficulty=1,
        week_number=1,
        is_published=True,
        environment_requirements={},
        success_criteria={
            "required_commands": ["ipconfig /all", "ping 192.168.1.1", "nslookup intranet.nexus.internal"],
            "questions": [
                {
                    "id": "diagnosis",
                    "prompt": "What failed?",
                    "type": "single_choice",
                    "options": [{"id": "dns", "label": "DNS"}, {"id": "dhcp", "label": "DHCP"}],
                    "correct": ["dns"],
                    "explanation": "The name lookup failed after IP reachability succeeded.",
                }
            ],
        },
        required_evidence={},
        hints={},
    )
    db.add(lab)
    db.commit()

    missing = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"notes": "PS> ipconfig /all", "answers": {"diagnosis": ["dns"]}},
        headers=auth_headers(student),
    )

    assert missing.status_code == 400
    assert missing.json()["detail"] == "Run every required command in the practice terminal before submitting"

    completed = client.post(
        f"/api/labs/{lab.id}/submit",
        json={
            "notes": (
                "PS C:\\Users\\Student> ipconfig /all\n"
                "PS C:\\Users\\Student> ping 192.168.1.1\n"
                "PS C:\\Users\\Student> nslookup intranet.nexus.internal"
            ),
            "answers": {"diagnosis": ["dns"]},
        },
        headers=auth_headers(student),
    )

    assert completed.status_code == 200
    assert completed.json()["data"]["structured_feedback"]["score_pct"] == 100


def test_week_24_final_support_shift_capstone_grades_and_requires_evidence(db):
    from app.services.training_curriculum_seed import FINAL_SUPPORT_SHIFT_PRACTICE

    student = make_student(db)
    lab = LabTemplate(
        title="Final Support Shift",
        description="Triage, diagnose with CLI evidence, decide escalation, and document the outcome.",
        lab_type="structured_capstone",
        difficulty=1,
        week_number=24,
        is_published=True,
        environment_requirements={},
        success_criteria={
            "questions": FINAL_SUPPORT_SHIFT_PRACTICE,
            "required_commands": ["ipconfig /all", "nslookup helpdesk.nexus.internal", "gpresult /r"],
        },
        required_evidence={},
        hints={},
    )
    db.add(lab)
    db.commit()
    answers = {question["id"]: question["correct"] for question in FINAL_SUPPORT_SHIFT_PRACTICE}

    blocked = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"notes": "no terminal evidence gathered", "answers": answers},
        headers=auth_headers(student),
    )
    assert blocked.status_code == 400

    completed = client.post(
        f"/api/labs/{lab.id}/submit",
        json={
            "notes": "ipconfig /all\nnslookup helpdesk.nexus.internal\ngpresult /r",
            "answers": answers,
        },
        headers=auth_headers(student),
    )
    assert completed.status_code == 200
    body = completed.json()["data"]
    assert body["status"] == "submitted"
    assert body["structured_feedback"]["score_pct"] == 100


def test_get_lab_unauthenticated(db):
    lab = _seed_lab(db)
    res = client.get(f"/api/labs/{lab.id}")
    assert res.status_code == 401


def test_start_vm_backed_lab_provisions_guacamole_session(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    queued = []
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: queued.append(assignment_id))

    before = time.monotonic()
    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    elapsed = time.monotonic() - before

    assert started.status_code == 202
    assert elapsed < 1
    data = started.json()["data"]
    assert data["status"] == "in_progress"
    assert data["vm_assignment"]["status"] == "provisioning"
    assert data["vm_assignment"]["vmid"] is None

    assignment = db.query(VmAssignment).filter(VmAssignment.lab_run_id == data["run_id"]).one()
    assert queued == [assignment.id]

    second = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assert second.status_code == 202
    assert db.query(VmAssignment).filter(VmAssignment.lab_run_id == data["run_id"]).count() == 1
    assert queued == [assignment.id]


def test_start_vm_backed_lab_marks_assignment_failed_without_ip(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)

    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]

    monkeypatch.setattr(proxmox_service, "clone_template", lambda template_vmid, name: 211)
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(proxmox_service, "get_vm_ip", lambda vmid: None)
    provision_worker(assignment_id)

    db.expire_all()
    assignment = db.query(VmAssignment).filter(VmAssignment.id == assignment_id).one()
    assert assignment.status == "failed"
    assert assignment.vmid == 211
    assert assignment.provisioning_error == "Lab environment provisioning timed out. Please contact an administrator."


def test_provisioning_worker_persists_each_resource(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)
    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]

    monkeypatch.setattr(proxmox_service, "clone_template", lambda template_vmid, name: 215)
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(proxmox_service, "get_vm_ip", lambda vmid: "10.0.0.29")
    monkeypatch.setattr(guacamole_service, "create_connection", lambda vm_ip, vmid: "conn-215")
    provision_worker(assignment_id)

    db.expire_all()
    assignment = db.query(VmAssignment).filter_by(id=assignment_id).one()
    assert assignment.status == "running"
    assert assignment.vmid == 215
    assert assignment.ip_address == "10.0.0.29"
    assert assignment.guac_conn_id == "conn-215"
    assert assignment.started_at is not None
    assert assignment.expires_at is not None


def test_submit_vm_backed_lab_destroys_assignment(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    destroyed = []
    deleted = []

    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)
    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]
    assignment = db.query(VmAssignment).filter(VmAssignment.id == assignment_id).one()
    assignment.vmid = 212
    assignment.status = "running"
    assignment.ip_address = "10.0.0.26"
    assignment.guac_conn_id = "conn-212"
    assignment.guac_username = "temporary-student"
    db.commit()

    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid: destroyed.append(vmid))
    monkeypatch.setattr(guacamole_service, "delete_connection", lambda conn_id: deleted.append(conn_id))
    deleted_users = []
    monkeypatch.setattr(guacamole_service, "delete_user", lambda username: deleted_users.append(username))

    submitted = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"notes": "Finished the VM remediation steps."},
        headers=auth_headers(student),
    )

    assert submitted.status_code == 200
    db.expire_all()
    assignment = db.query(VmAssignment).filter(VmAssignment.vmid == 212).one()
    assert assignment.status == "destroyed"
    assert assignment.destroyed_at is not None
    assert destroyed == [212]
    assert deleted == ["conn-212"]
    assert deleted_users == ["temporary-student"]


def test_running_assignment_survives_refresh_and_issues_scoped_access(monkeypatch, db):
    student = make_student(db)
    other = make_student(db, username="student2")
    lab = _seed_lab(db, proxmox_template_vmid=900)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        vmid=214,
        student_id=student.id,
        lab_run_id=run.id,
        status="running",
        ip_address="10.0.0.28",
        guac_conn_id="conn-214",
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(assignment)
    db.commit()

    refreshed = client.get(f"/api/labs/{lab.id}", headers=auth_headers(student))
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["vm_assignment"]["vmid"] == 214

    monkeypatch.setattr(
        guacamole_service,
        "create_scoped_access",
        lambda conn_id, assignment_id, previous_username: {
            "username": "scoped-user",
            "url": "https://guac.local/#/client/safe?token=student-token",
        },
    )
    access = client.post(f"/api/labs/{lab.id}/vm-access", headers=auth_headers(student))
    assert access.status_code == 200
    assert access.json()["data"]["url"].endswith("token=student-token")
    db.expire_all()
    assert db.query(VmAssignment).filter_by(id=assignment.id).one().guac_username == "scoped-user"

    denied = client.post(f"/api/labs/{lab.id}/vm-access", headers=auth_headers(other))
    assert denied.status_code == 404


def test_expired_assignment_cannot_reconnect_and_is_queued_for_destroy(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        vmid=216,
        student_id=student.id,
        lab_run_id=run.id,
        status="running",
        guac_conn_id="conn-216",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db.add(assignment)
    db.commit()
    queued = []
    monkeypatch.setattr(labs_module, "_destroy_vm_task", lambda assignment_id: queued.append(assignment_id))

    access = client.post(f"/api/labs/{lab.id}/vm-access", headers=auth_headers(student))
    assert access.status_code == 410
    status = client.get(f"/api/labs/{lab.id}/vm-status", headers=auth_headers(student))
    assert status.status_code == 200
    assert status.json()["data"]["status"] == "destroying"
    assert queued == [assignment.id]


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

    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid: destroyed.append(vmid))
    monkeypatch.setattr(guacamole_service, "delete_connection", lambda conn_id: deleted.append(conn_id))

    res = admin_client.delete("/api/admin/vms/cleanup", headers={"X-Admin-Key": "unit-test-admin"})

    assert res.status_code == 200
    assert res.json()["data"]["destroyed"] == [213]
    db.refresh(assignment)
    assert assignment.status == "destroyed"
    assert assignment.destroyed_at is not None
    assert destroyed == [213]
    assert deleted == ["conn-213"]


def test_admin_can_see_safe_provisioning_failure(db, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "unit-test-admin")
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        student_id=student.id,
        lab_run_id=run.id,
        status="failed",
        provisioning_error="Lab environment provisioning failed. Please contact an administrator.",
    )
    db.add(assignment)
    db.commit()

    res = admin_client.get("/api/admin/vms/assignments", headers={"X-Admin-Key": "unit-test-admin"})

    assert res.status_code == 200
    row = res.json()["data"][0]
    assert row["student_name"] == student.name
    assert row["lab_title"] == lab.title
    assert row["status"] == "failed"
    assert row["provisioning_error"] == assignment.provisioning_error
    assert "guac_username" not in row
