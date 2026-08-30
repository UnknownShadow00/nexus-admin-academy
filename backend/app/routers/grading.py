"""Student-facing read for the Phase 1C grading pipeline.

A student can check whether their own ambiguous free-response / Explain answer
has been graded yet. Ownership is enforced from the authenticated student; the
response is deliberately thin — no rubric, no AI internals, no error detail.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.grading import (
    GRADE_JOB_GRADED,
    GRADE_JOB_NEEDS_REVIEW,
    PendingGrade,
)
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.utils.responses import ok

router = APIRouter(prefix="/api/grading", tags=["grading"])

_STUDENT_MESSAGE = {
    GRADE_JOB_GRADED: "Your response has been graded.",
    GRADE_JOB_NEEDS_REVIEW: "Your response was saved and is waiting for a mentor to review it.",
}
_PENDING_MESSAGE = "Your response was saved and is waiting to be graded."


@router.get("/status")
def grading_status(
    source_type: str,
    submission_ref: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    job = (
        db.query(PendingGrade)
        .filter(
            PendingGrade.source_type == source_type,
            PendingGrade.submission_ref == submission_ref,
        )
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="No grading job for that submission.")
    if job.student_id != current_student.id:
        # Do not disclose existence of another student's job.
        raise HTTPException(status_code=404, detail="No grading job for that submission.")

    graded = job.status == GRADE_JOB_GRADED
    return ok(
        {
            "state": "graded" if graded else "pending_grading",
            "message": _STUDENT_MESSAGE.get(job.status, _PENDING_MESSAGE),
            "score": job.resolved_score if graded else None,
            "passed": job.resolved_passed if graded else None,
        }
    )
