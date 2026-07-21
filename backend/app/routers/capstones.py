from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.progression import Role, StudentRole
from app.models.student import Student
from app.schemas.capstone import CapstoneSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import get_current_student
from app.services.progression_service import require_week_reached
from app.utils.responses import ok

router = APIRouter(prefix="/api/capstones", tags=["capstones"])


def _accessible_capstones_query(db: Session, student: Student):
    query = db.query(CapstoneTemplate).filter(CapstoneTemplate.is_published.is_(True))
    if student.is_mentor:
        return query

    student_rank = (
        db.query(func.coalesce(func.max(Role.rank_order), 1))
        .select_from(StudentRole)
        .join(Role, StudentRole.role_id == Role.id)
        .filter(StudentRole.student_id == student.id)
        .scalar_subquery()
    )
    required_role = aliased(Role)
    return query.outerjoin(required_role, CapstoneTemplate.role_level == required_role.id).filter(
        or_(CapstoneTemplate.role_level.is_(None), required_role.rank_order <= student_rank)
    )


def has_unlocked_capstones(db: Session, student: Student) -> bool:
    return _accessible_capstones_query(db, student).with_entities(CapstoneTemplate.id).first() is not None


def _serialize_capstone(template: CapstoneTemplate, run: CapstoneRun | None = None) -> dict:
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
        "title": template.title,
        "description": template.description,
        "requirements": template.requirements or {},
        "deliverables": template.deliverables or {},
        "rubric": template.rubric or {},
        "estimated_hours": template.estimated_hours,
        "week_number": template.week_number,
        "status": status,
        "run_id": run.id if run else None,
        "notes": run.notes if run else "",
        "started_at": run.started_at if run else None,
        "submitted_at": run.submitted_at if run else None,
    }


def _get_published_capstone(db: Session, capstone_id: int) -> CapstoneTemplate:
    capstone = (
        db.query(CapstoneTemplate)
        .filter(CapstoneTemplate.id == capstone_id, CapstoneTemplate.is_published.is_(True))
        .first()
    )
    if not capstone:
        raise HTTPException(status_code=404, detail="Capstone not found")
    return capstone


def _get_capstone_run(db: Session, capstone_id: int, student_id: int) -> CapstoneRun | None:
    return (
        db.query(CapstoneRun)
        .filter(CapstoneRun.capstone_template_id == capstone_id, CapstoneRun.student_id == student_id)
        .order_by(CapstoneRun.created_at.desc(), CapstoneRun.id.desc())
        .first()
    )


@router.get("")
def get_capstones(
    week_number: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    query = _accessible_capstones_query(db, current_student)
    if week_number is not None:
        query = query.filter(CapstoneTemplate.week_number == week_number)
    capstones = query.order_by(CapstoneTemplate.week_number.asc(), CapstoneTemplate.created_at.desc()).all()

    capstone_ids = [capstone.id for capstone in capstones]
    runs = {}
    if capstone_ids:
        rows = (
            db.query(CapstoneRun)
            .filter(CapstoneRun.student_id == current_student.id, CapstoneRun.capstone_template_id.in_(capstone_ids))
            .order_by(CapstoneRun.created_at.desc(), CapstoneRun.id.desc())
            .all()
        )
        for row in rows:
            runs.setdefault(row.capstone_template_id, row)

    data = [_serialize_capstone(capstone, runs.get(capstone.id)) for capstone in capstones]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{capstone_id}")
def get_capstone(
    capstone_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    capstone = (
        _accessible_capstones_query(db, current_student)
        .filter(CapstoneTemplate.id == capstone_id)
        .first()
    )
    if not capstone:
        raise HTTPException(status_code=404, detail="Capstone not found")
    run = _get_capstone_run(db, capstone_id, current_student.id)
    return ok(_serialize_capstone(capstone, run))


@router.post("/{capstone_id}/start")
def start_capstone(
    capstone_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    capstone = _get_published_capstone(db, capstone_id)
    require_week_reached(db, current_student, capstone.week_number)
    accessible = (
        _accessible_capstones_query(db, current_student)
        .filter(CapstoneTemplate.id == capstone_id)
        .first()
    )
    if not accessible:
        raise HTTPException(status_code=403, detail="Capstone is locked")
    run = _get_capstone_run(db, capstone_id, current_student.id)
    created = False

    if run is None:
        run = CapstoneRun(
            capstone_template_id=capstone.id,
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
        log_activity(db, current_student.id, "capstone_started", capstone.title, "Capstone in progress")
    return ok({"created": created, **_serialize_capstone(capstone, run)})


@router.post("/{capstone_id}/submit")
def submit_capstone(
    capstone_id: int,
    payload: CapstoneSubmitRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    capstone = _get_published_capstone(db, capstone_id)
    require_week_reached(db, current_student, capstone.week_number)
    accessible = (
        _accessible_capstones_query(db, current_student)
        .filter(CapstoneTemplate.id == capstone_id)
        .first()
    )
    if not accessible:
        raise HTTPException(status_code=403, detail="Capstone is locked")
    run = _get_capstone_run(db, capstone_id, current_student.id)
    now = datetime.now(UTC)

    if run is None:
        run = CapstoneRun(
            capstone_template_id=capstone.id,
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
    log_activity(db, current_student.id, "capstone_submitted", capstone.title, "Capstone submitted")
    return ok(_serialize_capstone(capstone, run))
