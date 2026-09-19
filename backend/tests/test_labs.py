from datetime import datetime, timedelta, timezone
import importlib
import json
import threading
import time

from fastapi import BackgroundTasks, HTTPException
from conftest import auth_headers, make_client, make_student
from app.database import Base
from app.models.lab import LabRun, LabTemplate
from app.models.student import Student
from app.models.vm_assignment import VmAssignment
from app.routers.admin_content import router as admin_content_router
from app.routers.labs import router
from app.services import guacamole_service, proxmox_service
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

labs_module = importlib.import_module("app.routers.labs")
provision_worker = labs_module._provision_vm_task

client = make_client(router)
admin_client = make_client(admin_content_router)


def _seed_lab(
    db,
    title="Subnetting Practice",
    week_number=1,
    is_published=True,
    proxmox_template_vmid=None,
    environment_requirements=None,
):
    lab = LabTemplate(
        title=title,
        description="Practice exercise",
        lab_type="guided",
        difficulty=2,
        week_number=week_number,
        estimated_minutes=30,
        environment_requirements=environment_requirements or {},
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


def test_endpoint_workbench_hides_answer_keys_and_requires_structured_documentation(db):
    student = make_student(db)
    lab = LabTemplate(
        title="Endpoint evidence case",
        description="Inspect evidence before deciding.",
        lab_type="structured_endpoint",
        difficulty=2,
        week_number=1,
        is_published=True,
        environment_requirements={},
        success_criteria={
            "endpoint_workbench": {
                "guidance_level": "troubleshoot",
                "brief": "A managed app is missing.",
                "required_inspections": ["device", "apps"],
                "panels": [
                    {"id": "device", "label": "Device", "fields": [{"label": "Managed", "value": "Yes"}]},
                    {"id": "apps", "label": "Applications", "fields": [{"label": "Detection", "value": "Failed"}]},
                ],
                "verification": {
                    "label": "Simulated device state after action",
                    "description": "This is training evidence, not a claim that a real device changed.",
                    "fields": [],
                },
                "documentation_required": True,
            },
            "questions": [
                {
                    "id": "diagnosis",
                    "prompt": "What explains the symptom?",
                    "type": "single_choice",
                    "options": [{"id": "detection", "label": "Detection mismatch"}],
                    "correct": ["detection"],
                    "explanation": "The install exists but detection failed.",
                }
            ],
        },
        required_evidence={},
        hints={},
    )
    db.add(lab)
    db.commit()

    fetched = client.get(f"/api/labs/{lab.id}", headers=auth_headers(student))
    assert fetched.status_code == 200
    body = fetched.json()["data"]
    assert body["success_criteria"]["endpoint_workbench"]["required_inspections"] == ["device", "apps"]
    assert "verification" not in body["success_criteria"]["endpoint_workbench"]
    assert "correct" not in body["success_criteria"]["questions"][0]
    assert "explanation" not in body["success_criteria"]["questions"][0]

    missing_inspection = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": {"diagnosis": ["detection"]}, "inspected_panel_ids": ["device"]},
        headers=auth_headers(student),
    )
    assert missing_inspection.status_code == 200
    assert missing_inspection.json()["data"]["ready"] is False
    assert "verification" not in missing_inspection.json()["data"]

    wrong_verification = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": {"diagnosis": ["wrong"]}, "inspected_panel_ids": ["device", "apps"]},
        headers=auth_headers(student),
    )
    assert wrong_verification.status_code == 200
    assert wrong_verification.json()["data"] == {
        "ready": False,
        "message": "The selected path did not produce the expected state. Re-open the evidence and revise the unsupported decision.",
    }
    assert "verification" not in wrong_verification.json()["data"]

    completion_payload = {
        "answers": {"diagnosis": ["detection"]},
        "notes": '{"issue":"App missing","evidence":"Detection failed","action":"Correct detection rule","verification":"App reports installed"}',
    }
    unverified = client.post(
        f"/api/labs/{lab.id}/submit",
        json=completion_payload,
        headers=auth_headers(student),
    )
    assert unverified.status_code == 409
    assert unverified.json()["detail"] == "Run the simulated verification for this exact plan before submitting"

    correct_verification = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": {"diagnosis": ["detection"]}, "inspected_panel_ids": ["device", "apps"]},
        headers=auth_headers(student),
    )
    assert correct_verification.status_code == 200
    assert correct_verification.json()["data"]["ready"] is True
    assert correct_verification.json()["data"]["verification"]["label"] == "Simulated device state after action"
    assert "not a claim that a real device changed" in correct_verification.json()["data"]["verification"]["description"]
    db.expire_all()
    verified_run = db.query(LabRun).filter_by(lab_template_id=lab.id, student_id=student.id).one()
    assert verified_run.verified_at is not None
    assert '"diagnosis":["detection"]' in verified_run.feedback

    changed_after_verification = client.post(
        f"/api/labs/{lab.id}/submit",
        json=completion_payload | {"answers": {"diagnosis": ["wrong"]}},
        headers=auth_headers(student),
    )
    assert changed_after_verification.status_code == 409

    whitespace_note = client.post(
        f"/api/labs/{lab.id}/submit",
        json=completion_payload | {"notes": '{"issue":"App missing","evidence":"  ","action":"Correct detection rule","verification":"App reports installed"}'},
        headers=auth_headers(student),
    )
    assert whitespace_note.status_code == 400

    missing_note = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"answers": {"diagnosis": ["detection"]}, "notes": "Clicked through."},
        headers=auth_headers(student),
    )
    assert missing_note.status_code == 400
    assert missing_note.json()["detail"] == "Complete all four support-note fields before submitting"

    completed = client.post(
        f"/api/labs/{lab.id}/submit",
        json=completion_payload,
        headers=auth_headers(student),
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["structured_feedback"]["score_pct"] == 100
    assert completed.json()["data"]["notes"] == completion_payload["notes"]


def test_evidence_case_workbench_is_server_verified_and_isolated_per_student(db):
    student = make_student(db, "case-owner")
    other = make_student(db, "case-other")
    lab = LabTemplate(
        title="Server evidence case",
        description="Inspect incident-specific state.",
        lab_type="structured_evidence_case",
        difficulty=3,
        week_number=1,
        is_published=True,
        environment_requirements={},
        success_criteria={
            "evidence_case_workbench": {
                "title": "Windows Server evidence case",
                "guidance_level": "prove",
                "complaint": "The department service stopped overnight.",
                "required_inspections": ["service", "terminal:event"],
                "panels": [
                    {"id": "service", "label": "Service", "fields": [{"label": "State", "value": "Stopped"}]},
                ],
                "terminal_profile": {
                    "id": "service-failure",
                    "commands": [
                        {
                            "command": "Get-WinEvent -MaxEvents 5",
                            "inspection_id": "terminal:event",
                            "output": ["Logon failure after credential rotation"],
                        }
                    ],
                },
                "verification": {
                    "label": "Service state after approved response",
                    "description": "Deterministic training evidence.",
                    "fields": [{"label": "State", "value": "Running"}],
                },
                "documentation_required": True,
                "additional_note_fields": [{"id": "handoff", "label": "Escalation / handoff"}],
            },
            "questions": [
                {
                    "id": "diagnosis",
                    "prompt": "What failed?",
                    "type": "single_choice",
                    "options": [{"id": "credential", "label": "Stored credential"}, {"id": "disk", "label": "Disk"}],
                    "correct": ["credential"],
                    "explanation": "The event correlates with credential rotation.",
                }
            ],
        },
        required_evidence={},
        hints={},
    )
    db.add(lab)
    db.commit()

    fetched = client.get(f"/api/labs/{lab.id}", headers=auth_headers(student))
    assert fetched.status_code == 200
    safe_case = fetched.json()["data"]["success_criteria"]["evidence_case_workbench"]
    assert safe_case["terminal_profile"]["commands"][0]["output"] == ["Logon failure after credential rotation"]
    assert "verification" not in safe_case

    wrong = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": {"diagnosis": ["disk"]}, "inspected_panel_ids": ["service", "terminal:event"]},
        headers=auth_headers(student),
    )
    assert wrong.status_code == 200
    assert wrong.json()["data"]["ready"] is False

    verified = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": {"diagnosis": ["credential"]}, "inspected_panel_ids": ["service", "terminal:event"]},
        headers=auth_headers(student),
    )
    assert verified.status_code == 200
    assert verified.json()["data"]["verification"]["fields"][0]["value"] == "Running"
    db.expire_all()
    run = db.query(LabRun).filter_by(lab_template_id=lab.id, student_id=student.id).one()
    assert '"kind":"evidence_case_workbench_verification"' in run.feedback

    base_notes = {
        "issue": "Department sync stopped.",
        "evidence": "Service event reports a logon failure.",
        "action": "Coordinated the credential update.",
        "verification": "Controlled sync completed.",
    }
    other_lab = LabTemplate(
        title="Different server evidence case",
        description=lab.description,
        lab_type=lab.lab_type,
        difficulty=lab.difficulty,
        week_number=lab.week_number,
        is_published=True,
        environment_requirements={},
        success_criteria=json.loads(json.dumps(lab.success_criteria)),
        required_evidence={},
        hints={},
    )
    db.add(other_lab)
    db.commit()
    cross_lab_submit = client.post(
        f"/api/labs/{other_lab.id}/submit",
        json={
            "answers": {"diagnosis": ["credential"]},
            "notes": json.dumps(base_notes | {"handoff": "Identity Operations owns the update."}),
        },
        headers=auth_headers(student),
    )
    assert cross_lab_submit.status_code == 409

    missing_handoff = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"answers": {"diagnosis": ["credential"]}, "notes": json.dumps(base_notes)},
        headers=auth_headers(student),
    )
    assert missing_handoff.status_code == 400
    assert missing_handoff.json()["detail"] == "Complete every required support-note field before submitting"

    other_submit = client.post(
        f"/api/labs/{lab.id}/submit",
        json={
            "answers": {"diagnosis": ["credential"]},
            "notes": json.dumps(base_notes | {"handoff": "Identity Operations owns the update."}),
        },
        headers=auth_headers(other),
    )
    assert other_submit.status_code == 409

    completed = client.post(
        f"/api/labs/{lab.id}/submit",
        json={
            "answers": {"diagnosis": ["credential"]},
            "notes": json.dumps(base_notes | {"handoff": "Identity Operations owns the update."}),
        },
        headers=auth_headers(student),
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["structured_feedback"]["score_pct"] == 100


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


def test_published_inc2504_poc_cannot_start_before_rollout(monkeypatch, db):
    monkeypatch.delenv("HYBRID_LABS_POC_ENABLED", raising=False)
    student = make_student(db)
    lab = _seed_lab(
        db,
        title="Accidentally published INC2504 POC",
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )

    listed = client.get("/api/labs", headers=auth_headers(student))
    detailed = client.get(f"/api/labs/{lab.id}", headers=auth_headers(student))
    submitted = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"notes": "Attempted direct submission."},
        headers=auth_headers(student),
    )
    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))

    assert all(item["id"] != lab.id for item in listed.json()["data"])
    assert detailed.status_code == 404
    assert submitted.status_code == 404
    assert started.status_code == 404
    assert db.query(LabRun).filter_by(lab_template_id=lab.id).count() == 0
    assert db.query(VmAssignment).count() == 0


