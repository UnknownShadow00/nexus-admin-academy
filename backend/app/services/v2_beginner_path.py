"""Pilot-only ordering and access policy for the versioned beginner path."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.certification import CertificationModule, CertificationVersion
from app.models.student import Student
from app.services.v2_access import (
    V2_UNAVAILABLE_DETAIL, require_v2_student_access, student_has_v2_access,
)
from app.services.v2_continuation_service import has_beginner_continuation_grant

BEGINNER_VERSION = "nexus_beginner_aplus_v1"
STAGE_KEYS = (
    "module.nexus.beginner.stage1",
    "module.nexus.beginner.stage2",
    "module.nexus.beginner.stage3",
    "module.nexus.beginner.stage4",
)


def beginner_path_enabled() -> bool:
    return os.getenv("V2_BEGINNER_PATH_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }


def stage_lock_reason(db: Session, student_id: int, module_key: str) -> str | None:
    """Return a learner-facing prerequisite, without trusting client progress."""
    if module_key not in STAGE_KEYS:
        return None
    index = STAGE_KEYS.index(module_key)
    for prior_index, previous in enumerate(STAGE_KEYS[:index], start=1):
        prior = db.query(CertificationModule).filter_by(module_key=previous, active=True).one_or_none()
        if prior is None or not has_beginner_continuation_grant(db, student_id, prior.id):
            return f"Finish Stage {prior_index} before starting Stage {index + 1}."
    return None


def enforce_beginner_module_policy(
    db: Session,
    student: Student,
    module_key: str,
    *,
    module: CertificationModule | None = None,
    existing_trusted: bool = False,
) -> None:
    """Authorize new V2 work or a caller-verified, already-owned run/attempt.

    Routers must verify persisted run/attempt provenance before using
    ``existing_trusted``. That exception preserves work already in progress;
    it never permits a new launch from a hidden curriculum version.
    """
    if not student_has_v2_access(student):
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)
    if existing_trusted:
        return
    if not beginner_path_enabled():
        if module_key in STAGE_KEYS:
            raise HTTPException(status_code=404, detail="This stage is not available.")
        return
    if module is None:
        module = db.query(CertificationModule).filter_by(module_key=module_key, active=True).one_or_none()
    elif module.module_key != module_key or not module.active:
        module = None
    version = db.get(CertificationVersion, module.certification_version_id) if module else None
    if version is None or version.version_key != BEGINNER_VERSION:
        raise HTTPException(status_code=404, detail="This stage is not available.")
    reason = stage_lock_reason(db, student.id, module_key)
    if reason:
        raise HTTPException(status_code=403, detail=reason)


def require_beginner_stage(
    module_key: str,
    db: Session = Depends(get_db),
    student: Student = Depends(require_v2_student_access),
) -> None:
    """Protect every V2 module route when the beginner pilot path is active."""
    enforce_beginner_module_policy(db, student, module_key)
