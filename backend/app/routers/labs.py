import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models.evidence import EvidenceArtifact
from app.models.lab import LabRun, LabTemplate
from app.models.certification import ModuleAssessment, CertificationModule
from app.models.student import Student
from app.models.v2_progress import V2ModuleActivity
from app.models.vm_assignment import VmAssignment
from app.schemas.lab import LabSubmitRequest, LabVerifyRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import get_current_student
from app.services.progression_service import require_week_reached
from app.services.v2_progress_service import record_activity
from app.services.v2_access import V2_UNAVAILABLE_DETAIL, student_has_v2_access
from app.utils.responses import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/labs", tags=["labs"])
ALLOWED_EVIDENCE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_EVIDENCE_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_EVIDENCE_UPLOAD_BYTES = int(os.getenv("MAX_EVIDENCE_UPLOAD_BYTES", str(10 * 1024 * 1024)))
UPLOAD_CHUNK_BYTES = 1024 * 1024
ACTIVE_VM_STATUSES = {
    "provisioning",
    "starting",
    "waiting_for_ip",
    "configuring_connection",
    "running",
    "destroying",
}


def _normalize_hints(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        items = value.get("items") or value.get("hints")
        return items if isinstance(items, list) else []
    return []


_QUESTION_ANSWER_KEY_FIELDS = ("correct", "explanation")
_WORKBENCH_KEYS = ("evidence_case_workbench", "endpoint_workbench")


def _student_safe_questions(questions: list) -> list:
    """Strip answer-key fields (`correct`, `explanation`) before a lab's
    question set reaches a student. Grading always reads the unfiltered
    ORM `success_criteria` directly (see submit_lab), never this DTO."""
    return [
        {key: value for key, value in question.items() if key not in _QUESTION_ANSWER_KEY_FIELDS}
        for question in questions
    ]


def _student_safe_success_criteria(success_criteria: dict) -> dict:
    safe = dict(success_criteria)
    if "questions" in safe:
        safe["questions"] = _student_safe_questions(safe["questions"])
    for workbench_key in _WORKBENCH_KEYS:
        workbench = safe.get(workbench_key)
        if isinstance(workbench, dict):
            # The simulated after-state is outcome evidence. Do not preload it
            # before the server accepts the student's exact plan.
            safe[workbench_key] = {
                key: value for key, value in workbench.items() if key != "verification"
            }
    if "final_shift" in safe:
        # The Final Support Shift's queue/incident content, including its
        # answer key, is served exclusively by /api/final-shift/{lab_id}
        # (see app/routers/final_shift.py), which strips diagnosis.correct,
        # actions[].safe, and verification before responding. This generic
        # lab endpoint must never forward the raw case data.
        safe = {key: value for key, value in safe.items() if key != "final_shift"}
    return safe


def _configured_workbench(success_criteria: dict) -> tuple[str | None, dict]:
    for key in _WORKBENCH_KEYS:
        workbench = success_criteria.get(key)
        if isinstance(workbench, dict) and workbench:
            return key, workbench
    return None, {}


def _normalized_workbench_answers(questions: list, answers: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        question["id"]: sorted(set(answers.get(question["id"], [])))
        for question in questions
    }


def _workbench_verification_record(
    workbench_key: str,
    questions: list,
    answers: dict[str, list[str]],
    inspected_panel_ids: list[str],
) -> str:
    return json.dumps(
        {
            "kind": f"{workbench_key}_verification",
            "answers": _normalized_workbench_answers(questions, answers),
            "inspected_panel_ids": sorted(set(inspected_panel_ids)),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _serialize_lab(template: LabTemplate, run: LabRun | None = None) -> dict:
    status = "not_started"
    if run is not None:
        if run.status == "submitted":
            status = "submitted"
        elif run.status in {"assigned", "not_started"}:
            status = run.status
        else:
            status = "in_progress"

    raw_success_criteria = template.success_criteria or {}
    data = {
        "id": template.id,
        "lesson_id": template.lesson_id,
        "title": template.title,
        "description": template.description,
        "lab_type": template.lab_type,
        "difficulty": template.difficulty,
        "week_number": template.week_number,
        "estimated_minutes": template.estimated_minutes,
        "setup_instructions": template.setup_instructions,
        "success_criteria": _student_safe_success_criteria(raw_success_criteria),
        "questions": _student_safe_questions(raw_success_criteria.get("questions", [])),
        "required_evidence": template.required_evidence or {},
        "hints": _normalize_hints(template.hints),
        "status": status,
        "run_id": run.id if run else None,
        "notes": run.notes if run else "",
        "started_at": run.started_at if run else None,
        "submitted_at": run.submitted_at if run else None,
    }
    if run is not None and run.structured_feedback is not None:
        data["structured_feedback"] = run.structured_feedback
    return data


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _serialize_vm(assignment: VmAssignment | None) -> dict | None:
    if assignment is None:
        return None
    return {
        "assignment_id": assignment.id,
        "vmid": assignment.vmid,
        "status": assignment.status,
        "ip_address": assignment.ip_address,
        "provisioning_error": assignment.provisioning_error,
        "started_at": assignment.started_at,
        "expires_at": assignment.expires_at,
    }


def _assignment_for_run(db: Session, run_id: int) -> VmAssignment | None:
    return db.query(VmAssignment).filter(VmAssignment.lab_run_id == run_id).first()


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


def _v2_run_activity(db: Session, student: Student, run: LabRun):
    """Return trusted V2 provenance for a run, independent of current access."""
    rows = db.query(V2ModuleActivity).filter(
        V2ModuleActivity.student_id == student.id,
        V2ModuleActivity.activity_type == "practical",
    ).all()
    return next(
        (row for row in rows if (row.detail or {}).get("lab_run_id") == run.id),
        None,
    )


def _v2_run_context(db: Session, student: Student, run: LabRun):
    """Was this lab run actually launched from a V2 practical by this student?

    ``start_lab`` records the launch as a V2 practical activity carrying the
    ``lab_run_id``. That record is the validated V2 launch context for
    follow-up calls (``/verify``, ``/evidence``) that carry no query
    parameters of their own — it cannot be forged from the request, and it
    ties the bypass to a launch this same student really made.
    """
    activity = _v2_run_activity(db, student, run)
    if activity is None:
        return None
    if not student_has_v2_access(student):
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)
    module = db.query(CertificationModule).filter_by(
        module_key=activity.module_key, active=True
    ).one_or_none()
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id if module else None,
        assessment_key=activity.ref_key,
        assessment_role="practical",
        lab_template_id=run.lab_template_id,
        active=True,
    ).one_or_none()
    if module is None or assessment is None:
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)
    return activity


