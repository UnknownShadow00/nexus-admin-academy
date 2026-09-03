"""Student-facing Nexus V2 module progress (Phase 2A, development flow).

A student records their own activity in a V2 module and reads their own
roll-up. Ownership is taken from the authenticated student — the body cannot
name another student. This endpoint does NOT feed any legacy progression gate,
XP ledger, mastery calculation, or TrainingWeek.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.services.v2_progress_service import (
    V2ProgressError,
    module_progress,
)
from app.utils.responses import ok

router = APIRouter(prefix="/api/v2/progress", tags=["v2-progress"])


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