def test_start_vm_backed_lab_marks_assignment_failed_without_ip(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)

    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]

    monkeypatch.setattr(
        proxmox_service,
        "clone_template",
        lambda template_vmid, name, **_kwargs: 211,
    )
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(proxmox_service, "get_vm_ip", lambda vmid: None)
    destroyed = []
    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid, **_kwargs: destroyed.append(vmid))
    provision_worker(assignment_id)

    db.expire_all()
    assignment = db.query(VmAssignment).filter(VmAssignment.id == assignment_id).one()
    assert assignment.status == "failed"
    assert assignment.vmid == 211
    assert assignment.provisioning_error == "Lab environment provisioning timed out. Please contact an administrator."
    assert destroyed == [211]


def test_provisioning_worker_persists_each_resource(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=900)
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)
    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]

    monkeypatch.setattr(
        proxmox_service,
        "clone_template",
        lambda template_vmid, name, **_kwargs: 215,
    )
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
    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid, **_kwargs: destroyed.append(vmid))
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

    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid, **_kwargs: destroyed.append(vmid))
    monkeypatch.setattr(guacamole_service, "delete_connection", lambda conn_id: deleted.append(conn_id))

    res = admin_client.delete("/api/admin/vms/cleanup", headers={"X-Admin-Key": "unit-test-admin"})

    assert res.status_code == 200
    assert res.json()["data"]["destroyed"] == [213]
    db.refresh(assignment)
    assert assignment.status == "destroyed"
    assert assignment.destroyed_at is not None
    assert destroyed == [213]
    assert deleted == ["conn-213"]