def _authorize_existing_run(db: Session, student: Student, run: LabRun, lab: LabTemplate):
    """Authorize a trusted V2 run or apply the ordinary legacy week gate."""
    if _v2_run_context(db, student, run) is None:
        require_week_reached(db, student, lab.week_number)


def _v2_lab_assessment(
    db: Session,
    lab_id: int,
    module_key: str | None,
    assessment_key: str | None,
    student: Student | None = None,
):
    """Resolve and validate a V2 practical launch context.

    Returning a context is what lets the caller bypass the legacy week gate,
    so this is a real authorization boundary: the master switch must be on,
    the caller must be enrolled in the V2 pilot, and the named assessment must
    actually be an active ``practical`` bound to this exact lab template.
    """
    if not module_key and not assessment_key:
        return None
    if not student_has_v2_access(student):
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)
    if not module_key or not assessment_key:
        raise HTTPException(status_code=422, detail="The V2 lab context is incomplete.")
    row = db.query(ModuleAssessment, CertificationModule).join(
        CertificationModule, CertificationModule.id == ModuleAssessment.certification_module_id
    ).filter(
        CertificationModule.module_key == module_key,
        CertificationModule.active.is_(True),
        ModuleAssessment.assessment_key == assessment_key,
        ModuleAssessment.assessment_role == "practical",
        ModuleAssessment.lab_template_id == lab_id,
        ModuleAssessment.active.is_(True),
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="This practical is not available.")
    return row


def _lab_is_v2_bound(db: Session, lab_id: int) -> bool:
    return db.query(ModuleAssessment.id).join(
        CertificationModule,
        CertificationModule.id == ModuleAssessment.certification_module_id,
    ).filter(
        ModuleAssessment.lab_template_id == lab_id,
        ModuleAssessment.assessment_role == "practical",
        ModuleAssessment.active.is_(True),
        CertificationModule.active.is_(True),
    ).first() is not None


