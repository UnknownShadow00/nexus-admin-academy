"""Fixed beginner orientation gate for V2 Service Desk assessments."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.certification import ModuleAssessment
from app.models.service_desk import ServiceDeskScenario
from app.models.v2_progress import (
    V2_ACTIVITY_SERVICE_DESK,
    V2_STATUS_PASSED,
    V2ModuleActivity,
)


SERVICE_DESK_ONBOARDING = (
    "assess.aplus-core1-printers-mfds.service_desk",
    "assess.aplus-core2-windows-admin-cli-networking.service_desk",
    "assess.aplus-core2-service-desk-workflow.service_desk",
)

_SERVICE_DESK_ONBOARDING_SCENARIOS = ("inc2504", "inc2505", "inc2506")

SERVICE_DESK_PREVIOUS_ORIENTATION_REQUIRED = "previous_orientation_ticket_required"
SERVICE_DESK_ORIENTATION_REQUIRED = "service_desk_orientation_required"


def _scenario_stable_key(
    db: Session, assessment: ModuleAssessment
) -> str | None:
    scenario = (
        db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
        if assessment.service_desk_scenario_id
        else None
    )
    if scenario is not None:
        return scenario.stable_key.lower()
    stable_key = (assessment.config or {}).get("engine_service_desk_ref")
    return stable_key.lower() if isinstance(stable_key, str) else None


def _onboarding_bindings_are_valid(db: Session) -> bool:
    """Fail closed if the authored sequence no longer resolves as designed."""
    rows = {
        row.assessment_key: row
        for row in db.query(ModuleAssessment)
        .filter(ModuleAssessment.assessment_key.in_(SERVICE_DESK_ONBOARDING))
        .all()
    }
    return all(
        (assessment := rows.get(assessment_key)) is not None
        and assessment.active
        and assessment.assessment_role == V2_ACTIVITY_SERVICE_DESK
        and _scenario_stable_key(db, assessment) == expected_scenario
        for assessment_key, expected_scenario in zip(
            SERVICE_DESK_ONBOARDING,
            _SERVICE_DESK_ONBOARDING_SCENARIOS,
            strict=True,
        )
    )


def service_desk_onboarding_blocker(
    db: Session,
    student_id: int | None,
    assessment: ModuleAssessment,
) -> str | None:
    """Return the orientation blocker for ``assessment``, if any.

    Calls without a student remain useful as content/playability checks. Every
    student-specific availability or launch path supplies an id and is gated.
    """
    if student_id is None or assessment.assessment_key not in SERVICE_DESK_ONBOARDING:
        return None
    if not _onboarding_bindings_are_valid(db):
        return SERVICE_DESK_ORIENTATION_REQUIRED

    passed_keys = {
        ref_key
        for (ref_key,) in db.query(V2ModuleActivity.ref_key)
        .filter(
            V2ModuleActivity.student_id == student_id,
            V2ModuleActivity.activity_type == V2_ACTIVITY_SERVICE_DESK,
            V2ModuleActivity.ref_key.in_(SERVICE_DESK_ONBOARDING),
            V2ModuleActivity.status == V2_STATUS_PASSED,
        )
        .all()
    }
    try:
        onboarding_index = SERVICE_DESK_ONBOARDING.index(
            assessment.assessment_key
        )
    except ValueError:
        # Non-onboarding Service Desk assessments are NOT hard-blocked behind
        # orientation. Forcing every module's Service Desk ticket to wait on
        # three tickets that live in other modules conflicts with per-module
        # completion semantics (Support Tickets are Extra Practice, never a
        # module gate). The onboarding progression is expressed by ordering
        # the three orientation tickets among themselves plus the
        # ``guidance_level`` / ``onboarding_order`` metadata the frontend uses
        # to surface them first. Reported as a Section 4 conflict.
        return None

    prerequisites = SERVICE_DESK_ONBOARDING[:onboarding_index]
    return (
        None
        if all(key in passed_keys for key in prerequisites)
        else SERVICE_DESK_PREVIOUS_ORIENTATION_REQUIRED
    )