def test_admin_cleanup_preserves_in_flight_clone_lease(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "unit-test-admin")
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=173)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        vmid=175,
        student_id=student.id,
        lab_run_id=run.id,
        status="provisioning",
        retry_count=1,
        singleton_key="inc2504_printer_stale_ip",
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    db.add(assignment)
    db.commit()
    monkeypatch.setattr(
        proxmox_service,
        "destroy_vm",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("in-flight clone must be reconciled by its worker")
        ),
    )

    response = admin_client.delete(
        "/api/admin/vms/cleanup",
        headers={"X-Admin-Key": "unit-test-admin"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "destroyed": [],
        "errors": [
            {
                "vmid": 175,
                "error": "VM provisioning is still being reconciled",
            }
        ],
    }
    db.refresh(assignment)
    assert assignment.status == "provisioning"
    assert assignment.singleton_key == "inc2504_printer_stale_ip"


def test_admin_cannot_delete_template_with_live_vm_assignment(monkeypatch, db):
    monkeypatch.setenv("ADMIN_API_KEY", "unit-test-admin")
    student = make_student(db)
    lab = _seed_lab(db, proxmox_template_vmid=173)
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        vmid=175,
        student_id=student.id,
        lab_run_id=run.id,
        status="running",
        singleton_key="inc2504_printer_stale_ip",
    )
    db.add(assignment)
    db.commit()
    lab_id = lab.id

    blocked = admin_client.delete(
        f"/api/admin/labs/templates/{lab_id}",
        headers={"X-Admin-Key": "unit-test-admin"},
    )

    assert blocked.status_code == 409
    assert db.get(LabTemplate, lab_id) is not None
    assert db.get(VmAssignment, assignment.id) is not None

    assignment.status = "destroyed"
    assignment.singleton_key = None
    db.commit()
    deleted = admin_client.delete(
        f"/api/admin/labs/templates/{lab_id}",
        headers={"X-Admin-Key": "unit-test-admin"},
    )

    assert deleted.status_code == 200
    db.expire_all()
    assert db.get(LabTemplate, lab_id) is None


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


