from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lab import LabRun, LabTemplate
from app.models.student import Student
from app.schemas.lab import LabSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import get_current_student
from app.utils.responses import ok

router = APIRouter(prefix="/api/labs", tags=["labs"])


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
            status = "not_started"
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
    return ok(_serialize_lab(lab, run))


@router.post("/{lab_id}/start")
def start_lab(
    lab_id: int,
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
    return ok({"created": created, **_serialize_lab(lab, run)})


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
    mark_student_active(db, current_student.id)
    log_activity(db, current_student.id, "lab_submitted", lab.title, "Lab submitted")
    return ok(_serialize_lab(lab, run))
