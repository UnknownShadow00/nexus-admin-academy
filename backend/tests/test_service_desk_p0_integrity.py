"""Wave 0 expected-failure characterization for P0 Service Desk findings."""

from __future__ import annotations

import pytest

import seed_v2_foundation
from app.models.certification import ModuleAssessment
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.services.service_desk_grading import compute_grade
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


@pytest.mark.xfail(strict=True, reason="P0 Finding A — fixed in Wave 2")
def test_p0_finding_a_note_only_v2_ticket_must_not_award_100(db):
    seed_v2_foundation.run(db)
    _, _, version = _published_assessment(
        db, "assess.aplus-core2-service-desk-workflow.service_desk"
    )
    student = make_student(db, username="p0-note-only")
    attempt = _attempt(db, student, version)
    ticket_id = version.definition_json["id"]
    _event(
        db,
        attempt,
        1,
        "ticket.add_note",
        {"ticketId": ticket_id, "body": "Restarted computer and issue resolved."},
    )
    _event(db, attempt, 2, "ticket.close", {"ticketId": ticket_id})
    db.commit()

    grade = compute_grade(db, attempt)
    broken_signature = (
        grade["passed"],
        grade["overall_score"],
        grade["details"]["process_weights"],
    )
    # Today this is exactly (True, 100, None). Wave 2 makes the V2 assessment
    # invalid/unavailable, so this note-only path must stop awarding credit.
    assert broken_signature != (True, 100, None)


@pytest.mark.xfail(strict=True, reason="P0 Finding B — fixed in Wave 3")
def test_p0_finding_b_every_v2_service_desk_assessment_is_browser_operable(db):
    seed_v2_foundation.run(db)
    failures = browser_operability_failures(
        collect_inventory(db, feature_enabled=True)
    )
    # The paired simulation-engine test actually applies ticket.add_note plus
    # connect/login/authenticate/remote_desktop.open_app. Wave 3 must make this
    # complete set operable or unavailable rather than leave a broken launch.
    assert failures == [], f"browser-inoperable V2 assessments: {failures}"


@pytest.mark.xfail(strict=True, reason="P0 Finding E — fixed in Wave 6")
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