def test_provisioning_worker_runs_approved_handler_before_connection(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    student = make_student(db)
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {
                "handler": "inc2504_printer_stale_ip",
            }
        },
    )

    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]

    events = []
    monkeypatch.setattr(
        proxmox_service,
        "clone_template",
        lambda template_vmid, name, **_kwargs: events.append(("clone", template_vmid)) or 175,
    )
    monkeypatch.setattr(
        proxmox_service,
        "start_vm",
        lambda vmid: events.append(("start", vmid)),
    )
    monkeypatch.setattr(
        labs_module,
        "_apply_vm_provisioning",
        lambda lab, vmid: events.append(
            (
                "scenario",
                lab.environment_requirements["provisioning"]["handler"],
                vmid,
            )
        ),
        raising=False,
    )
    monkeypatch.setattr(
        proxmox_service,
        "get_vm_ip",
        lambda vmid: events.append(("ip", vmid)) or "10.10.10.10",
    )
    monkeypatch.setattr(
        guacamole_service,
        "create_connection",
        lambda vm_ip, vmid: events.append(("guac", vm_ip, vmid)) or "conn-175",
    )

    provision_worker(assignment_id)

    assert events == [
        ("clone", 173),
        ("start", 175),
        ("scenario", "inc2504_printer_stale_ip", 175),
        ("ip", 175),
        ("guac", "10.10.10.10", 175),
    ]

    db.expire_all()
    assignment = db.query(VmAssignment).filter_by(id=assignment_id).one()
    assert assignment.status == "running"


