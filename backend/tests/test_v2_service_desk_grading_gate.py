"""Permanent integrity gates for V2 Service Desk grading profiles."""

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
from app.services.service_desk_objectives import objective_definition
from app.services.service_desk_realism import fixture_catalog
from app.services.service_desk_scenario_validation import (
    scenario_has_supported_grading_profile,
)
from app.services.v2_content_loader import (
    ContentValidationError,
    LoadSummary,
    load_module,
    reconcile_service_desk_grading_profiles,
)
from app.services.v2_curriculum_service import (
    assessment_is_available,
    service_desk_scenario_is_playable,
)
from conftest import make_student
from scripts.generate_service_desk_v2_inventory import (
    collect_inventory,
    wave2_invariant_failures,
)
from seed import seed_service_desk_scenarios

NOTE_ONLY_ASSESSMENT_KEYS = {
    "assess.aplus-core1-hardware-fault-isolation.service_desk",
    "assess.aplus-core1-mobile-device-support.service_desk",
    "assess.aplus-core1-network-services-troubleshooting.service_desk",
    "assess.aplus-core1-printers-mfds.service_desk",
    "assess.aplus-core2-connected-endpoint-mobile-security.service_desk",
    "assess.aplus-core2-cross-platform-app-cloud-support.service_desk",
    "assess.aplus-core2-identity-endpoint-hardening.service_desk",
    "assess.aplus-core2-service-desk-workflow.service_desk",
    "assess.aplus-core2-threat-malware-response.service_desk",
    "assess.aplus-core2-windows-admin-cli-networking.service_desk",
}
SUPPORTED_ASSESSMENT_KEYS = {
    "assess.aplus.ipcfg.service_desk",
    "assess.aplus.wintriage.service_desk",
}


def _resolved_scenario_version(db, assessment):
    scenario = (
        db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
        if assessment.service_desk_scenario_id
        else None
    )
    if scenario is None:
        stable_key = (assessment.config or {}).get("engine_service_desk_ref")
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=stable_key).one()
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id, status="published")
        .order_by(
            ServiceDeskScenarioVersion.version_number.desc(),
            ServiceDeskScenarioVersion.id.desc(),
        )
        .first()
    )
    assert version is not None
    return scenario, version


def test_every_active_v2_service_desk_assessment_has_categories(db):
    seed_v2_foundation.run(db)
    assessments = (
        db.query(ModuleAssessment)
        .filter_by(assessment_role="service_desk", active=True)
        .all()
    )
    inventory = collect_inventory(db, feature_enabled=True)

    assert wave2_invariant_failures([row for row in inventory if row.active]) == []
    assert assessments
    for assessment in assessments:
        scenario, version = _resolved_scenario_version(db, assessment)
        resolved = objective_definition(scenario.stable_key, version.definition_json)
        assert scenario_has_supported_grading_profile(
            scenario.stable_key, version.definition_json
        )
        assert resolved is not None
        assert {category.name for category in resolved.categories}


def test_note_only_assessments_are_deactivated_and_unavailable(db):
    seed_v2_foundation.run(db)
    student = make_student(db, username="wave2-unavailable")
    assessments = {
        row.assessment_key: row
        for row in db.query(ModuleAssessment).filter_by(
            assessment_role="service_desk"
        )
    }

    assert {
        key for key, row in assessments.items() if not row.active
    } == NOTE_ONLY_ASSESSMENT_KEYS
    for key in NOTE_ONLY_ASSESSMENT_KEYS:
        assessment = assessments[key]
        assert assessment.config["auto_deactivated_reason"] == "no_grading_profile"
        assert service_desk_scenario_is_playable(db, assessment) is False
        assert assessment_is_available(db, assessment, student.id) is False


def test_supported_assessments_remain_active_and_available(db):
    seed_v2_foundation.run(db)
    student = make_student(db, username="wave2-supported")
    assessments = {
        row.assessment_key: row
        for row in db.query(ModuleAssessment).filter(
            ModuleAssessment.assessment_key.in_(SUPPORTED_ASSESSMENT_KEYS)
        )
    }

    assert set(assessments) == SUPPORTED_ASSESSMENT_KEYS
    for assessment in assessments.values():
        assert assessment.active is True
        assert "auto_deactivated_reason" not in (assessment.config or {})
        assert service_desk_scenario_is_playable(db, assessment) is True
        assert assessment_is_available(db, assessment, student.id) is True


