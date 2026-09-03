"""Single idempotent write-back contract from resolved grades to V2 progress."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.certification import CertificationModule, InterviewPrompt
from app.models.grading import GRADE_JOB_GRADED, PendingGrade
from app.models.v2_progress import (
    V2_ACTIVITY_EXPLAIN,
    V2_STATUS_FAILED,
    V2_STATUS_PASSED,
    V2AssessmentAttemptQuestion,
    V2ExplainSubmission,
)
from app.services.v2_progress_service import record_activity


def _numeric_ref_id(submission_ref: str, prefix: str) -> int | None:
    """Return a numeric runtime id without breaking legacy/synthetic grade refs."""
    if not submission_ref.startswith(prefix):
        return None
    try:
        return int(submission_ref.removeprefix(prefix))
    except ValueError:
        return None


def reconcile_resolved_grade(db: Session, job: PendingGrade) -> None:
    """Apply a final AI/mentor result to its owning V2 runtime record."""
    if job.status != GRADE_JOB_GRADED or job.resolved_passed is None:
        return
    if job.submission_ref.startswith("v2-explain:"):
        submission_id = _numeric_ref_id(job.submission_ref, "v2-explain:")
        if submission_id is None:
            return
        submission = db.get(V2ExplainSubmission, submission_id)
        if not submission or submission.student_id != job.student_id:
            return
        prompt = db.get(InterviewPrompt, submission.prompt_id)
        module = db.get(CertificationModule, prompt.certification_module_id) if prompt else None
        if not prompt or not module:
            return
        passed = job.resolved_passed is True
        record_activity(
            db, student_id=job.student_id, module_key=module.module_key,
            activity_type=V2_ACTIVITY_EXPLAIN, ref_key=prompt.prompt_key,
            status=V2_STATUS_PASSED if passed else V2_STATUS_FAILED,
            score=round(float(job.resolved_score or 0) * 100), passed=passed,
            detail={
                "submission_id": submission.id,
                "pending_grade_id": job.id,
                "grading_state": "graded",
                "grade_source": job.resolved_grade_source,
            },
        )
        return
    if job.submission_ref.startswith("v2-assessment-response:"):
        response_id = _numeric_ref_id(job.submission_ref, "v2-assessment-response:")
        if response_id is None:
            return
        response = db.get(V2AssessmentAttemptQuestion, response_id)
        if not response or response.attempt.student_id != job.student_id:
            return
        from app.services.v2_curriculum_service import finalize_assessment_attempt

        finalize_assessment_attempt(db, response.attempt)