def test_provisioning_worker_passes_ephemeral_vm_credentials_to_guacamole(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    student = make_student(db)
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            'provisioning': {
                'handler': 'inc2504_printer_stale_ip',
            }
        },
    )

    worker_session = sessionmaker(
        bind=db.get_bind(),
        autocommit=False,
        autoflush=False,
    )
    monkeypatch.setattr(labs_module, 'SessionLocal', worker_session)
    monkeypatch.setattr(labs_module, '_provision_vm_task', lambda assignment_id: None)

    started = client.post(
        f'/api/labs/{lab.id}/start',
        headers=auth_headers(student),
    )
    assignment_id = started.json()['data']['vm_assignment']['assignment_id']

    monkeypatch.setattr(
        proxmox_service,
        'clone_template',
        lambda template_vmid, name, **_kwargs: 175,
    )
    monkeypatch.setattr(proxmox_service, 'start_vm', lambda vmid: None)

    monkeypatch.setattr(
        labs_module,
        '_apply_vm_provisioning',
        lambda lab, vmid: {
            'username': 'labadmin',
            'password': 'ephemeral-secret',
            'ip_address': '10.10.10.10',
        },
    )

    monkeypatch.setattr(
        proxmox_service,
        'get_vm_ip',
        lambda vmid: (_ for _ in ()).throw(
            AssertionError('verified provisioner IP must be used')
        ),
    )

    connection_calls = []

    def create_connection(vm_ip, vmid, *, username=None, password=None):
        connection_calls.append(
            (vm_ip, vmid, username, password)
        )
        return 'conn-175'

    monkeypatch.setattr(
        guacamole_service,
        'create_connection',
        create_connection,
    )

    provision_worker(assignment_id)

    assert connection_calls == [
        ('10.10.10.10', 175, 'labadmin', 'ephemeral-secret')
    ]

    db.expire_all()
    assignment = db.query(VmAssignment).filter_by(id=assignment_id).one()

    assert assignment.status == 'running'
    assert not hasattr(assignment, 'password')
    assert not hasattr(assignment, 'vm_password')
    assert 'ephemeral-secret' not in json.dumps(started.json())


def test_provisioning_failure_destroys_clone_before_marking_failed(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    student = make_student(db)
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]
    monkeypatch.setattr(
        proxmox_service,
        "clone_template",
        lambda template_vmid, name, **_kwargs: 175,
    )
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(
        labs_module,
        "_apply_vm_provisioning",
        lambda lab, vmid: (_ for _ in ()).throw(RuntimeError("verification failed")),
    )
    destroyed = []
    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda vmid, **_kwargs: destroyed.append(vmid))

    provision_worker(assignment_id)

    db.expire_all()
    assignment = db.query(VmAssignment).filter_by(id=assignment_id).one()
    assert assignment.status == "failed"
    assert assignment.singleton_key is None
    assert destroyed == [175]


def test_uncertain_clone_keeps_persisted_vmid_and_singleton_for_retry(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    student = make_student(db)
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]

    def uncertain_clone(_template_vmid, _name, *, on_vmid_selected):
        on_vmid_selected(175)
        raise proxmox_service.CloneRequestError("clone polling failed", vmid=175)

    monkeypatch.setattr(proxmox_service, "clone_template", uncertain_clone)
    destroyed = []
    monkeypatch.setattr(
        proxmox_service,
        "destroy_vm",
        lambda vmid, **_kwargs: destroyed.append(vmid),
    )

    provision_worker(assignment_id)

    db.expire_all()
    assignment = db.get(VmAssignment, assignment_id)
    assert assignment.vmid == 175
    assert assignment.status == "cleanup_failed"
    assert assignment.singleton_key == "inc2504_printer_stale_ip"
    assert destroyed == [175]

    labs_module._destroy_vm_task(assignment_id)
    db.expire_all()
    assignment = db.get(VmAssignment, assignment_id)
    assert assignment.status == "destroyed"
    assert assignment.singleton_key is None
    assert destroyed == [175, 175]


