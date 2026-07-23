"""Server-side feature gates for the disabled-by-default Service Desk slice."""

import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.service_desk import ServiceDeskBetaEnrollment
from app.models.student import Student


def _enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def service_desk_student_enabled() -> bool:
    """Students require an explicit environment opt-in."""
    return _enabled("SERVICE_DESK_LAB_ENABLED")


def service_desk_admin_enabled() -> bool:
    """Admin review is independently opt-in; student rollout never enables it."""
    return _enabled("SERVICE_DESK_LAB_ADMIN_ENABLED")


def require_service_desk_student_enabled() -> None:
    if not service_desk_student_enabled():
        raise HTTPException(
            status_code=404,
            detail={"code": "SERVICE_DESK_UNAVAILABLE", "message": "Service Desk Lab is not available."},
        )


def require_service_desk_admin_enabled() -> None:
    if not service_desk_admin_enabled():
        raise HTTPException(
            status_code=404,
            detail={"code": "SERVICE_DESK_ADMIN_UNAVAILABLE", "message": "Service Desk Lab administration is not available."},
        )


def student_has_service_desk_beta_access(db: Session, student: Student) -> bool:
    """Return only an explicit active enrollment; mentors receive no implicit access."""
    return bool(
        db.query(ServiceDeskBetaEnrollment.id)
        .filter(
            ServiceDeskBetaEnrollment.student_id == student.id,
            ServiceDeskBetaEnrollment.enabled.is_(True),
            ServiceDeskBetaEnrollment.removed_at.is_(None),
        )
        .first()
    )


def require_service_desk_student_access(db: Session, student: Student) -> None:
    require_service_desk_student_enabled()
    if not student_has_service_desk_beta_access(db, student):
        # A 404 prevents route probing from becoming a beta roster oracle.
        raise HTTPException(
            status_code=404,
            detail={"code": "SERVICE_DESK_UNAVAILABLE", "message": "Service Desk Lab is not available."},
        )
