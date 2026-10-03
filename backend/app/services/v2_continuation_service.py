"""Beginner continuation is a monotonic learning permission, never mastery.

Future course or certificate completion must continue to require actual
``module_complete`` for every required stage.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.certification import CertificationModule
from app.models.lab import LabRun, LabTemplate
from app.models.v2_continuation import V2BeginnerContinuationGrant
from app.models.v2_progress import V2ModuleActivity


def has_beginner_continuation_grant(db: Session, student_id: int, module_id: int) -> bool:
    return db.query(V2BeginnerContinuationGrant.id).filter_by(
        student_id=student_id, certification_module_id=module_id,
    ).first() is not None


def valid_mentor_practical_submission(
    db: Session, student_id: int, assessment, activity: V2ModuleActivity | None,
    *, allow_prior_review: bool = False,
) -> bool:
    """Check current review state against an owned, matching server lab run."""
    valid_states = {"needs_review", "passed"}
    if allow_prior_review:
        valid_states.update({"failed", "in_progress"})
    if activity is None or activity.status not in valid_states:
        return False
    detail = activity.detail or {}
    run_id = detail.get("lab_run_id")
    if not isinstance(run_id, int) or isinstance(run_id, bool):
        return False
    run = db.query(LabRun).filter_by(
        id=run_id, student_id=student_id, lab_template_id=assessment.lab_template_id,
    ).one_or_none()
    if run is None:
        return False
    if activity.status == "needs_review":
        return run.status == "submitted" and run.submitted_at is not None
    if activity.status == "passed":
        return activity.passed is True and detail.get("review_decision") == "approve" and bool(detail.get("reviewed_at"))
    if activity.status == "in_progress":
        # Backfill only: a reviewed practical may have been reopened before
        # grants existed. Normal learning never grants from stale review data.
        return detail.get("review_decision") in {"approve", "reject"} and bool(detail.get("reviewed_at"))
    # Rejection reopens the run and clears submitted_at. The mentor decision,
    # reviewed timestamp and owned run together prove a prior submission.
    return detail.get("review_decision") == "reject" and bool(detail.get("reviewed_at"))


def mentor_review_required(db: Session, assessment) -> bool:
    if not assessment.lab_template_id:
        return False
    lab = db.get(LabTemplate, assessment.lab_template_id)
    return bool(lab and (lab.required_evidence or {}).get("mentor_review_required"))


def create_beginner_continuation_grant(
    db: Session, student_id: int, module_id: int, reason: str,
) -> bool:
    """Insert once inside a savepoint; preserve the caller's other writes."""
    if has_beginner_continuation_grant(db, student_id, module_id):
        return False
    try:
        with db.begin_nested():
            db.add(V2BeginnerContinuationGrant(
                student_id=student_id,
                certification_module_id=module_id,
                grant_reason=reason,
            ))
            db.flush()
    except IntegrityError:
        # The database unique key decides a concurrent or repeated attempt.
        if not has_beginner_continuation_grant(db, student_id, module_id):
            raise
        return False
    return True


def ensure_beginner_continuation_grant(db: Session, student_id: int, module_key: str) -> bool:
    """Evaluate current trusted evidence and persist permission if qualified.

    The caller owns the transaction and commits this with the evidence write.
    Existing grants are never deleted, including after mentor rejection or
    reopening an approved practical.
    """
    from app.services.v2_beginner_path import STAGE_KEYS
    from app.services.v2_progress_service import module_progress

    if module_key not in STAGE_KEYS:
        return False
    module = db.query(CertificationModule).filter_by(module_key=module_key, active=True).one_or_none()
    if module is None or has_beginner_continuation_grant(db, student_id, module.id):
        return False
    if not module_progress(db, student_id, module_key)["continuation_eligible"]:
        return False
    return create_beginner_continuation_grant(db, student_id, module.id, "requirements_satisfied")
