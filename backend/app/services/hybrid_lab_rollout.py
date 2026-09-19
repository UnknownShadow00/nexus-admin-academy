"""Shared student-visibility policy for gated Hybrid Labs definitions."""

import os

from app.models.lab import LabTemplate


SINGLE_ACTIVE_PROVISIONERS = {"inc2504_printer_stale_ip"}


def lab_provisioning_handler(lab: LabTemplate) -> str | None:
    requirements = lab.environment_requirements
    if requirements is None:
        return None
    if not isinstance(requirements, dict):
        raise RuntimeError("Lab environment requirements must be an object")
    if "provisioning" not in requirements:
        return None

    provisioning = requirements["provisioning"]
    if not isinstance(provisioning, dict):
        raise RuntimeError("VM provisioning metadata must be an object")
    handler = provisioning.get("handler")
    if not isinstance(handler, str) or not handler.strip():
        raise RuntimeError("VM provisioning handler must be a non-empty string")
    return handler.strip()


def hybrid_poc_rollout_enabled() -> bool:
    return (os.getenv("HYBRID_LABS_POC_ENABLED") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def student_lab_is_visible(lab: LabTemplate) -> bool:
    return (
        lab_provisioning_handler(lab) not in SINGLE_ACTIVE_PROVISIONERS
        or hybrid_poc_rollout_enabled()
    )
