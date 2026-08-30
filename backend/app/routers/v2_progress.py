"""Student-facing Nexus V2 module progress (Phase 2A, development flow).

A student records their own activity in a V2 module and reads their own
roll-up. Ownership is taken from the authenticated student — the body cannot
name another student. This endpoint does NOT feed any legacy progression gate,
XP ledger, mastery calculation, or TrainingWeek.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.services.v2_progress_service import (
    V2ProgressError,
    module_progress,
    record_activity,
)
from app.utils.responses import ok

router = APIRouter(prefix="/api/v2/progress", tags=["v2-progress"])


class RecordActivityRequest(BaseModel):
    module_key: str = Field(..., min_length=3, max_length=160)
    activity_type: str = Field(..., min_length=3, max_length=24)
    ref_key: str = Field(..., min_length=1, max_length=200)
    status: str | None = Field(default=None, max_length=20)
    score: int | None = Field(default=None, ge=0, le=100)
    passed: bool | None = None
    detail: dict | None = None


@router.post("/activity")
def post_activity(
    body: RecordActivityRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    try:
        row = record_activity(
            db,
            student_id=current_student.id,
            module_key=body.module_key,
            activity_type=body.activity_type,
            ref_key=body.ref_key,
            status=body.status,
            score=body.score,
            passed=body.passed,
            detail=body.detail,
            commit=True,
        )
    except V2ProgressError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ok(
        {
            "id": row.id,
            "activity_type": row.activity_type,
            "ref_key": row.ref_key,
            "status": row.status,
            "score": row.score,
            "passed": row.passed,
            "detail": row.detail,
        }
    )


@router.get("/module/{module_key}")
def get_module_progress(
    module_key: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    try:
        data = module_progress(db, current_student.id, module_key)
    except V2ProgressError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ok(data)
