from datetime import UTC, datetime
import logging
import os
from pathlib import Path
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models.evidence import EvidenceArtifact
from app.models.lab import LabRun, LabTemplate
from app.models.student import Student
from app.models.vm_assignment import VmAssignment
from app.schemas.lab import LabSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import get_current_student
from app.utils.responses import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/labs", tags=["labs"])
ALLOWED_EVIDENCE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _normalize_hints(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        items = value.get("items") or value.get("hints")
        return items if isinstance(items, list) else []
    return []


def _serialize_lab(template: LabTemplate, run: LabRun | None = None) -> dict:
    status = "not_started"
    if run is not None:
        if run.status == "submitted":
            status = "submitted"
        elif run.status in {"assigned", "not_started"}:
            status = run.status
        else:
            status = "in_progress"

    return {
        "id": template.id,
        "lesson_id": template.lesson_id,
        "title": template.title,
        "description": template.description,
        "lab_type": template.lab_type,
        "difficulty": template.difficulty,
        "week_number": template.week_number,
        "estimated_minutes": template.estimated_minutes,
        "setup_instructions": template.setup_instructions,
        "success_criteria": template.success_criteria or {},
        "required_evidence": template.required_evidence or {},
        "hints": _normalize_hints(template.hints),
        "status": status,
        "run_id": run.id if run else None,
        "notes": run.notes if run else "",
        "started_at": run.started_at if run else None,
        "submitted_at": run.submitted_at if run else None,
    }


def _screenshots_dir() -> Path:
    configured = os.getenv("UPLOAD_DIR")
    path = (Path(configured) / "screenshots") if configured else Path(__file__).resolve().parents[2] / "uploads" / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _serialize_artifact(artifact: EvidenceArtifact) -> dict:
    return {
        "id": artifact.id,
        "artifact_id": artifact.id,
        "artifact_type": artifact.artifact_type,
        "storage_key": artifact.storage_key,
        "original_filename": artifact.original_filename,
        "uploaded_at": artifact.uploaded_at,
    }


def _get_published_lab(db: Session, lab_id: int) -> LabTemplate:
    lab = db.query(LabTemplate).filter(LabTemplate.id == lab_id, LabTemplate.is_published.is_(True)).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab


def _get_lab_run(db: Session, lab_id: int, student_id: int) -> LabRun | None:
    return (
        db.query(LabRun)
        .filter(LabRun.lab_template_id == lab_id, LabRun.student_id == student_id)
        .order_by(LabRun.created_at.desc(), LabRun.id.desc())
        .first()
    )


def _do_provision(db: Session, run: LabRun, lab_id: int, template_vmid: int) -> str:
    from app.services import proxmox_service, guacamole_service

    existing = db.query(VmAssignment).filter(
        VmAssignment.lab_run_id == run.id,
        VmAssignment.status != "destroyed",
    ).first()
    if existing:
        if existing.status == "failed":
            raise RuntimeError("Lab VM provisioning previously failed. Ask an admin to clean up this VM assignment.")
        if existing.guac_conn_id:
            return guacamole_service.get_student_token_url(existing.guac_conn_id, run.id)
        if existing.ip_address:
            conn_id = guacamole_service.create_connection(existing.ip_address, existing.vmid)
            existing.guac_conn_id = conn_id
            existing.status = "running"
            db.commit()
            return guacamole_service.get_student_token_url(conn_id, run.id)
        raise RuntimeError("Lab VM exists but no remote session is available yet.")

    assignment = None
    try:
        name = f"lab-{lab_id}-student-{run.student_id}-run-{run.id}"
        vmid = proxmox_service.clone_template(template_vmid, name)
        assignment = VmAssignment(
            vmid=vmid,
            student_id=run.student_id,
            lab_run_id=run.id,
            status="provisioning",
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        proxmox_service.start_vm(vmid)
        ip = proxmox_service.get_vm_ip(vmid)
        if not ip:
            assignment.status = "failed"
            db.commit()
            raise RuntimeError("Lab VM started but did not report an IP address.")

        conn_id = guacamole_service.create_connection(ip, vmid)
        if not conn_id:
            assignment.status = "failed"
            assignment.ip_address = ip
            db.commit()
            raise RuntimeError("Lab VM remote connection could not be created.")

        assignment.status = "running"
        assignment.ip_address = ip
        assignment.guac_conn_id = conn_id
        db.commit()
        return guacamole_service.get_student_token_url(conn_id, run.id)
    except RuntimeError:
        raise
    except Exception as exc:
        if assignment is not None:
            assignment.status = "failed"
            db.commit()
        raise RuntimeError("Lab VM provisioning failed.") from exc


def _provision_vm_task(lab_run_id: int, lab_id: int, template_vmid: int) -> None:
    """Runs in a FastAPI BackgroundTask with its own DB session — the request
    that scheduled it has already returned 202."""
    db = SessionLocal()
    try:
        run = db.query(LabRun).filter(LabRun.id == lab_run_id).first()
        if run is None:
            return
        try:
            guac_url = _do_provision(db, run, lab_id, template_vmid)
            run.vm_status = "ready"
            run.guac_url = guac_url
        except Exception as exc:
            logger.error("VM provisioning failed for lab_run %s: %s", lab_run_id, exc)
            run.vm_status = "failed"
            run.guac_url = None
        db.commit()
    finally:
        db.close()


def _destroy_vm_if_assigned(db: Session, lab_run_id: int) -> None:
    assignment = db.query(VmAssignment).filter(
        VmAssignment.lab_run_id == lab_run_id,
        VmAssignment.status != "destroyed",
    ).first()
    if not assignment:
        return

    try:
        from app.services import proxmox_service
        proxmox_service.destroy_vm(assignment.vmid)
    except Exception as exc:
        logger.warning("Failed to destroy VM %s: %s", assignment.vmid, exc)
        assignment.status = "failed"
        db.commit()
        return

    if assignment.guac_conn_id:
        from app.services import guacamole_service
        try:
            guacamole_service.delete_connection(assignment.guac_conn_id)
        except Exception as exc:
            logger.warning("Failed to delete Guacamole connection %s: %s", assignment.guac_conn_id, exc)
        try:
            guacamole_service.delete_lab_user(lab_run_id)
        except Exception as exc:
            logger.warning("Failed to delete Guacamole lab user for run %s: %s", lab_run_id, exc)

    assignment.status = "destroyed"
    assignment.destroyed_at = datetime.now(UTC)
    run = db.query(LabRun).filter(LabRun.id == lab_run_id).first()
    if run is not None:
        run.vm_status = None
        run.guac_url = None
    db.commit()


@router.get("")
def get_labs(
    week_number: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    query = db.query(LabTemplate).filter(LabTemplate.is_published.is_(True))
    if week_number is not None:
        query = query.filter(LabTemplate.week_number == week_number)
    labs = query.order_by(LabTemplate.week_number.asc(), LabTemplate.created_at.desc()).all()

    lab_ids = [lab.id for lab in labs]
    runs = {}
    if lab_ids:
        rows = (
            db.query(LabRun)
            .filter(LabRun.student_id == current_student.id, LabRun.lab_template_id.in_(lab_ids))
            .order_by(LabRun.created_at.desc(), LabRun.id.desc())
            .all()
        )
        for row in rows:
            runs.setdefault(row.lab_template_id, row)

    data = [_serialize_lab(lab, runs.get(lab.id)) for lab in labs]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{lab_id}")
def get_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_published_lab(db, lab_id)
    run = _get_lab_run(db, lab_id, current_student.id)
    data = _serialize_lab(lab, run)
    if run:
        artifacts = (
            db.query(EvidenceArtifact)
            .filter(EvidenceArtifact.submission_type == "lab", EvidenceArtifact.submission_id == run.id)
            .order_by(EvidenceArtifact.uploaded_at.desc(), EvidenceArtifact.id.desc())
            .all()
        )
        data["evidence_artifacts"] = [_serialize_artifact(artifact) for artifact in artifacts]
    else:
        data["evidence_artifacts"] = []
    return ok(data)


@router.post("/{lab_id}/start")
def start_lab(
    lab_id: int,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_published_lab(db, lab_id)
    run = _get_lab_run(db, lab_id, current_student.id)
    created = False

    if run is None:
        run = LabRun(
            lab_template_id=lab.id,
            student_id=current_student.id,
            status="in_progress",
            started_at=datetime.now(UTC),
        )
        db.add(run)
        created = True
    else:
        if run.started_at is None:
            run.started_at = datetime.now(UTC)
        if run.status in {"assigned", "not_started"}:
            run.status = "in_progress"

    db.commit()
    db.refresh(run)
    mark_student_active(db, current_student.id)
    if created:
        log_activity(db, current_student.id, "lab_started", lab.title, "Lab in progress")

    vm_data = {}
    if lab.proxmox_template_vmid:
        if run.vm_status == "ready" and run.guac_url:
            vm_data = {"vm_status": "ready", "guac_token_url": run.guac_url}
        elif run.vm_status == "provisioning":
            response.status_code = 202
            vm_data = {"vm_status": "provisioning"}
        else:
            run.vm_status = "provisioning"
            run.guac_url = None
            db.commit()
            background_tasks.add_task(_provision_vm_task, run.id, lab.id, lab.proxmox_template_vmid)
            response.status_code = 202
            vm_data = {"vm_status": "provisioning"}

    return ok({"created": created, **vm_data, **_serialize_lab(lab, run)})


@router.get("/{lab_id}/vm-status")
def get_vm_status(
    lab_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    run = _get_lab_run(db, lab_id, current_student.id)
    if run is None:
        raise HTTPException(status_code=404, detail="Lab run not found")
    return ok({
        "run_id": run.id,
        "vm_status": run.vm_status,
        "guac_token_url": run.guac_url if run.vm_status == "ready" else None,
    })


@router.post("/{lab_id}/submit")
def submit_lab(
    lab_id: int,
    payload: LabSubmitRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_published_lab(db, lab_id)
    run = _get_lab_run(db, lab_id, current_student.id)
    now = datetime.now(UTC)

    if run is None:
        run = LabRun(
            lab_template_id=lab.id,
            student_id=current_student.id,
            status="in_progress",
            started_at=now,
        )
        db.add(run)
        db.flush()

    if run.started_at is None:
        run.started_at = now

    run.status = "submitted"
    run.submitted_at = now
    run.notes = payload.notes.strip()
    if run.final_score is None:
        run.final_score = 10

    db.commit()
    db.refresh(run)
    _destroy_vm_if_assigned(db, run.id)
    mark_student_active(db, current_student.id)
    log_activity(db, current_student.id, "lab_submitted", lab.title, "Lab submitted")
    return ok(_serialize_lab(lab, run))


@router.post("/{lab_run_id}/evidence")
async def upload_lab_evidence(
    lab_run_id: int,
    file: UploadFile = File(...),
    artifact_type: str = Form("screenshot"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    run = db.query(LabRun).filter(LabRun.id == lab_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Lab run not found")
    if run.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Not allowed to upload evidence for this lab run")

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")

    storage_name = f"{uuid.uuid4()}.{ext}"
    dest = (_screenshots_dir() / storage_name).resolve()
    data = await file.read()
    with open(dest, "wb") as handle:
        handle.write(data)

    artifact = EvidenceArtifact(
        submission_type="lab",
        submission_id=run.id,
        artifact_type=artifact_type or "screenshot",
        storage_key=storage_name,
        original_filename=file.filename,
        file_size_bytes=len(data),
        mime_type=file.content_type,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)

    return ok({"artifact_id": artifact.id, "storage_key": artifact.storage_key})