def test_submit_during_clone_keeps_singleton_until_worker_reconciles(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    first_student = make_student(db, username="first")
    second_student = make_student(db, username="second")
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(first_student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]
    run_id = started.json()["data"]["run_id"]
    competing_starts = []

    def clone_while_student_submits(_template_vmid, _name, *, on_vmid_selected):
        on_vmid_selected(175)
        submitted = client.post(
            f"/api/labs/{lab.id}/submit",
            json={"notes": "Submitted while the VM clone was in flight."},
            headers=auth_headers(first_student),
        )
        assert submitted.status_code == 200

        # Submission cleanup may attempt deletion, but cannot release the
        # lease until the claimed worker reconciles the in-flight clone task.
        guarded = worker_session()
        try:
            assignment = guarded.get(VmAssignment, assignment_id)
            assert assignment.status == "destroying"
            assert assignment.singleton_key == "inc2504_printer_stale_ip"
        finally:
            guarded.close()

        competing_starts.append(
            client.post(
                f"/api/labs/{lab.id}/start",
                headers=auth_headers(second_student),
            )
        )
        return 175

    monkeypatch.setattr(proxmox_service, "clone_template", clone_while_student_submits)
    monkeypatch.setattr(
        proxmox_service,
        "start_vm",
        lambda _vmid: (_ for _ in ()).throw(AssertionError("cancelled VM was started")),
    )
    destroyed = []
    monkeypatch.setattr(
        proxmox_service,
        "destroy_vm",
        lambda vmid, **kwargs: destroyed.append((vmid, kwargs["expected_name"])),
    )

    provision_worker(assignment_id)

    assert [response.status_code for response in competing_starts] == [409]
    expected_destroy = (
        175,
        proxmox_service.assignment_vm_name(
            lab_id=lab.id,
            student_id=first_student.id,
            run_id=run_id,
        ),
    )
    # Submission cleanup and the cancelled worker both use protected,
    # idempotent destruction around the external clone race.
    assert destroyed == [expected_destroy, expected_destroy]
    db.expire_all()
    assignment = db.get(VmAssignment, assignment_id)
    assert assignment.status == "destroyed"
    assert assignment.singleton_key is None
    assert assignment.destroyed_at is not None


def test_failed_vm_teardown_keeps_inc2504_singleton_guarded(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    first_student = make_student(db, username="first")
    second_student = make_student(db, username="second")
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    started = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(first_student))
    assignment_id = started.json()["data"]["vm_assignment"]["assignment_id"]
    monkeypatch.setattr(
        proxmox_service,
        "clone_template",
        lambda template_vmid, name, **_kwargs: 175,
    )
    monkeypatch.setattr(proxmox_service, "start_vm", lambda vmid: None)
    monkeypatch.setattr(
        labs_module,
        "_apply_vm_provisioning",
        lambda lab, vmid: (_ for _ in ()).throw(RuntimeError("verification failed")),
    )
    monkeypatch.setattr(
        proxmox_service,
        "destroy_vm",
        lambda vmid, **_kwargs: (_ for _ in ()).throw(RuntimeError("cleanup failed")),
    )

    provision_worker(assignment_id)

    db.expire_all()
    assignment = db.query(VmAssignment).filter_by(id=assignment_id).one()
    assert assignment.status == "cleanup_failed"
    assert assignment.singleton_key == "inc2504_printer_stale_ip"
    second = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(second_student))
    assert second.status_code == 409


def test_inc2504_rejects_second_active_instance(monkeypatch, db):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    first_student = make_student(db, username="first")
    second_student = make_student(db, username="second")
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    first = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(first_student))
    assert first.status_code == 202

    second = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(second_student))

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "This POC lab already has an active instance. End it before starting another."
    )
    assert db.query(VmAssignment).count() == 1


