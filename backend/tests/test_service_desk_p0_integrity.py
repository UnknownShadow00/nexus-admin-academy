"""Wave 0 expected-failure characterization for P0 Service Desk findings."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import seed_v2_foundation
from app.models.certification import ModuleAssessment
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskAssignment,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.v2_progress import V2ModuleActivity
from app.routers.service_desk import start_attempt
from app.services.service_desk_grading import compute_grade
from app.services.v2_curriculum_service import (
    assessment_is_available,
    service_desk_scenario_is_playable,
)
from conftest import make_student
from scripts.generate_service_desk_v2_inventory import (
    browser_operability_failures,
    collect_inventory,
)


def _published_assessment(db, assessment_key: str):
    assessment = db.query(ModuleAssessment).filter_by(
        assessment_key=assessment_key
    ).one()
    scenario = db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id, status="published")
        .order_by(ServiceDeskScenarioVersion.version_number.desc())
        .first()
    )
    assert version is not None
    return assessment, scenario, version


def _attempt(db, student, version, *, current_state=None):
    attempt = ServiceDeskAttempt(
        student_id=student.id,
        scenario_version_id=version.id,
        mode="learning",
        experience_mode="assessment",
        current_state=current_state or {},
        current_state_hash="p0-characterization".ljust(64, "0"),
        state_version=0,
        attempt_number=1,
    )
    db.add(attempt)
    db.flush()
    return attempt


def _event(db, attempt, sequence, event_type, payload):
    db.add(
        ServiceDeskAttemptEvent(
            attempt_id=attempt.id,
            sequence_number=sequence,
            idempotency_key=f"p0-{attempt.id}-{sequence}",
            event_type=event_type,
            tool="ticket",
            payload_json=payload,
            previous_state_hash=attempt.current_state_hash,
            resulting_state_hash=attempt.current_state_hash,
            success=True,
            trusted=True,
        )
    )


def test_p0_finding_a_note_only_v2_ticket_is_unavailable(db, monkeypatch):
    seed_v2_foundation.run(db)
    assessment, scenario, _ = _published_assessment(
        db, "assess.aplus-core2-identity-endpoint-hardening.service_desk"
    )
    student = make_student(db, username="p0-note-only")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", str(student.id))

    assert assessment.active is False
    assert service_desk_scenario_is_playable(db, assessment) is False
    assert assessment_is_available(db, assessment, student.id) is False

    module_key = "module.aplus.core2.identity_endpoint_hardening"
    assignment = ServiceDeskAssignment(
        student_id=student.id,
        scenario_id=scenario.id,
        mode="learning",
        is_required=True,
        maximum_attempts=3,
        assigned_by=f"v2_curriculum:{module_key}:{assessment.assessment_key}",
    )
    db.add(assignment)
    db.add(
        V2ModuleActivity(
            student_id=student.id,
            module_key=module_key,
            activity_type="service_desk",
            ref_key=assessment.assessment_key,
            detail={"scenario_id": scenario.id},
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        start_attempt(
            assignment.id,
            current_student=student,
            db=db,
            _=None,
            v2_module_key=module_key,
            v2_assessment_key=assessment.assessment_key,
        )
    assert exc_info.value.status_code == 404
    # The raw compute_grade fallback deliberately remains unchanged for
    # non-V2 legacy scenarios; V2 safety is enforced at availability/start.


def test_p0_finding_b_every_v2_service_desk_assessment_is_browser_operable(db):
    seed_v2_foundation.run(db)
    rows = collect_inventory(db, feature_enabled=True)
    active_rows = [row for row in rows if row.active]
    failures = browser_operability_failures(active_rows)
    # The paired simulation-engine test actually applies ticket.add_note plus
    # connect/login/authenticate/remote_desktop.open_app. Wave 3 must make this
    # complete set operable or unavailable rather than leave a broken launch.
    assert len(active_rows) == 6 and failures == [], (
        f"available set is incomplete or browser-inoperable: "
        f"active={len(active_rows)}, failures={failures}"
    )


def test_p0_finding_e_resolved_ticket_exposes_failed_learner_outcome(db):
    seed_v2_foundation.run(db)
    assessment, _, version = _published_assessment(
        db, "assess.aplus.wintriage.service_desk"
    )
    student = make_student(db, username="p0-resolved-not-passed")
    ticket_id = version.definition_json["id"]
    attempt = _attempt(
        db,
        student,
        version,
        current_state={"ticket": {"id": ticket_id, "status": "Resolved"}},
    )
    _event(db, attempt, 1, "ticket.close", {"ticketId": ticket_id})
    db.commit()

    grade = compute_grade(db, attempt)
    assert attempt.current_state["ticket"]["status"] == "Resolved"
    assert grade["passed"] is False
    assert grade["overall_score"] < assessment.pass_percent
    # Wave 6 adds an explicit learner outcome distinct from operational state.
    assert grade["details"]["learner_outcome"] == "needs_another_attempt"
