"""Pilot-gated student API for the Nexus V2 curriculum presentation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.services.v2_access import (
    require_v2_enabled,
    require_v2_student_access,
    v2_access_state,
    v2_master_enabled,
)
from app.services.v2_curriculum_service import (
    assessment_questions,
    entry_view,
    explain_view,
    lesson_view,
    launch_service_desk,
    module_view,
    resource_activity,
    submit_assessment,
    submit_explain,
)
from app.services.v2_progress_service import V2ProgressError, record_activity
from app.utils.responses import ok

router = APIRouter(prefix="/api/v2/curriculum", tags=["v2-curriculum"])

# Backwards-compatible alias. ``labs.py`` and older tests import this name;
# the policy itself now lives in ``app.services.v2_access``.
v2_curriculum_enabled = v2_master_enabled

__all__ = ["router", "require_v2_enabled", "v2_curriculum_enabled"]


def _not_found(exc: V2ProgressError):
    raise HTTPException(status_code=404, detail=str(exc)) from exc


class ResourceActivityRequest(BaseModel):
    opened: bool = False
    completed: bool = False


class AssessmentSubmitRequest(BaseModel):
    attempt_id: int = Field(..., gt=0)
    answers: dict[str, str | list[str]] = Field(default_factory=dict)


class ExplainSubmitRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=10000)


@router.get("/access")
def get_access(student: Student = Depends(get_current_student)):
    """Answer whether *this* student may use V2.

    Deliberately not behind the V2 gate: the frontend needs a truthful answer
    while V2 is off or the caller is not enrolled. The response describes only
    the caller — never the allowlist, its size, or another student.
    """
    return ok(v2_access_state(student))


@router.get("")
def get_entry(
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    return ok(entry_view(db, student.id))


@router.get("/modules/{module_key}")
def get_module(
    module_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(module_view(db, student.id, module_key))
    except V2ProgressError as exc:
        _not_found(exc)


@router.get("/modules/{module_key}/lessons/{lesson_key}")
def get_lesson(
    module_key: str,
    lesson_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(lesson_view(db, student.id, module_key, lesson_key))
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/lessons/{lesson_key}/complete")
def complete_lesson(
    module_key: str,
    lesson_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        lesson_view(db, student.id, module_key, lesson_key)
        row = record_activity(
            db, student_id=student.id, module_key=module_key,
            activity_type="lesson", ref_key=lesson_key, status="completed", commit=True,
        )
        return ok({"status": row.status, "completed_at": row.updated_at})
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/resources/{resource_key}/activity")
def post_resource_activity(
    module_key: str,
    resource_key: str,
    body: ResourceActivityRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    if not body.opened and not body.completed:
        raise HTTPException(status_code=422, detail="Choose an activity to record.")
    try:
        return ok(resource_activity(db, student.id, module_key, resource_key, opened=body.opened, completed=body.completed))
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/service-desk/{assessment_key}/launch")
def post_service_desk_launch(
    module_key: str,
    assessment_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(launch_service_desk(db, student.id, module_key, assessment_key))
    except V2ProgressError as exc:
        _not_found(exc)


@router.get("/modules/{module_key}/assessments/{assessment_key}")
def get_assessment(
    module_key: str,
    assessment_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(assessment_questions(db, student.id, module_key, assessment_key))
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/assessments/{assessment_key}/submit")
def post_assessment(
    module_key: str,
    assessment_key: str,
    body: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    normalized = {
        key: ",".join(value) if isinstance(value, list) else value
        for key, value in body.answers.items()
    }
    try:
        return ok(submit_assessment(db, student.id, module_key, assessment_key, body.attempt_id, normalized))
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/assessments/{assessment_key}/attempts")
def start_assessment_attempt(
    module_key: str,
    assessment_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(assessment_questions(db, student.id, module_key, assessment_key, explicit_start=True))
    except V2ProgressError as exc:
        _not_found(exc)


@router.get("/modules/{module_key}/explain/{prompt_key}")
def get_explain(
    module_key: str,
    prompt_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(explain_view(db, student.id, module_key, prompt_key))
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/explain/{prompt_key}/submit")
def post_explain(
    module_key: str,
    prompt_key: str,
    body: ExplainSubmitRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(submit_explain(db, student.id, module_key, prompt_key, body.answer))
    except V2ProgressError as exc:
        _not_found(exc)
