"""Pilot-gated student API for the Nexus V2 curriculum presentation."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
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
from app.services.v2_beginner_path import require_beginner_stage
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
from app.services.v2_progress_service import V2EvidenceConflict, V2ProgressError, record_activity
from app.services.v2_interaction_service import (
    MAX_INTERACTION_RESPONSE_LENGTH, InteractionStale, InteractionUnavailable, InteractionValidationError, interaction_view,
    submit_interaction,
)
from app.utils.responses import ok

router = APIRouter(prefix="/api/v2/curriculum", tags=["v2-curriculum"])

# Backwards-compatible alias. ``labs.py`` and older tests import this name;
# the policy itself now lives in ``app.services.v2_access``.
v2_curriculum_enabled = v2_master_enabled

__all__ = ["router", "require_v2_enabled", "v2_curriculum_enabled"]


def _not_found(exc: V2ProgressError):
    raise HTTPException(status_code=404, detail=str(exc)) from exc


class ResourceActivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opened: bool = False
    watched: bool = False


class AssessmentSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attempt_id: int = Field(..., gt=0)
    answers: dict[str, str | list[str]] = Field(default_factory=dict, max_length=200)

    @field_validator("answers")
    @classmethod
    def bounded_answers(cls, answers):
        for key, value in answers.items():
            if not key.isdecimal() or len(key) > 20:
                raise ValueError("Answer keys must be question IDs")
            values = value if isinstance(value, list) else [value]
            if len(values) > 8:
                raise ValueError("Select at most eight options")
            for answer in values:
                if len(answer) > 10000 or any(ord(char) < 32 and char not in "\n\r\t" for char in answer):
                    raise ValueError("Answers allow up to 10,000 characters and no control characters except line breaks and tabs")
        return answers


class ExplainSubmitRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=10000)


class InteractionSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: int = Field(..., gt=0, strict=True)
    response: dict


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


@router.get("/modules/{module_key}", dependencies=[Depends(require_beginner_stage)])
def get_module(
    module_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(module_view(db, student.id, module_key))
    except V2ProgressError as exc:
        _not_found(exc)


@router.get("/modules/{module_key}/lessons/{lesson_key}", dependencies=[Depends(require_beginner_stage)])
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


@router.get("/modules/{module_key}/interactions/{interaction_key}", dependencies=[Depends(require_beginner_stage)])
def get_interaction(
    module_key: str, interaction_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    try:
        return ok(interaction_view(db, student.id, module_key, interaction_key))
    except InteractionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/modules/{module_key}/interactions/{interaction_key}/submit", dependencies=[Depends(require_beginner_stage)])
def post_interaction(
    module_key: str, interaction_key: str, body: InteractionSubmitRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    if len(json.dumps(body.response)) > MAX_INTERACTION_RESPONSE_LENGTH:
        raise HTTPException(status_code=422, detail="Response is too large")
    try:
        return ok(submit_interaction(db, student.id, module_key, interaction_key, body.version_id, body.response))
    except InteractionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InteractionStale as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InteractionValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Please retry this interaction") from exc


@router.post("/modules/{module_key}/lessons/{lesson_key}/complete", dependencies=[Depends(require_beginner_stage)])
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


@router.post("/modules/{module_key}/resources/{resource_key}/activity", dependencies=[Depends(require_beginner_stage)])
def post_resource_activity(
    module_key: str,
    resource_key: str,
    body: ResourceActivityRequest,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
):
    if not body.opened and not body.watched:
        raise HTTPException(status_code=422, detail="Choose an activity to record.")
    try:
        return ok(resource_activity(db, student.id, module_key, resource_key, opened=body.opened, watched=body.watched))
    except V2EvidenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except V2ProgressError as exc:
        _not_found(exc)


@router.post("/modules/{module_key}/service-desk/{assessment_key}/launch", dependencies=[Depends(require_beginner_stage)])
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


@router.get("/modules/{module_key}/assessments/{assessment_key}", dependencies=[Depends(require_beginner_stage)])
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


@router.post("/modules/{module_key}/assessments/{assessment_key}/submit", dependencies=[Depends(require_beginner_stage)])
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


@router.post("/modules/{module_key}/assessments/{assessment_key}/attempts", dependencies=[Depends(require_beginner_stage)])
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


@router.get("/modules/{module_key}/explain/{prompt_key}", dependencies=[Depends(require_beginner_stage)])
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


@router.post("/modules/{module_key}/explain/{prompt_key}/submit", dependencies=[Depends(require_beginner_stage)])
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
