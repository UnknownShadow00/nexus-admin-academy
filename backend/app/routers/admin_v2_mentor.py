"""Feature-flagged mentor/admin surface for Nexus V2 progress intelligence.

One read: everything the backend knows about one student's work in one V2
module — completion, quiz score, missed questions, the objectives those
questions map to, Explain state, practical / Service Desk results, and weak
objectives. Requires ``verify_admin`` like every other ``/api/admin/*`` route.
A polished dashboard is out of scope for Phase 2A; this is the data layer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.admin_auth import verify_admin
from app.routers.v2_curriculum import require_v2_enabled
from app.services.v2_mentor_service import (
    cohort_focus,
    cohort_progress,
    module_report,
    set_cohort_focus,
)
from app.services.v2_progress_service import V2ProgressError
from app.utils.responses import ok

router = APIRouter(
    prefix="/api/admin/v2/mentor",
    tags=["admin", "v2-mentor"],
    dependencies=[Depends(verify_admin), Depends(require_v2_enabled)],
)


class CohortFocusRequest(BaseModel):
    module_key: str = Field(..., min_length=1, max_length=160)


@router.get("/cohort/{module_key}")
def get_cohort_progress(module_key: str, db: Session = Depends(get_db)):
    try:
        return ok(cohort_progress(db, module_key))
    except V2ProgressError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/cohort-focus")
def get_cohort_focus(db: Session = Depends(get_db)):
    return ok(cohort_focus(db))


@router.put("/cohort-focus")
def update_cohort_focus(body: CohortFocusRequest, db: Session = Depends(get_db)):
    try:
        return ok(set_cohort_focus(db, body.module_key))
    except V2ProgressError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/module/{module_key}/student/{student_id}")
def get_module_report(
    module_key: str,
    student_id: int,
    db: Session = Depends(get_db),
):
    try:
        data = module_report(db, student_id, module_key)
    except V2ProgressError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ok(data)
