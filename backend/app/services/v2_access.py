"""Single source of truth for who may use the Nexus V2 curriculum.

V2 ships behind two independent controls:

``V2_CURRICULUM_ENABLED``
    The master kill switch. Off means nobody — student, mentor, or admin —
    reaches a V2 surface.

``V2_PILOT_STUDENT_IDS``
    The pilot enrolment allowlist: a comma-separated list of student ids that
    may use V2 while the master switch is on. This deliberately **fails
    closed** — turning the master switch on without naming anyone enrols
    nobody, so a mis-set flag cannot expose the whole cohort mid-pilot.

A student reaches V2 when the master switch is on **and** they are either
named in the allowlist or flagged as a mentor (mentors preview the cohort's
experience; they are not enrolled learners).

Every V2 environment variable is parsed here and nowhere else. Routers depend
on the helpers below rather than reading ``os.environ`` themselves.
"""

from __future__ import annotations

import os
import re

from fastapi import Depends, HTTPException

from app.models.student import Student
from app.services.auth_service import get_current_student

_TRUTHY = {"1", "true", "yes", "on"}

# Operators paste these lists by hand; accept commas, semicolons, and newlines.
_SEPARATORS = re.compile(r"[,;\s]+")

#: Presented to any caller denied a V2 surface. It is deliberately identical
#: to the "feature is off" message so a non-enrolled student cannot probe
#: whether the pilot exists.
V2_UNAVAILABLE_DETAIL = "This learning experience is not available."

MODE_DISABLED = "disabled"
MODE_NOT_ENROLLED = "not_enrolled"
MODE_PILOT = "pilot"
MODE_MENTOR = "mentor"


def v2_master_enabled() -> bool:
    """Return whether the V2 master kill switch is on."""
    return os.getenv("V2_CURRICULUM_ENABLED", "false").strip().lower() in _TRUTHY


def pilot_student_ids() -> frozenset[int]:
    """Parse ``V2_PILOT_STUDENT_IDS`` into a set of student ids.

    Never raises. Malformed entries (non-numeric, negative, zero, floats) are
    dropped rather than failing the whole list, so one bad character in an
    operator-edited env file cannot take the pilot offline or, worse, be
    interpreted as "everyone". Whitespace is trimmed and duplicates collapse.
    """
    raw = os.getenv("V2_PILOT_STUDENT_IDS") or ""
    ids: set[int] = set()
    for token in _SEPARATORS.split(raw.strip()):
        if not token:
            continue
        try:
            value = int(token)
        except ValueError:
            continue
        if value > 0:
            ids.add(value)
    return frozenset(ids)


def pilot_student_count() -> int:
    """How many students are enrolled. Operator/mentor surfaces only."""
    return len(pilot_student_ids())


def student_has_v2_access(student: Student | None) -> bool:
    """Return whether this student may use V2 right now."""
    if student is None or not v2_master_enabled():
        return False
    if getattr(student, "is_mentor", False):
        return True
    student_id = getattr(student, "id", None)
    return student_id is not None and student_id in pilot_student_ids()


def v2_access_state(student: Student | None) -> dict:
    """The student-facing access contract.

    Answers only for the caller. It never reveals the allowlist, its size, or
    any other student's enrolment.
    """
    master = v2_master_enabled()
    enabled = student_has_v2_access(student)
    if not master:
        mode = MODE_DISABLED
    elif not enabled:
        mode = MODE_NOT_ENROLLED
    elif getattr(student, "is_mentor", False) and getattr(student, "id", None) not in pilot_student_ids():
        mode = MODE_MENTOR
    else:
        mode = MODE_PILOT
    return {"master_enabled": master, "student_enabled": enabled, "mode": mode}


def require_v2_enabled() -> None:
    """Master-switch-only gate, for mentor/admin surfaces.

    Admin routes authorize through ``verify_admin``; the pilot allowlist is a
    student enrolment list and must not narrow them.
    """
    if not v2_master_enabled():
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)


def require_v2_student_access(
    student: Student = Depends(get_current_student),
) -> Student:
    """Authenticate the caller and confirm they are in the V2 pilot.

    Returns the resolved student so a route can depend on this alone instead
    of resolving the student twice. Denial is 404, matching the master-switch
    response, so enrolment cannot be probed.
    """
    if not student_has_v2_access(student):
        raise HTTPException(status_code=404, detail=V2_UNAVAILABLE_DETAIL)
    return student
