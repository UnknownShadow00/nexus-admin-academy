"""Explicit, rerunnable learner-data backfill for beginner continuation."""

from collections import Counter

from sqlalchemy.orm import Session

from app.models.certification import CertificationModule
from app.models.student import Student
from app.models.v2_continuation import V2BeginnerContinuationGrant
from app.models.v2_evidence import V2EvidenceRecord, V2EvidenceRequirement
from app.models.v2_interaction import V2InteractionAttempt, V2InteractionDefinition
from app.models.v2_progress import V2AssessmentAttempt, V2ModuleActivity
from app.services.v2_beginner_path import STAGE_KEYS
from app.services.v2_continuation_service import create_beginner_continuation_grant
from app.services.v2_progress_service import V2ProgressError, module_progress

GRANT_REASONS = (
    "requirements_satisfied", "backfill_mastered", "backfill_prior_access",
    "backfill_reopened_approval",
)


def backfill_beginner_continuation(db: Session, *, dry_run: bool = True) -> dict:
    """Plan grants from current mastery/evidence and trusted later-stage work.

    No mastery record is changed. A failed row alone cannot prove earlier
    access; it is reported for manual review instead.
    """
    modules = {
        row.module_key: row for row in db.query(CertificationModule).filter(
            CertificationModule.module_key.in_(STAGE_KEYS),
        )
    }
    counts: Counter[str] = Counter()
    exceptions: list[dict] = []
    for (student_id,) in db.query(Student.id).order_by(Student.id):
        existing = {
            module_id for (module_id,) in db.query(V2BeginnerContinuationGrant.certification_module_id).filter_by(
                student_id=student_id,
            )
        }
        planned: dict[int, str] = {}
        for key in STAGE_KEYS:
            module = modules.get(key)
            if module is None:
                continue
            try:
                progress = module_progress(db, student_id, key)
            except V2ProgressError as exc:
                exceptions.append({"student_id": student_id, "module_key": key, "reason": str(exc)})
                continue
            if module.id in existing:
                continue
            if progress["module_complete"]:
                planned[module.id] = "backfill_mastered"
            elif progress["continuation_eligible"]:
                planned[module.id] = "requirements_satisfied"
            elif module_progress(
                db, student_id, key, backfill_prior_review=True,
            )["continuation_eligible"]:
                planned[module.id] = (
                    "requirements_satisfied" if progress["status"] == "needs_correction"
                    else "backfill_reopened_approval"
                )
            elif progress["status"] == "needs_correction":
                exceptions.append({"student_id": student_id, "module_key": key, "reason": "rejected practical lacks qualifying evidence"})

        # Later server-owned activity proves the learner previously reached
        # that stage. Preserve the entire earlier prefix, regardless of its
        # present mentor review state or a later content revision.
        for index, key in enumerate(STAGE_KEYS):
            module = modules.get(key)
            if module is None:
                continue
            later = db.query(V2ModuleActivity.id).filter(
                V2ModuleActivity.student_id == student_id,
                V2ModuleActivity.module_key == key,
                V2ModuleActivity.status.notin_(("failed", "not_started")),
            ).first()
            if not later:
                later = db.query(V2AssessmentAttempt.id).filter(
                    V2AssessmentAttempt.student_id == student_id,
                    V2AssessmentAttempt.module_key == key,
                    V2AssessmentAttempt.status != "failed",
                ).first()
            if not later:
                later = db.query(V2InteractionAttempt.id).join(
                    V2InteractionDefinition,
                    V2InteractionAttempt.definition_id == V2InteractionDefinition.id,
                ).filter(
                    V2InteractionAttempt.student_id == student_id,
                    V2InteractionDefinition.module_id == module.id,
                    V2InteractionAttempt.passed.is_(True),
                ).first()
            if not later:
                later = db.query(V2EvidenceRecord.id).join(
                    V2EvidenceRequirement,
                    V2EvidenceRecord.requirement_id == V2EvidenceRequirement.id,
                ).filter(
                    V2EvidenceRecord.student_id == student_id,
                    V2EvidenceRequirement.module_id == module.id,
                ).first()
            failed_only = db.query(V2ModuleActivity.id).filter_by(
                student_id=student_id, module_key=key, status="failed",
            ).first()
            if failed_only and not later:
                exceptions.append({"student_id": student_id, "module_key": key, "reason": "failed-only later activity needs manual review"})
            if not later:
                continue
            for previous in STAGE_KEYS[:index]:
                prior = modules.get(previous)
                if prior and prior.id not in existing and prior.id not in planned:
                    planned[prior.id] = "backfill_prior_access"

        for module_id, reason in planned.items():
            if dry_run or create_beginner_continuation_grant(db, student_id, module_id, reason):
                counts[reason] += 1
    if not dry_run:
        db.commit()
    return {"dry_run": dry_run, "counts": {reason: counts[reason] for reason in GRANT_REASONS}, "exceptions": exceptions}
