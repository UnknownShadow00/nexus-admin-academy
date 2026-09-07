"""Wave 4 regression guards for the fixed Service Desk orientation."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import seed_v2_foundation
from app.models.certification import CertificationModule, ModuleAssessment
from app.models.service_desk import ServiceDeskAssignment, ServiceDeskScenario
from app.routers.service_desk import start_attempt
from app.services.v2_curriculum_service import (
    assessment_is_available,
    launch_service_desk,
    module_view,
)
from app.services.v2_progress_service import V2ProgressError, record_activity
from conftest import enroll_v2, make_student


ONBOARDING = (
    (
        "assess.aplus-core1-printers-mfds.service_desk",
        "inc2504",
        "tutorial",
        1,
    ),
    (
        "assess.aplus-core2-windows-admin-cli-networking.service_desk",
        "inc2505",
        "guided",
        2,
    ),
    (
        "assess.aplus-core2-service-desk-workflow.service_desk",
        "inc2506",
        "guided_escalation",
        3,
    ),
)
OTHER_AVAILABLE = {
    "assess.aplus.ipcfg.service_desk",
    "assess.aplus.wintriage.service_desk",
    "assess.aplus-core2-threat-malware-response.service_desk",
}
UNAVAILABLE = {
    "assess.aplus-core1-network-services-troubleshooting.service_desk",
    "assess.aplus-core1-hardware-fault-isolation.service_desk",
    "assess.aplus-core1-mobile-device-support.service_desk",
    "assess.aplus-core2-identity-endpoint-hardening.service_desk",
    "assess.aplus-core2-connected-endpoint-mobile-security.service_desk",
    "assess.aplus-core2-cross-platform-app-cloud-support.service_desk",
}


@pytest.fixture()
def onboarding(db, monkeypatch):
    seed_v2_foundation.run(db)
    student = make_student(db, username="service-desk-orientation")
    enroll_v2(monkeypatch, student)
    assessments = {
        row.assessment_key: row
        for row in db.query(ModuleAssessment).filter_by(
            assessment_role="service_desk"
        )
    }
    return db, student, assessments


def _pass(db, student_id: int, assessment: ModuleAssessment) -> None:
    module = db.get(CertificationModule, assessment.certification_module_id)
    scenario = db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
    record_activity(
        db,
        student_id=student_id,
        module_key=module.module_key,
        activity_type="service_desk",
        ref_key=assessment.assessment_key,
        status="passed",
        score=100,
        passed=True,
        detail={"attempt_id": assessment.id, "scenario_id": scenario.id},
        commit=True,
    )


def _available_keys(db, student_id: int, assessments: dict[str, ModuleAssessment]):
    return {
        key
        for key, assessment in assessments.items()
        if assessment_is_available(db, assessment, student_id)
    }


def _card(db, student_id: int, assessment: ModuleAssessment) -> dict:
    module = db.get(CertificationModule, assessment.certification_module_id)
    return next(
        row
        for row in module_view(db, student_id, module.module_key)["assessments"]
        if row["key"] == assessment.assessment_key
    )


def test_fresh_student_sees_tutorial_and_ungated_tickets(onboarding):
    db, student, assessments = onboarding

    # The three orientation tickets are ordered among themselves; every other
    # available Service Desk ticket is reachable straight away (a per-module
    # Service Desk assessment is Extra Practice, not a hard gate).
    assert _available_keys(db, student.id, assessments) == (
        {ONBOARDING[0][0]} | OTHER_AVAILABLE
    )

    for key, *_ in ONBOARDING[1:]:
        unavailable = _card(db, student.id, assessments[key])["unavailable"]
        assert unavailable["status"] == "service_desk_orientation_required"
        assert unavailable["required_action"] == (
            "Complete the previous orientation ticket first."
        )


def test_orientation_unlocks_one_ticket_at_a_time(onboarding):
    db, student, assessments = onboarding

    _pass(db, student.id, assessments[ONBOARDING[0][0]])
    assert _available_keys(db, student.id, assessments) == (
        {ONBOARDING[0][0], ONBOARDING[1][0]} | OTHER_AVAILABLE
    )

    _pass(db, student.id, assessments[ONBOARDING[1][0]])
    assert _available_keys(db, student.id, assessments) == (
        {key for key, *_ in ONBOARDING} | OTHER_AVAILABLE
    )


def test_launch_rejects_locked_ticket_and_accepts_current_orientation_step(onboarding):
    db, student, assessments = onboarding
    first = assessments[ONBOARDING[0][0]]
    second = assessments[ONBOARDING[1][0]]

    with pytest.raises(V2ProgressError, match="not available"):
        launch_service_desk(
            db,
            student.id,
            db.get(CertificationModule, second.certification_module_id).module_key,
            second.assessment_key,
        )

    first_module = db.get(CertificationModule, first.certification_module_id)
    launch = launch_service_desk(
        db, student.id, first_module.module_key, first.assessment_key
    )
    assert launch["launch_url"].startswith("/service-desk/tickets/INC2504")

    _pass(db, student.id, first)
    second_module = db.get(CertificationModule, second.certification_module_id)
    launch = launch_service_desk(
        db, student.id, second_module.module_key, second.assessment_key
    )
    assert launch["launch_url"].startswith("/service-desk/tickets/INC2505")


def test_attempt_start_rechecks_orientation_for_a_forged_locked_assignment(onboarding):
    db, student, assessments = onboarding
    locked = assessments[ONBOARDING[1][0]]
    module = db.get(CertificationModule, locked.certification_module_id)
    assignment = ServiceDeskAssignment(
        student_id=student.id,
        scenario_id=locked.service_desk_scenario_id,
        mode="learning",
        is_required=True,
        maximum_attempts=3,
        assigned_by=f"v2_curriculum:{module.module_key}:{locked.assessment_key}",
    )
    db.add(assignment)
    db.flush()
    record_activity(
        db,
        student_id=student.id,
        module_key=module.module_key,
        activity_type="service_desk",
        ref_key=locked.assessment_key,
        status="in_progress",
        detail={"scenario_id": locked.service_desk_scenario_id},
        commit=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        start_attempt(
            assignment.id,
            current_student=student,
            db=db,
            _=None,
            v2_module_key=module.module_key,
            v2_assessment_key=locked.assessment_key,
        )
    assert exc_info.value.status_code == 404


def test_assessment_view_exposes_orientation_guidance_metadata(onboarding):
    db, student, assessments = onboarding

    for key, stable_key, guidance_level, onboarding_order in ONBOARDING:
        card = _card(db, student.id, assessments[key])
        assert card["service_desk"] == {
            **card["service_desk"],
            "stable_key": stable_key,
            "guidance_level": guidance_level,
            "onboarding_order": onboarding_order,
        }


def test_wave3_unavailable_modules_stay_unavailable_before_and_after_orientation(
    onboarding,
):
    db, student, assessments = onboarding

    for complete_orientation in (False, True):
        if complete_orientation:
            for key, *_ in ONBOARDING:
                _pass(db, student.id, assessments[key])
        for key in UNAVAILABLE:
            assert assessments[key].active is False
            assert assessment_is_available(db, assessments[key], student.id) is False