def test_strict_loader_names_every_unsupported_active_assessment(db):
    seed_service_desk_scenarios(
        db, ticket_ids=set(fixture_catalog()) | {"INC2403"}
    )

    with pytest.raises(ContentValidationError) as exc_info:
        load_module(db, strict=True)

    message = str(exc_info.value)
    for key in NOTE_ONLY_ASSESSMENT_KEYS:
        assert key in message
    for key in SUPPORTED_ASSESSMENT_KEYS:
        assert key not in message


def test_reconciliation_reactivates_only_gate_owned_rows(db):
    seed_v2_foundation.run(db)
    supported = db.query(ModuleAssessment).filter_by(
        assessment_key="assess.aplus.ipcfg.service_desk"
    ).one()
    gate_owned = db.query(ModuleAssessment).filter_by(
        assessment_key="assess.aplus-core1-printers-mfds.service_desk"
    ).one()
    gate_owned.service_desk_scenario_id = supported.service_desk_scenario_id
    gate_owned.config = {
        **(gate_owned.config or {}),
        "engine_service_desk_ref": "inc2503",
    }
    author_inactive = db.query(ModuleAssessment).filter_by(
        assessment_key="assess.aplus.wintriage.service_desk"
    ).one()
    author_inactive.active = False
    author_inactive.config = {
        key: value
        for key, value in (author_inactive.config or {}).items()
        if key != "auto_deactivated_reason"
    }

    reconcile_service_desk_grading_profiles(db, summary=LoadSummary())

    assert gate_owned.active is True
    assert "auto_deactivated_reason" not in gate_owned.config
    assert author_inactive.active is False


def test_unlinked_legacy_note_only_scenario_keeps_raw_grading_fallback(db):
    student = make_student(db, username="wave2-legacy-control")
    ticket_id = "LEGACY-NOTE-ONLY"
    scenario = ServiceDeskScenario(
        stable_key="legacy-note-only",
        title="Legacy note-only control",
        category="legacy",
        difficulty=1,
        status="active",
        created_by="test",
    )
    db.add(scenario)
    db.flush()
    definition = {
        "id": ticket_id,
        "priority": "medium",
        "objectives": [
            {
                "id": "document",
                "required": True,
                "predicateType": "action_event_occurred",
                "predicateParams": {
                    "actionType": "ticket.add_note",
                    "payloadMatch": {"ticketId": ticket_id},
                },
            }
        ],
    }
    version = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=1,
        definition_json=definition,
        definition_hash="1" * 64,
        validation_status="valid",
        status="published",
        published_by="test",
    )
    db.add(version)
    db.flush()
    attempt = ServiceDeskAttempt(
        student_id=student.id,
        scenario_version_id=version.id,
        mode="learning",
        experience_mode="assessment",
        current_state={},
        current_state_hash="legacy-control".ljust(64, "0"),
        state_version=0,
        attempt_number=1,
    )
    db.add(attempt)
    db.flush()
    for sequence, event_type, payload in (
        (1, "ticket.add_note", {"ticketId": ticket_id, "body": "Legacy note"}),
        (2, "ticket.close", {"ticketId": ticket_id}),
    ):
        db.add(
            ServiceDeskAttemptEvent(
                attempt_id=attempt.id,
                sequence_number=sequence,
                idempotency_key=f"legacy-control-{sequence}",
                event_type=event_type,
                tool="ticket",
                payload_json=payload,
                previous_state_hash=attempt.current_state_hash,
                resulting_state_hash=attempt.current_state_hash,
                success=True,
                trusted=True,
            )
        )
    db.commit()

    assert db.query(ModuleAssessment).count() == 0
    grade = compute_grade(db, attempt)
    assert grade["passed"] is True
    assert grade["overall_score"] == 100
    assert grade["details"]["process_weights"] is None
