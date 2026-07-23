"""Server-side feature gates for the disabled-by-default Service Desk slice."""

import os

from fastapi import HTTPException


def _enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def service_desk_student_enabled() -> bool:
    """Students require an explicit environment opt-in."""
    return _enabled("SERVICE_DESK_LAB_ENABLED")


def service_desk_admin_enabled() -> bool:
    """Admin inspection can be enabled separately during controlled validation."""
    return service_desk_student_enabled() or _enabled("SERVICE_DESK_LAB_ADMIN_ENABLED")


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
