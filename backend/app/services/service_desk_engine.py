"""Deterministic, server-owned Service Desk attempt state and grading engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskAttemptGrade,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.schemas.service_desk import (
    AttemptActionRequest,
    ScenarioActionKey,
    ScenarioDefinition,
    ScenarioMode,
)
from app.services.service_desk_definitions import published_definition
from app.services.service_desk_features import require_service_desk_student_access


class ScenarioTransitionError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


@dataclass
class TransitionOutcome:
    state: dict
    success: bool
    critical_failure: bool
    feedback: str
    score_key: str | None = None


def state_hash(state: dict) -> str:
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _conditions_match(state: dict, conditions) -> bool:
    return all(state.get(condition.field) == condition.equals for condition in conditions)


def _validated_payload(action_definition, payload: dict) -> None:
    expected = set(action_definition.required_payload_fields)
    provided = set(payload)
    if provided - expected:
        raise ScenarioTransitionError(
            "Action payload contains unsupported fields.", code="INVALID_ACTION_PAYLOAD"
        )
    missing = expected - provided
    if missing:
        raise ScenarioTransitionError(
            "Action payload is missing required information.", code="INVALID_ACTION_PAYLOAD"
        )
    for key in expected:
        value = payload.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ScenarioTransitionError(
                "Action payload is missing required information.", code="INVALID_ACTION_PAYLOAD"
            )


def _precondition_feedback(action_definition, mode: ScenarioMode) -> str:
    if mode == ScenarioMode.LEARNING and action_definition.learning_precondition_feedback:
        return action_definition.learning_precondition_feedback
    return action_definition.simulation_precondition_feedback


def apply_action(
    definition: ScenarioDefinition,
    state: dict,
    *,
    action: ScenarioActionKey,
    payload: dict,
    mode: ScenarioMode,
) -> TransitionOutcome:
    """Apply one declarative action without touching persistence.

    This pure boundary powers both the transactional API path and health/replay
    tests. It does not accept a score, a final state, or a completion signal.
    """
    try:
        action_definition = next(item for item in definition.actions if item.key == action)
    except StopIteration as exc:
        raise ScenarioTransitionError("Unsupported scenario action.", code="UNKNOWN_ACTION") from exc

    if action == ScenarioActionKey.REQUEST_HINT and mode != ScenarioMode.LEARNING:
        raise ScenarioTransitionError("Hints are unavailable in simulation mode.", code="ACTION_NOT_ALLOWED")
    _validated_payload(action_definition, payload)
    next_state = dict(state)

    if not _conditions_match(state, action_definition.preconditions):
        critical = action_definition.critical_on_precondition_failure
        if critical:
            next_state["critical_failure"] = True
        return TransitionOutcome(
            state=next_state,
            success=False,
            critical_failure=critical,
            feedback=_precondition_feedback(action_definition, mode),
        )

    matching_branch = next(
        (
            branch
            for branch in action_definition.branches
            if branch.match_payload
            and all(payload.get(key) == value for key, value in branch.match_payload.items())
        ),
        None,
    )
    if matching_branch is None:
        matching_branch = next(branch for branch in action_definition.branches if not branch.match_payload)

    if not _conditions_match(state, matching_branch.preconditions):
        return TransitionOutcome(
            state=next_state,
            success=False,
            critical_failure=False,
            feedback=_precondition_feedback(action_definition, mode),
        )

    for mutation in matching_branch.mutations:
        next_state[mutation.field] = mutation.value
    if matching_branch.critical_failure:
        next_state["critical_failure"] = True
    return TransitionOutcome(
        state=next_state,
        success=not matching_branch.critical_failure,
        critical_failure=matching_branch.critical_failure,
        feedback=matching_branch.student_feedback,
        score_key=matching_branch.score_key,
    )


def _safe_event_payload(action: ScenarioActionKey, payload: dict, outcome: TransitionOutcome) -> dict:
    """Persist replayable evidence without retaining free-form resolution text."""
    safe = {"action": action.value, "critical_failure": outcome.critical_failure}
    if outcome.score_key:
        safe["score_key"] = outcome.score_key
    for key, value in payload.items():
        if key == "note":
            safe["note_recorded"] = bool(str(value).strip())
            safe["note_length"] = len(str(value))
        elif key in {"password", "recovery_key", "verification_value"}:
            # Scenarios model state transitions, never client-supplied secrets.
            safe[f"{key}_recorded"] = bool(str(value).strip())
        else:
            safe[key] = value
    return safe


def _replay_payload(event: ServiceDeskAttemptEvent) -> dict:
    payload = dict(event.payload_json or {})
    if payload.get("note_recorded"):
        payload["note"] = "[redacted resolution note]"
    payload.pop("action", None)
    payload.pop("critical_failure", None)
    payload.pop("score_key", None)
    payload.pop("note_recorded", None)
    payload.pop("note_length", None)
    return payload


def _score_details(db: Session, attempt: ServiceDeskAttempt, definition: ScenarioDefinition) -> tuple[int, bool, bool, str, dict]:
    events = (
        db.query(ServiceDeskAttemptEvent)
        .filter(ServiceDeskAttemptEvent.attempt_id == attempt.id)
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )
    earned = {
        str((event.payload_json or {}).get("score_key"))
        for event in events
        if event.success and (event.payload_json or {}).get("score_key")
    }
    score = sum(value for key, value in definition.scoring.point_values.items() if key in earned)
    critical = bool(attempt.current_state.get("critical_failure")) or any(
        bool((event.payload_json or {}).get("critical_failure")) for event in events
    )
    technical_complete = _conditions_match(attempt.current_state, definition.success_conditions)
    passed = technical_complete and not critical and score >= definition.scoring.passing_score
    if critical:
        feedback = definition.feedback.critical_failure
    elif passed:
        feedback = definition.feedback.passed
    else:
        feedback = definition.feedback.failed
    return score, technical_complete, critical, feedback, {"earned_score_keys": sorted(earned)}


def _upsert_grade(db: Session, attempt: ServiceDeskAttempt, definition: ScenarioDefinition) -> ServiceDeskAttemptGrade:
    score, technical_complete, critical, feedback, details = _score_details(db, attempt, definition)
    grade = (
        db.query(ServiceDeskAttemptGrade)
        .filter(ServiceDeskAttemptGrade.attempt_id == attempt.id)
        .first()
    )
    if grade is None:
        grade = ServiceDeskAttemptGrade(
            attempt_id=attempt.id,
            scenario_version_id=attempt.scenario_version_id,
            rubric_version=definition.scoring.rubric_version,
            technical_complete=technical_complete,
            critical_failure=critical,
            overall_score=score,
            passed=technical_complete and not critical and score >= definition.scoring.passing_score,
            feedback_summary=feedback,
            details_json=details,
        )
        db.add(grade)
    else:
        grade.technical_complete = technical_complete
        grade.critical_failure = critical
        grade.overall_score = score
        grade.passed = technical_complete and not critical and score >= definition.scoring.passing_score
        grade.feedback_summary = feedback
        grade.details_json = details
        grade.calculated_at = datetime.now(timezone.utc)
    attempt.score = score
    attempt.passed = grade.passed
    return grade


def _scenario_or_404(db: Session, scenario_id: int) -> tuple[ServiceDeskScenario, ServiceDeskScenarioVersion, ScenarioDefinition]:
    scenario = db.query(ServiceDeskScenario).filter(ServiceDeskScenario.id == scenario_id).first()
    if scenario is None or scenario.status != "active":
        raise HTTPException(status_code=404, detail="Scenario not found")
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter(
            ServiceDeskScenarioVersion.scenario_id == scenario.id,
            ServiceDeskScenarioVersion.status == "published",
            ServiceDeskScenarioVersion.validation_status == "valid",
        )
        .order_by(ServiceDeskScenarioVersion.version_number.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario, version, published_definition(version)


def start_attempt(db: Session, student: Student, scenario_id: int, mode: ScenarioMode) -> ServiceDeskAttempt:
    require_service_desk_student_access(db, student)
    scenario, version, definition = _scenario_or_404(db, scenario_id)
    if mode not in definition.supported_modes:
        raise ScenarioTransitionError("Scenario mode is not supported.", code="MODE_NOT_SUPPORTED")
    active = (
        db.query(ServiceDeskAttempt)
        .filter(
            ServiceDeskAttempt.student_id == student.id,
            ServiceDeskAttempt.scenario_version_id == version.id,
            ServiceDeskAttempt.mode == mode.value,
            ServiceDeskAttempt.status == "in_progress",
        )
        .first()
    )
    if active:
        return active
    if mode == ScenarioMode.SIMULATION:
        scored_attempts = (
            db.query(func.count(ServiceDeskAttempt.id))
            .filter(
                ServiceDeskAttempt.student_id == student.id,
                ServiceDeskAttempt.scenario_version_id == version.id,
                ServiceDeskAttempt.mode == ScenarioMode.SIMULATION.value,
                ServiceDeskAttempt.status.in_(["completed", "failed"]),
                ServiceDeskAttempt.admin_reset_at.is_(None),
            )
            .scalar()
            or 0
        )
        assignment = db.query(ServiceDeskAssignment).filter(ServiceDeskAssignment.student_id == student.id, ServiceDeskAssignment.scenario_id == scenario.id, ServiceDeskAssignment.mode == mode.value).first()
        limit = assignment.maximum_attempts if assignment and assignment.maximum_attempts is not None else 3
        if scored_attempts >= limit:
            raise ScenarioTransitionError("Simulation attempt limit reached.", code="SIMULATION_ATTEMPT_LIMIT", status_code=403)
    next_attempt_number = (
        db.query(func.coalesce(func.max(ServiceDeskAttempt.attempt_number), 0))
        .filter(
            ServiceDeskAttempt.student_id == student.id,
            ServiceDeskAttempt.scenario_version_id == version.id,
        )
        .scalar()
        + 1
    )
    initial_state = dict(definition.initial_state)
    attempt = ServiceDeskAttempt(
        student_id=student.id,
        scenario_version_id=version.id,
        mode=mode.value,
        status="in_progress",
        current_state=initial_state,
        current_state_hash=state_hash(initial_state),
        state_version=0,
        attempt_number=next_attempt_number,
    )
    db.add(attempt)
    db.flush()
    db.add(
        ServiceDeskAttemptEvent(
            attempt_id=attempt.id,
            sequence_number=1,
            idempotency_key=f"system-start-{attempt.id}",
            event_type="attempt_started",
            tool="system",
            payload_json={"mode": mode.value},
            previous_state_hash=attempt.current_state_hash,
            resulting_state_hash=attempt.current_state_hash,
            success=True,
        )
    )
    db.flush()
    _upsert_grade(db, attempt, definition)
    db.commit()
    db.refresh(attempt)
    return attempt


def _attempt_and_definition(db: Session, student: Student, attempt_id: int) -> tuple[ServiceDeskAttempt, ScenarioDefinition]:
    attempt = (
        db.query(ServiceDeskAttempt)
        .filter(ServiceDeskAttempt.id == attempt_id, ServiceDeskAttempt.student_id == student.id)
        .first()
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Scenario attempt not found")
    version = db.query(ServiceDeskScenarioVersion).filter(ServiceDeskScenarioVersion.id == attempt.scenario_version_id).first()
    if version is None:
        raise HTTPException(status_code=500, detail="Scenario version is unavailable")
    return attempt, published_definition(version)


def get_owned_attempt(db: Session, student: Student, attempt_id: int) -> tuple[ServiceDeskAttempt, ScenarioDefinition]:
    require_service_desk_student_access(db, student)
    return _attempt_and_definition(db, student, attempt_id)


def apply_attempt_action(db: Session, student: Student, attempt_id: int, request: AttemptActionRequest) -> tuple[ServiceDeskAttempt, TransitionOutcome, bool]:
    require_service_desk_student_access(db, student)
    attempt, definition = _attempt_and_definition(db, student, attempt_id)
    existing = (
        db.query(ServiceDeskAttemptEvent)
        .filter(
            ServiceDeskAttemptEvent.attempt_id == attempt.id,
            ServiceDeskAttemptEvent.idempotency_key == request.idempotency_key,
        )
        .first()
    )
    if existing:
        return attempt, TransitionOutcome(
            state=dict(attempt.current_state), success=existing.success,
            critical_failure=bool((existing.payload_json or {}).get("critical_failure")),
            feedback="This action was already processed.",
            score_key=(existing.payload_json or {}).get("score_key"),
        ), True
    if attempt.status != "in_progress":
        raise ScenarioTransitionError("This attempt is no longer active.", code="ATTEMPT_NOT_ACTIVE", status_code=409)
    if request.expected_state_version != attempt.state_version:
        raise ScenarioTransitionError("Attempt state has changed. Refresh and try again.", code="STATE_CONFLICT", status_code=409)

    outcome = apply_action(
        definition,
        dict(attempt.current_state),
        action=request.action,
        payload=request.payload,
        mode=ScenarioMode(attempt.mode),
    )
    previous_hash = attempt.current_state_hash
    if outcome.state != attempt.current_state:
        attempt.current_state = outcome.state
        attempt.current_state_hash = state_hash(outcome.state)
        attempt.state_version += 1
    sequence = (db.query(func.coalesce(func.max(ServiceDeskAttemptEvent.sequence_number), 0)).filter(ServiceDeskAttemptEvent.attempt_id == attempt.id).scalar() or 0) + 1
    event = ServiceDeskAttemptEvent(
        attempt_id=attempt.id,
        sequence_number=sequence,
        idempotency_key=request.idempotency_key,
        event_type="action",
        tool=next(item.tool for item in definition.actions if item.key == request.action),
        payload_json=_safe_event_payload(request.action, request.payload, outcome),
        previous_state_hash=previous_hash,
        resulting_state_hash=attempt.current_state_hash,
        success=outcome.success,
    )
    db.add(event)
    db.flush()
    grade = _upsert_grade(db, attempt, definition)
    if outcome.critical_failure:
        attempt.status = "failed"
        attempt.completed_at = datetime.now(timezone.utc)
    elif request.action == ScenarioActionKey.RESOLVE_TICKET and outcome.success:
        attempt.status = "completed" if grade.passed else "failed"
        attempt.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ScenarioTransitionError("Concurrent action conflict. Refresh and try again.", code="STATE_CONFLICT", status_code=409) from exc
    db.refresh(attempt)
    return attempt, outcome, False


def replay_attempt(db: Session, attempt: ServiceDeskAttempt) -> dict:
    version = db.query(ServiceDeskScenarioVersion).filter(ServiceDeskScenarioVersion.id == attempt.scenario_version_id).first()
    definition = published_definition(version)
    state = dict(definition.initial_state)
    events = (
        db.query(ServiceDeskAttemptEvent)
        .filter(ServiceDeskAttemptEvent.attempt_id == attempt.id, ServiceDeskAttemptEvent.event_type == "action")
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )
    for event in events:
        action = ScenarioActionKey((event.payload_json or {}).get("action"))
        outcome = apply_action(
            definition, state, action=action, payload=_replay_payload(event), mode=ScenarioMode(attempt.mode)
        )
        state = outcome.state
    return {"state": state, "state_hash": state_hash(state), "event_count": len(events)}


def student_projection(db: Session, attempt: ServiceDeskAttempt, definition: ScenarioDefinition) -> dict:
    grade = db.query(ServiceDeskAttemptGrade).filter(ServiceDeskAttemptGrade.attempt_id == attempt.id).first()
    visible_state = {field: attempt.current_state.get(field) for field in definition.student_visible_state_fields}
    allowed_actions = []
    if attempt.status == "in_progress":
        for action in definition.actions:
            if action.key == ScenarioActionKey.REQUEST_HINT and attempt.mode != ScenarioMode.LEARNING.value:
                continue
            # Field names are necessary for the simulated tool form, but the
            # accepted values and branch rules remain server-only.
            allowed_actions.append({
                "key": action.key.value,
                "tool": action.tool,
                "payload_fields": action.required_payload_fields,
            })
    return {
        "id": attempt.id,
        "scenario": {
            "id": attempt.scenario_version_id,
            "stable_key": definition.stable_key,
            "title": definition.title,
            "description": definition.description,
            "category": definition.category,
            "difficulty": definition.difficulty,
            "learning_objectives": definition.learning_objectives,
            "student_facts": definition.student_facts,
        },
        "mode": attempt.mode,
        "status": attempt.status,
        "attempt_number": attempt.attempt_number,
        "state_version": attempt.state_version,
        "visible_state": visible_state,
        "allowed_actions": allowed_actions,
        "learning_hint": definition.learning_hint if attempt.mode == ScenarioMode.LEARNING.value else None,
        "result": {
            "technical_complete": grade.technical_complete if grade else False,
            "overall_score": grade.overall_score if grade else 0,
            "passed": grade.passed if grade else False,
            "feedback_summary": grade.feedback_summary if grade else None,
        },
    }


def admin_attempt_inspection(db: Session, attempt_id: int) -> dict:
    attempt = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.id == attempt_id).first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Scenario attempt not found")
    events = (
        db.query(ServiceDeskAttemptEvent)
        .filter(ServiceDeskAttemptEvent.attempt_id == attempt.id)
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )
    grade = db.query(ServiceDeskAttemptGrade).filter(ServiceDeskAttemptGrade.attempt_id == attempt.id).first()
    return {
        "attempt": {
            "id": attempt.id, "student_id": attempt.student_id, "scenario_version_id": attempt.scenario_version_id,
            "mode": attempt.mode, "status": attempt.status, "current_state": attempt.current_state,
            "current_state_hash": attempt.current_state_hash, "state_version": attempt.state_version,
            "attempt_number": attempt.attempt_number, "score": attempt.score, "passed": attempt.passed,
            "admin_reset_at": attempt.admin_reset_at.isoformat() if attempt.admin_reset_at else None,
            "admin_reset_by": attempt.admin_reset_by,
        },
        "events": [
            {"sequence_number": event.sequence_number, "event_type": event.event_type, "tool": event.tool,
             "payload": event.payload_json, "success": event.success, "previous_state_hash": event.previous_state_hash,
             "resulting_state_hash": event.resulting_state_hash}
            for event in events
        ],
        "grade": None if grade is None else {
            "technical_complete": grade.technical_complete, "critical_failure": grade.critical_failure,
            "overall_score": grade.overall_score, "passed": grade.passed,
            "feedback_summary": grade.feedback_summary, "details": grade.details_json,
            "rubric_version": grade.rubric_version,
        },
    }


def reset_simulation_attempt(db: Session, attempt_id: int, *, reset_by: str = "admin") -> ServiceDeskAttempt:
    """Release one completed simulation attempt from the three-attempt cap.

    The original attempt, grade, and event log remain intact for audit and
    replay. This is an administrative policy override, not a destructive reset.
    """
    attempt = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.id == attempt_id).first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Scenario attempt not found")
    if attempt.mode != ScenarioMode.SIMULATION.value:
        raise ScenarioTransitionError("Only simulation attempts can be reset.", code="INVALID_RESET")
    if attempt.status == "in_progress":
        raise ScenarioTransitionError("Complete or fail the active attempt before resetting it.", code="ATTEMPT_NOT_TERMINAL", status_code=409)
    if attempt.admin_reset_at is not None:
        return attempt

    sequence = (
        db.query(func.coalesce(func.max(ServiceDeskAttemptEvent.sequence_number), 0))
        .filter(ServiceDeskAttemptEvent.attempt_id == attempt.id)
        .scalar()
        or 0
    ) + 1
    now = datetime.now(timezone.utc)
    attempt.admin_reset_at = now
    attempt.admin_reset_by = reset_by
    db.add(
        ServiceDeskAttemptEvent(
            attempt_id=attempt.id,
            sequence_number=sequence,
            idempotency_key=f"admin-reset-{attempt.id}",
            event_type="admin_reset",
            tool="admin",
            payload_json={"reason": "simulation_attempt_policy_override"},
            previous_state_hash=attempt.current_state_hash,
            resulting_state_hash=attempt.current_state_hash,
            success=True,
        )
    )
    db.commit()
    db.refresh(attempt)
    return attempt