def _lab_access_context(
    db: Session,
    lab_id: int,
    module_key: str | None,
    assessment_key: str | None,
    student: Student,
):
    context = _v2_lab_assessment(
        db, lab_id, module_key, assessment_key, student
    )
    if context is None and _lab_is_v2_bound(db, lab_id):
        # V2 practicals are never legacy week-zero labs. Requiring the exact
        # module/assessment relationship closes direct URL and stale-client
        # bypasses while leaving genuinely legacy labs unchanged.
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)
    return context


def _safe_provisioning_error(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "Lab environment provisioning timed out. Please contact an administrator."
    return "Lab environment provisioning failed. Please contact an administrator."


def _provision_vm_task(assignment_id: int) -> None:
    """Provision a VM using a worker-owned database session."""
    db = SessionLocal()
    try:
        assignment = (
            db.query(VmAssignment)
            .filter(VmAssignment.id == assignment_id)
            .with_for_update()
            .first()
        )
        if not assignment or assignment.status != "provisioning" or assignment.retry_count > 0:
            return
        assignment.retry_count += 1
        db.commit()
        run = db.query(LabRun).filter(LabRun.id == assignment.lab_run_id).first()
        lab = db.query(LabTemplate).filter(LabTemplate.id == run.lab_template_id).first() if run else None
        if not run or not lab or not lab.proxmox_template_vmid:
            raise RuntimeError("VM assignment is missing its lab template")

        from app.services import guacamole_service, proxmox_service

        name = f"lab-{lab.id}-student-{run.student_id}-run-{run.id}"
        vmid = proxmox_service.clone_template(lab.proxmox_template_vmid, name)
        assignment.vmid = vmid
        assignment.status = "starting"
        db.commit()

        proxmox_service.start_vm(vmid)
        assignment.status = "waiting_for_ip"
        db.commit()

        ip = proxmox_service.get_vm_ip(vmid)
        if not ip:
            raise TimeoutError("VM did not report an IP address")
        assignment.ip_address = ip
        assignment.status = "configuring_connection"
        db.commit()

        conn_id = guacamole_service.create_connection(ip, vmid)
        now = datetime.now(UTC)
        assignment.guac_conn_id = conn_id
        assignment.status = "running"
        assignment.started_at = now
        assignment.expires_at = now + timedelta(minutes=max(1, int(os.getenv("LAB_VM_TTL_MINUTES", "120"))))
        assignment.provisioning_error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        assignment = db.query(VmAssignment).filter(VmAssignment.id == assignment_id).first()
        if assignment and assignment.status != "destroyed":
            assignment.status = "failed"
            assignment.provisioning_error = _safe_provisioning_error(exc)
            db.commit()
        logger.exception("VM provisioning failed for assignment %s", assignment_id)
    finally:
        db.close()


def _destroy_vm_task(assignment_id: int) -> None:
    db = SessionLocal()
    try:
        assignment = db.query(VmAssignment).filter(VmAssignment.id == assignment_id).first()
        if not assignment or assignment.status == "destroyed":
            return
        from app.services import guacamole_service, proxmox_service

        cleanup_errors = []
        if assignment.guac_username:
            try:
                guacamole_service.delete_user(assignment.guac_username)
            except Exception as exc:
                cleanup_errors.append(exc)
        if assignment.guac_conn_id:
            try:
                guacamole_service.delete_connection(assignment.guac_conn_id)
            except Exception as exc:
                cleanup_errors.append(exc)
        if assignment.vmid is not None:
            try:
                proxmox_service.destroy_vm(assignment.vmid)
            except Exception as exc:
                cleanup_errors.append(exc)

        if cleanup_errors:
            assignment.status = "failed"
            assignment.provisioning_error = "Lab environment cleanup failed. Please contact an administrator."
            db.commit()
            logger.warning("VM cleanup failed for assignment %s", assignment_id)
            return
        assignment.status = "destroyed"
        assignment.guac_username = None
        assignment.destroyed_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


def _queue_assignment(db: Session, run: LabRun, background_tasks: BackgroundTasks) -> VmAssignment:
    # Locks the run on databases which support row locks. The unique constraint
    # on lab_run_id is the final duplicate-start guard.
    db.query(LabRun).filter(LabRun.id == run.id).with_for_update().first()
    existing = _assignment_for_run(db, run.id)
    if existing:
        if existing.status in ACTIVE_VM_STATUSES:
            return existing
        if existing.status == "failed":
            raise HTTPException(status_code=409, detail="Lab VM provisioning failed. Ask an administrator to retry it.")
        raise HTTPException(status_code=409, detail="This lab environment has ended and cannot be restarted.")

    assignment = VmAssignment(
        student_id=run.student_id,
        lab_run_id=run.id,
        status="provisioning",
        provisioning_started_at=datetime.now(UTC),
    )
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _assignment_for_run(db, run.id)
        if existing:
            return existing
        raise
    db.refresh(assignment)
    background_tasks.add_task(_provision_vm_task, assignment.id)
    return assignment


@router.get("")
def get_labs(
    week_number: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    query = db.query(LabTemplate).filter(LabTemplate.is_published.is_(True))
    if week_number is not None:
        query = query.filter(LabTemplate.week_number == week_number)
    v2_lab_ids = db.query(ModuleAssessment.lab_template_id).filter(
        ModuleAssessment.assessment_role == "practical",
        ModuleAssessment.active.is_(True),
        ModuleAssessment.lab_template_id.is_not(None),
    )
    query = query.filter(LabTemplate.id.not_in(v2_lab_ids))
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
    v2_module_key: str | None = None,
    v2_assessment_key: str | None = None,
):
    lab = _get_published_lab(db, lab_id)
    v2_context = _lab_access_context(
        db, lab_id, v2_module_key, v2_assessment_key, current_student
    )
    if v2_context is None:
        require_week_reached(db, current_student, lab.week_number)
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
        data["vm_assignment"] = _serialize_vm(_assignment_for_run(db, run.id))
    else:
        data["evidence_artifacts"] = []
        data["vm_assignment"] = None
    return ok(data)


@router.post("/{lab_id}/start")
def start_lab(
    lab_id: int,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
    v2_module_key: str | None = None,
    v2_assessment_key: str | None = None,
):
    lab = _get_published_lab(db, lab_id)
    v2_context = _lab_access_context(
        db, lab_id, v2_module_key, v2_assessment_key, current_student
    )
    if v2_context is None:
        require_week_reached(db, current_student, lab.week_number)
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
    if v2_context:
        assessment, module = v2_context
        record_activity(
            db, student_id=current_student.id, module_key=module.module_key,
            activity_type="practical", ref_key=assessment.assessment_key,
            status="in_progress", detail={"lab_run_id": run.id}, commit=True,
        )

    vm_data = {}
    if lab.proxmox_template_vmid:
        assignment = _queue_assignment(db, run, background_tasks)
        response.status_code = 202
        vm_data = {"vm_assignment": _serialize_vm(assignment)}

    return ok({"created": created, **vm_data, **_serialize_lab(lab, run)})


@router.get("/{lab_id}/vm-status")
def get_vm_status(
    lab_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_published_lab(db, lab_id)
    run = _get_lab_run(db, lab_id, current_student.id)
    if not run:
        raise HTTPException(status_code=404, detail="Lab run not found")
    _authorize_existing_run(db, current_student, run, lab)
    assignment = _assignment_for_run(db, run.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Lab environment not found")
    expires_at = _as_utc(assignment.expires_at)
    if assignment.status == "running" and expires_at and expires_at <= datetime.now(UTC):
        assignment.status = "destroying"
        db.commit()
        background_tasks.add_task(_destroy_vm_task, assignment.id)
    return ok(_serialize_vm(assignment))


@router.post("/{lab_id}/vm-access")
def create_vm_access(
    lab_id: int,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_published_lab(db, lab_id)
    run = _get_lab_run(db, lab_id, current_student.id)
    if not run:
        raise HTTPException(status_code=404, detail="Lab run not found")
    _authorize_existing_run(db, current_student, run, lab)
    assignment = _assignment_for_run(db, run.id)
    expires_at = _as_utc(assignment.expires_at) if assignment else None
    if not assignment or assignment.status != "running" or not assignment.guac_conn_id:
        raise HTTPException(status_code=409, detail="Lab environment is not ready")
    if expires_at and expires_at <= datetime.now(UTC):
        assignment.status = "destroying"
        db.commit()
        background_tasks.add_task(_destroy_vm_task, assignment.id)
        response.status_code = 410
        return ok({"status": "destroying", "message": "Lab environment has expired"})

    try:
        from app.services import guacamole_service

        access = guacamole_service.create_scoped_access(
            assignment.guac_conn_id,
            assignment.id,
            assignment.guac_username,
        )
    except Exception as exc:
        logger.exception("Could not create scoped remote access for assignment %s", assignment.id)
        raise HTTPException(status_code=502, detail="Remote lab access is temporarily unavailable") from exc
    assignment.guac_username = access["username"]
    db.commit()
    return ok({"url": access["url"], "expires_at": assignment.expires_at})


@router.post("/{lab_id}/verify")
def verify_evidence_workbench(
    lab_id: int,
    payload: LabVerifyRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
    v2_module_key: str | None = None,
    v2_assessment_key: str | None = None,
):
    """Check an evidence-case plan without exposing its answer key.

    This intentionally does not create a second grading or persistence path:
    final scoring still happens only in submit_lab. It gates simulated
    after-state evidence so an incorrect action cannot appear successful.
    """
    lab = _get_published_lab(db, lab_id)
    if _lab_access_context(
        db, lab_id, v2_module_key, v2_assessment_key, current_student
    ) is None:
        require_week_reached(db, current_student, lab.week_number)
    criteria = lab.success_criteria or {}
    workbench_key, workbench = _configured_workbench(criteria)
    questions = criteria.get("questions", [])
    if not workbench_key or not workbench or not questions:
        raise HTTPException(status_code=400, detail="Lab has no evidence workbench")
    required_inspections = set(workbench.get("required_inspections", []))
    inspections_complete = required_inspections.issubset(set(payload.inspected_panel_ids))
    ready = inspections_complete and all(
        set(payload.answers.get(question["id"], [])) == set(question["correct"])
        for question in questions
    )
    if not ready:
        return ok(
            {
                "ready": False,
                "message": "The selected path did not produce the expected state. Re-open the evidence and revise the unsupported decision.",
            }
        )
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
    elif run.started_at is None:
        run.started_at = now
    if run.status in {"assigned", "not_started"}:
        run.status = "in_progress"
    run.verified_at = now
    run.feedback = _workbench_verification_record(
        workbench_key,
        questions,
        payload.answers,
        payload.inspected_panel_ids,
    )
    db.commit()
    return ok({"ready": True, "verification": workbench.get("verification", {})})


@router.post("/{lab_id}/submit")
def submit_lab(
    lab_id: int,
    payload: LabSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
    v2_module_key: str | None = None,
    v2_assessment_key: str | None = None,
):
    lab = _get_published_lab(db, lab_id)
    v2_context = _lab_access_context(
        db, lab_id, v2_module_key, v2_assessment_key, current_student
    )
    if v2_context is None:
        require_week_reached(db, current_student, lab.week_number)
    is_structured_lab = (lab.lab_type or "").startswith("structured_")
    if v2_context and not is_structured_lab and not payload.notes.strip():
        raise HTTPException(
            status_code=400,
            detail="Describe the evidence you collected before submitting this practical",
        )
    questions = []
    if is_structured_lab:
        if not payload.answers:
            raise HTTPException(status_code=400, detail="Structured lab submissions require answers")
        questions = (lab.success_criteria or {}).get("questions", [])
        if not questions:
            raise HTTPException(status_code=400, detail="Structured lab has no configured questions")
        required_commands = (lab.success_criteria or {}).get("required_commands", [])
        if required_commands:
            terminal_session = " ".join(payload.notes.lower().split())
            if any(" ".join(command.lower().split()) not in terminal_session for command in required_commands):
                raise HTTPException(
                    status_code=400,
                    detail="Run every required command in the practice terminal before submitting",
                )
        workbench_key, workbench = _configured_workbench(lab.success_criteria or {})
        if workbench_key:
            run = _get_lab_run(db, lab_id, current_student.id)
            try:
                verification_record = json.loads(run.feedback) if run and run.feedback else {}
            except (json.JSONDecodeError, TypeError):
                verification_record = {}
            expected_answers = _normalized_workbench_answers(questions, payload.answers)
            if (
                not run
                or run.verified_at is None
                or verification_record.get("kind") != f"{workbench_key}_verification"
                or verification_record.get("answers") != expected_answers
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Run the simulated verification for this exact plan before submitting",
                )
        if workbench.get("documentation_required"):
            try:
                support_note = json.loads(payload.notes)
            except (json.JSONDecodeError, TypeError):
                support_note = {}
            additional_fields = workbench.get("additional_note_fields", [])
            required_note_fields = (
                "issue",
                "evidence",
                "action",
                "verification",
                *(field.get("id") for field in additional_fields if isinstance(field, dict) and field.get("id")),
            )
            if not isinstance(support_note, dict) or any(
                not str(support_note.get(field, "")).strip() for field in required_note_fields
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Complete all four support-note fields before submitting"
                        if not additional_fields
                        else "Complete every required support-note field before submitting"
                    ),
                )
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
    if is_structured_lab:
        feedback_questions = []
        correct_count = 0
        for question in questions:
            is_correct = set(payload.answers.get(question["id"], [])) == set(question["correct"])
            correct_count += int(is_correct)
            feedback_questions.append(
                {
                    "id": question["id"],
                    "correct": is_correct,
                    "explanation": question["explanation"],
                }
            )
        score_pct = round(100 * correct_count / len(questions))
        run.final_score = score_pct
        run.structured_feedback = {"questions": feedback_questions, "score_pct": score_pct}
    elif run.final_score is None:
        run.final_score = 10

    db.commit()
    db.refresh(run)
    assignment = _assignment_for_run(db, run.id)
    if assignment and assignment.status not in {"destroyed", "destroying"}:
        assignment.status = "destroying"
        db.commit()
        background_tasks.add_task(_destroy_vm_task, assignment.id)
    mark_student_active(db, current_student.id)
    log_activity(db, current_student.id, "lab_submitted", lab.title, "Lab submitted")
    if v2_context:
        assessment, module = v2_context
        practical_status = "completed" if is_structured_lab else "needs_review"
        practical_passed = True if is_structured_lab else None
        practical_activity = record_activity(
            db, student_id=current_student.id, module_key=module.module_key,
            activity_type="practical", ref_key=assessment.assessment_key,
            status=practical_status, passed=practical_passed,
            detail={"lab_run_id": run.id, "evidence_review_required": not is_structured_lab},
            commit=True,
        )
        if not is_structured_lab:
            # A resubmission after mentor rejection is pending again; do not
            # leak the prior deterministic fail/score into the new review.
            practical_activity.passed = None
            practical_activity.score = None
            db.commit()
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
    lab = _get_published_lab(db, run.lab_template_id)
    if _v2_run_context(db, current_student, run) is None:
        require_week_reached(db, current_student, lab.week_number)
    if run.status not in {"assigned", "in_progress"}:
        raise HTTPException(
            status_code=409,
            detail="Evidence can only be uploaded while the lab is in progress",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    if file.content_type not in ALLOWED_EVIDENCE_MIMES:
        raise HTTPException(status_code=415, detail="Unsupported MIME type")

    storage_name = f"{uuid.uuid4()}.{ext}"
    dest = (_screenshots_dir() / storage_name).resolve()
    file_size = 0
    try:
        with dest.open("xb") as handle:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                file_size += len(chunk)
                if file_size > MAX_EVIDENCE_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {MAX_EVIDENCE_UPLOAD_BYTES // (1024 * 1024)} MB limit",
                    )
                handle.write(chunk)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty files are not allowed")
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    artifact = EvidenceArtifact(
        student_id=current_student.id,
        submission_type="lab",
        submission_id=run.id,
        artifact_type=artifact_type or "screenshot",
        storage_key=storage_name,
        original_filename=file.filename,
        file_size_bytes=file_size,
        mime_type=file.content_type,
    )
    try:
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except Exception:
        db.rollback()
        dest.unlink(missing_ok=True)
        raise

    return ok({"artifact_id": artifact.id, "storage_key": artifact.storage_key})