def test_inc2504_singleton_insert_is_atomic_on_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("HYBRID_LABS_POC_ENABLED", "true")
    engine = create_engine(
        f"sqlite:///{tmp_path / 'singleton-race.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    local_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    setup = local_session()
    students = [
        Student(name=f"Student {index}", email=f"race{index}@test.local", username=f"race{index}")
        for index in (1, 2)
    ]
    lab = LabTemplate(
        title="INC2504 race fixture",
        lab_type="guided",
        difficulty=1,
        week_number=1,
        is_published=True,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
        success_criteria={},
        required_evidence={},
        hints={},
        proxmox_template_vmid=173,
    )
    setup.add_all([*students, lab])
    setup.flush()
    runs = [
        LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
        for student in students
    ]
    setup.add_all(runs)
    setup.commit()
    run_ids = [run.id for run in runs]
    setup.close()

    barrier = threading.Barrier(2)
    original_lookup = labs_module._assignment_for_run
    lookup_lock = threading.Lock()
    initial_lookups = 0

    def synchronized_initial_lookup(session, run_id):
        nonlocal initial_lookups
        result = original_lookup(session, run_id)
        with lookup_lock:
            should_wait = initial_lookups < 2
            initial_lookups += 1
        if should_wait:
            barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(labs_module, "_assignment_for_run", synchronized_initial_lookup)
    outcomes = []

    def queue(run_id):
        session = local_session()
        try:
            run = session.get(LabRun, run_id)
            assignment = labs_module._queue_assignment(session, run, BackgroundTasks())
            outcomes.append(("created", assignment.id))
        except HTTPException as exc:
            outcomes.append(("rejected", exc.status_code))
        except Exception as exc:  # pragma: no cover - surfaced by the assertion below
            outcomes.append(("error", repr(exc)))
        finally:
            session.close()

    threads = [threading.Thread(target=queue, args=(run_id,)) for run_id in run_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    verify = local_session()
    try:
        assert not any(thread.is_alive() for thread in threads)
        assert sorted(outcomes) == [("created", 1), ("rejected", 409)]
        [assignment] = verify.query(VmAssignment).all()
        assert assignment.singleton_key == "inc2504_printer_stale_ip"
    finally:
        verify.close()
        engine.dispose()


def test_cleanup_retry_marks_assignment_destroyed_when_vm_is_already_absent(monkeypatch, db):
    student = make_student(db)
    lab = _seed_lab(
        db,
        proxmox_template_vmid=173,
        environment_requirements={
            "provisioning": {"handler": "inc2504_printer_stale_ip"}
        },
    )
    run = LabRun(lab_template_id=lab.id, student_id=student.id, status="in_progress")
    db.add(run)
    db.flush()
    assignment = VmAssignment(
        vmid=175,
        student_id=student.id,
        lab_run_id=run.id,
        status="cleanup_failed",
        singleton_key="inc2504_printer_stale_ip",
    )
    db.add(assignment)
    db.commit()
    worker_session = sessionmaker(bind=db.get_bind(), autocommit=False, autoflush=False)
    monkeypatch.setattr(labs_module, "SessionLocal", worker_session)
    monkeypatch.setattr(proxmox_service, "destroy_vm", lambda _vmid, **_kwargs: None)

    labs_module._destroy_vm_task(assignment.id)

    db.expire_all()
    cleaned = db.get(VmAssignment, assignment.id)
    assert cleaned.status == "destroyed"
    assert cleaned.destroyed_at is not None
    assert cleaned.singleton_key is None


def test_non_inc2504_vm_labs_are_not_singleton(monkeypatch, db):
    first_student = make_student(db, username="first")
    second_student = make_student(db, username="second")
    lab = _seed_lab(db, proxmox_template_vmid=900)
    monkeypatch.setattr(labs_module, "_provision_vm_task", lambda assignment_id: None)

    first = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(first_student))
    second = client.post(f"/api/labs/{lab.id}/start", headers=auth_headers(second_student))

    assert first.status_code == 202
    assert second.status_code == 202
    assert db.query(VmAssignment).count() == 2
