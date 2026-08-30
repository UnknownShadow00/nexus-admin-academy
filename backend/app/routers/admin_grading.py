"""Mentor/admin surface for the Phase 1C AI grading pipeline.

Read the queue, read one submission's full grading history, override a grade,
request a regrade against the current rubric, or trigger the worker manually.
All routes require ``verify_admin`` (the single mentor/admin identity), matching
every other ``/api/admin/*`` router.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.grading import GRADE_JOB_PENDING, PendingGrade
from app.services.admin_auth import verify_admin
from app.services.grading_config import load_grading_config
from app.services.grading_queue import (
    apply_mentor_override,
    grading_history,
    mentor_queue,
    resolve_pending,
    run_pending_batch,
)
from app.utils.responses import ok

router = APIRouter(
    prefix="/api/admin/grading", tags=["admin", "grading"], dependencies=[Depends(verify_admin)]
)


class OverrideRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=4000)
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    passed: bool | None = None
    mentor_label: str = Field(default="mentor", max_length=120)


class RegradeRequest(BaseModel):
    rubric: dict | None = None
    rubric_version: str | None = Field(default=None, max_length=40)
    expected_concepts: list[str] | None = None


class RunRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=200)


def _job_or_404(db: Session, pending_grade_id: int) -> PendingGrade:
    job = db.get(PendingGrade, pending_grade_id)
    if job is None:
        raise HTTPException(status_code=404, detail="pending grade not found")
    return job


@router.get("/config")
def grading_config_view():
    cfg = load_grading_config()
    # Safe view only — never the URL or API key.
    return ok(
        {
            "enabled": cfg.enabled,
            "configured": cfg.configured,
            "is_local": cfg.is_local,
            "model": cfg.model or None,
            "endpoint_label": cfg.endpoint_label,
            "timeout_seconds": cfg.timeout_seconds,
            "max_retries": cfg.max_retries,
            "confidence_threshold": cfg.confidence_threshold,
        }
    )


@router.get("/queue")
def grading_queue(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    return ok(mentor_queue(db, limit=limit, offset=max(0, offset)))


@router.get("/{pending_grade_id}")
def grading_detail(pending_grade_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, pending_grade_id)
    return ok(grading_history(db, job))


@router.post("/{pending_grade_id}/override")
def override_grade(pending_grade_id: int, body: OverrideRequest, db: Session = Depends(get_db)):
    job = _job_or_404(db, pending_grade_id)
    try:
        override = apply_mentor_override(
            db,
            job,
            reason=body.reason,
            override_score=body.score,
            override_passed=body.passed,
            mentor_label=body.mentor_label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ok({"override_id": override.id, "history": grading_history(db, job)})


@router.post("/{pending_grade_id}/regrade")
def regrade(pending_grade_id: int, body: RegradeRequest, db: Session = Depends(get_db)):
    """Queue a fresh AI attempt against the CURRENT rubric. Prior ai_grades and
    overrides are preserved; a new attempt appends new history."""
    job = _job_or_404(db, pending_grade_id)
    if body.rubric is not None:
        job.rubric_json = body.rubric
    if body.rubric_version is not None:
        job.rubric_version = body.rubric_version
    if body.expected_concepts is not None:
        job.expected_concepts_json = body.expected_concepts
    job.status = GRADE_JOB_PENDING
    job.retry_count = 0
    job.next_retry_at = datetime.now(timezone.utc)
    job.last_error_category = None
    job.last_error_message = None
    db.flush()
    resolve_pending(db, job)
    db.commit()
    return ok({"pending_grade_id": job.id, "status": job.status})


@router.post("/run")
def run_worker_now(body: RunRequest, db: Session = Depends(get_db)):
    counts = run_pending_batch(db, limit=body.limit)
    return ok(counts)
