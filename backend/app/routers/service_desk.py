import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service_desk import (
    ServiceDeskAssignment, ServiceDeskAttempt, ServiceDeskAttemptEvent,
    ServiceDeskAttemptGrade, ServiceDeskScenario, ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.schemas.service_desk import (
    ServiceDeskActionCreate, ServiceDeskCompleteCreate, ServiceDeskEventCreate, ServiceDeskHintCreate,
)
from app.services.service_desk_objectives import SCENARIO_OBJECTIVES, payload_matches
from app.services.auth_service import ensure_student_access, get_current_student
from app.services.service_desk_grading import AttemptNotClosedError, compute_grade
from app.services.xp_service import award_xp

router = APIRouter(prefix="/api/service-desk", tags=["service-desk"])

# The API records simulation actions, not arbitrary browser facts.  Keep this
# intentionally narrow enough to reject invented namespaces while allowing the
# existing simulation tools to evolve within their owned namespaces.
_EVENT_PREFIX_TOOLS = {
    "ticket.": "ticket",
    "directory.": "directory",
    "remote_desktop.": "remote_desktop",
}


def _validate_event_shape(event_type: str, tool: str, payload: dict) -> None:
    expected_tool = next(
        (value for prefix, value in _EVENT_PREFIX_TOOLS.items() if event_type.startswith(prefix)),
        None,
    )
    if expected_tool is None:
        raise HTTPException(422, "Unknown Service Desk event type")
    if tool != expected_tool:
        raise HTTPException(422, "Event tool does not match its event type")
    if event_type == "ticket.close":
        # Close fields are UI metadata only.  They are allowed for compatibility
        # but cannot control verification in compute_grade().
        return
    if event_type.startswith("directory.") and not isinstance(payload.get("directoryUserId"), str):
        raise HTTPException(422, "Directory events require directoryUserId")
    if event_type.startswith("remote_desktop.") and not isinstance(payload.get("assetTag"), str):
        raise HTTPException(422, "Remote Desktop events require assetTag")


def _hash_state(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _json_response(content: dict, code: int) -> JSONResponse:
    return JSONResponse(status_code=code, content=jsonable_encoder(content))


def _event_dict(event: ServiceDeskAttemptEvent) -> dict:
    return {"id": event.id, "attempt_id": event.attempt_id, "sequence_number": event.sequence_number,
            "idempotency_key": event.idempotency_key, "event_type": event.event_type, "tool": event.tool,
            "payload": event.payload_json, "previous_state_hash": event.previous_state_hash,
            "resulting_state_hash": event.resulting_state_hash, "success": event.success, "created_at": event.created_at}


def _grade_dict(grade: ServiceDeskAttemptGrade | None) -> dict | None:
    if not grade:
        return None
    return {"id": grade.id, "attempt_id": grade.attempt_id, "scenario_version_id": grade.scenario_version_id,
            "rubric_version": grade.rubric_version, "technical_complete": grade.technical_complete,
            "critical_failure": grade.critical_failure, "overall_score": grade.overall_score,
            "passed": grade.passed, "feedback_summary": grade.feedback_summary, "details": grade.details_json,
            "calculated_at": grade.calculated_at, "mentor_feedback": grade.mentor_feedback,
            "mentor_feedback_by": grade.mentor_feedback_by, "mentor_feedback_at": grade.mentor_feedback_at}


def _attempt_dict(attempt: ServiceDeskAttempt, grade: ServiceDeskAttemptGrade | None = None) -> dict:
    return {"id": attempt.id, "student_id": attempt.student_id, "scenario_version_id": attempt.scenario_version_id,
            "mode": attempt.mode, "status": attempt.status, "current_state": attempt.current_state,
            "current_state_hash": attempt.current_state_hash, "state_version": attempt.state_version,
            "attempt_number": attempt.attempt_number, "started_at": attempt.started_at,
            "completed_at": attempt.completed_at, "score": attempt.score, "passed": attempt.passed,
            "created_at": attempt.created_at, "updated_at": attempt.updated_at, "grade": _grade_dict(grade)}


def _owned_attempt(db: Session, attempt_id: int, student: Student) -> ServiceDeskAttempt:
    attempt = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    ensure_student_access(student, attempt.student_id)
    return attempt


@router.get("/assignments")
def list_assignments(current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    rows = db.query(ServiceDeskAssignment, ServiceDeskScenario).join(
        ServiceDeskScenario, ServiceDeskScenario.id == ServiceDeskAssignment.scenario_id
    ).filter(ServiceDeskAssignment.student_id == current_student.id).order_by(ServiceDeskAssignment.id).all()
    result = []
    for assignment, scenario in rows:
        version = db.query(ServiceDeskScenarioVersion).filter(
            ServiceDeskScenarioVersion.scenario_id == scenario.id,
            ServiceDeskScenarioVersion.status == "published",
        ).order_by(ServiceDeskScenarioVersion.version_number.desc()).first()
        latest_attempt = None
        if version:
            latest_attempt = db.query(ServiceDeskAttempt).filter(
                ServiceDeskAttempt.student_id == current_student.id,
                ServiceDeskAttempt.scenario_version_id == version.id,
            ).order_by(ServiceDeskAttempt.attempt_number.desc()).first()
        result.append({"id": assignment.id, "student_id": assignment.student_id, "scenario_id": scenario.id,
                       "mode": assignment.mode, "is_required": assignment.is_required, "due_at": assignment.due_at,
                       "maximum_attempts": assignment.maximum_attempts, "assigned_by": assignment.assigned_by,
                       "assigned_at": assignment.assigned_at,
                       "scenario": {"stable_key": scenario.stable_key, "title": scenario.title,
                                    "description": scenario.description,
                                    "category": scenario.category, "difficulty": scenario.difficulty},
                       "latest_published_version": {"id": version.id, "version_number": version.version_number} if version else None,
                       "most_recent_attempt": {"id": latest_attempt.id, "status": latest_attempt.status,
                                               "attempt_number": latest_attempt.attempt_number} if latest_attempt else None})
    return jsonable_encoder(result)


@router.post("/assignments/{assignment_id}/attempts")
def start_attempt(assignment_id: int, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    assignment = db.query(ServiceDeskAssignment).filter(ServiceDeskAssignment.id == assignment_id).first()
    if not assignment or assignment.student_id != current_student.id:
        raise HTTPException(404, "Assignment not found")
    version = db.query(ServiceDeskScenarioVersion).filter(
        ServiceDeskScenarioVersion.scenario_id == assignment.scenario_id,
        ServiceDeskScenarioVersion.status == "published",
    ).order_by(ServiceDeskScenarioVersion.version_number.desc()).first()
    if not version:
        raise HTTPException(409, "This assignment has no published scenario version")
    existing = db.query(ServiceDeskAttempt).filter_by(student_id=current_student.id, scenario_version_id=version.id,
                                                       status="in_progress").first()
    if existing:
        return _json_response(_attempt_dict(existing), 200)
    count = db.query(ServiceDeskAttempt).filter_by(student_id=current_student.id, scenario_version_id=version.id).count()
    if assignment.maximum_attempts is not None and count >= assignment.maximum_attempts:
        raise HTTPException(403, "Maximum attempts for this assignment have been reached")
    attempt = ServiceDeskAttempt(student_id=current_student.id, scenario_version_id=version.id, mode=assignment.mode,
                                 status="in_progress", current_state={}, current_state_hash=_hash_state({}),
                                 state_version=0, attempt_number=count + 1)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _json_response(_attempt_dict(attempt), 201)


@router.get("/attempts/{attempt_id}")
def get_attempt(attempt_id: int, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    attempt = _owned_attempt(db, attempt_id, current_student)
    return jsonable_encoder(_attempt_dict(attempt, db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt.id).first()))


def _record_event(db: Session, attempt: ServiceDeskAttempt, *, key: str, event_type: str, tool: str,
                  payload: dict, resulting_state: dict, success: bool, trusted: bool = False):
    existing = db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt.id, idempotency_key=key).first()
    if existing:
        return _event_dict(existing), 200
    sequence = (db.query(func.max(ServiceDeskAttemptEvent.sequence_number)).filter_by(attempt_id=attempt.id).scalar() or 0) + 1
    event = ServiceDeskAttemptEvent(attempt_id=attempt.id, sequence_number=sequence, idempotency_key=key,
                                    event_type=event_type, tool=tool, payload_json=payload,
                                    previous_state_hash=attempt.current_state_hash,
                                    resulting_state_hash=_hash_state(resulting_state), success=success, trusted=trusted)
    db.add(event)
    # Versioned full snapshots are safe to restore across devices. Legacy
    # tool overlays remain evidence only, except for old ticket clients.
    if resulting_state.get("schema_version") == 1 and isinstance(resulting_state.get("nexus_service_desk_attempt"), dict):
        attempt.current_state = resulting_state
        attempt.current_state_hash = event.resulting_state_hash
    elif tool == "ticket":
        attempt.current_state = resulting_state
        attempt.current_state_hash = event.resulting_state_hash
    attempt.state_version += 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raced = db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt.id, idempotency_key=key).first()
        if raced:
            return _event_dict(raced), 200
        raise
    db.refresh(event)
    return _event_dict(event), 201


@router.post("/attempts/{attempt_id}/events")
def record_event(attempt_id: int, body: ServiceDeskEventCreate, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    attempt = _owned_attempt(db, attempt_id, current_student)
    if attempt.status != "in_progress":
        raise HTTPException(409, "Attempt is no longer in progress")
    _validate_event_shape(body.event_type, body.tool, body.payload)
    data, code = _record_event(db, attempt, key=body.idempotency_key, event_type=body.event_type, tool=body.tool,
                               payload=body.payload, resulting_state=body.resulting_state, success=body.success)
    return _json_response(data, code)


def _scenario_key(db: Session, attempt: ServiceDeskAttempt) -> str:
    return db.query(ServiceDeskScenario).join(ServiceDeskScenarioVersion).filter(
        ServiceDeskScenarioVersion.id == attempt.scenario_version_id
    ).one().stable_key.lower()


def _action_allowed(db: Session, attempt: ServiceDeskAttempt, event_type: str, payload: dict) -> bool:
    """Apply the small server-owned transition graph used for grading.

    Raw event posts cannot enter this graph.  Assignment is the required first
    transition; thereafter only exact scenario rule actions may become trusted.
    """
    key = _scenario_key(db, attempt)
    ticket_id = key.upper()
    events = db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt.id, trusted=True).all()
    # The attempt itself is created only from this student's assignment, so it
    # is a server-owned assignment prerequisite even when the fixture renders
    # the ticket as already assigned and the UI emits no ticket.assign click.
    assigned = db.query(ServiceDeskAssignment).join(ServiceDeskScenario).filter(
        ServiceDeskAssignment.student_id == attempt.student_id,
        ServiceDeskScenario.stable_key == key,
    ).first() is not None
    assigned = assigned or any(
        e.event_type == "ticket.assign" and (e.payload_json or {}).get("ticketId") == ticket_id
        for e in events
    )
    if event_type == "ticket.assign":
        return payload.get("ticketId") == ticket_id
    if not assigned:
        return False
    definition = SCENARIO_OBJECTIVES.get(key)
    if definition is None:
        return False
    rules = (*definition.required_all, *definition.required_any)
    return any(rule.event_type == event_type and payload_matches(payload, rule.payload) for rule in rules)


@router.post("/attempts/{attempt_id}/actions")
def request_action(attempt_id: int, body: ServiceDeskActionCreate, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    """Validate and record a server-authorized simulation transition.

    The browser never supplies success/trusted/state for this endpoint.
    """
    attempt = _owned_attempt(db, attempt_id, current_student)
    if attempt.status != "in_progress":
        raise HTTPException(409, "Attempt is no longer in progress")
    _validate_event_shape(body.event_type, body.tool, body.payload)
    trusted = _action_allowed(db, attempt, body.event_type, body.payload)
    # Non-objective UI actions remain auditable/resumable, but cannot be
    # promoted to grading evidence. Objective-shaped actions require the
    # transition graph above; an objective before assignment is rejected.
    key = _scenario_key(db, attempt)
    definition = SCENARIO_OBJECTIVES.get(key)
    objective_action = definition and any(
        rule.event_type == body.event_type and payload_matches(body.payload, rule.payload)
        for rule in (*definition.required_all, *definition.required_any)
    )
    if objective_action and not trusted:
        raise HTTPException(409, "Action is not available in the current server-authoritative attempt state")
    # Trusted transition state is reconstructed from the trusted ledger.  Do
    # not add it to current_state: that field is the untrusted, versioned UI
    # snapshot used by clean-browser resume.
    data, code = _record_event(db, attempt, key=body.idempotency_key, event_type=body.event_type,
                               tool=body.tool, payload=body.payload, resulting_state=body.resulting_state,
                               success=True, trusted=trusted)
    return _json_response(data, code)


@router.post("/attempts/{attempt_id}/hints")
def record_hint(attempt_id: int, body: ServiceDeskHintCreate, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    attempt = _owned_attempt(db, attempt_id, current_student)
    if attempt.status != "in_progress":
        raise HTTPException(409, "Attempt is no longer in progress")
    data, code = _record_event(db, attempt, key=body.idempotency_key, event_type="hint_requested", tool=body.tool,
                            payload=body.payload, resulting_state=body.resulting_state or attempt.current_state, success=True)
    return _json_response(data, code)


@router.post("/attempts/{attempt_id}/complete")
def complete_attempt(attempt_id: int, body: ServiceDeskCompleteCreate, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    attempt = _owned_attempt(db, attempt_id, current_student)
    existing = db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt.id).first()
    if attempt.status != "in_progress" and existing:
        return _json_response(_grade_dict(existing), 200)
    if attempt.status != "in_progress":
        raise HTTPException(409, "Attempt is no longer in progress")
    try:
        computed = compute_grade(db, attempt)
    except AttemptNotClosedError as exc:
        raise HTTPException(409, str(exc)) from exc
    grade = ServiceDeskAttemptGrade(attempt_id=attempt.id, scenario_version_id=attempt.scenario_version_id,
                                    rubric_version=computed["rubric_version"], technical_complete=computed["technical_complete"],
                                    critical_failure=computed["critical_failure"], overall_score=computed["overall_score"],
                                    passed=computed["passed"], feedback_summary=computed["feedback_summary"], details_json=computed["details"])
    db.add(grade)
    # A failed/incomplete verification is never XP eligible, even if an old
    # scoring display assigns partial points for a closed ticket.
    if computed["passed"]:
        award_xp(
            db,
            student_id=attempt.student_id,
            delta=computed["overall_score"],
            source_type="service_desk_attempt",
            source_id=attempt.id,
            description=f"Service Desk attempt {attempt.id}",
        )
    attempt.status = "completed" if computed["passed"] else "failed"
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.score = computed["overall_score"]
    attempt.passed = computed["passed"]
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt.id).first()
        if existing:
            return _json_response(_grade_dict(existing), 200)
        raise
    db.refresh(grade)
    return _json_response(_grade_dict(grade), 201)


@router.get("/attempts")
def list_attempts(current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    rows = db.query(ServiceDeskAttempt, ServiceDeskScenario).join(ServiceDeskScenarioVersion,
        ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id).join(ServiceDeskScenario,
        ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id).filter(
        ServiceDeskAttempt.student_id == current_student.id).order_by(ServiceDeskAttempt.started_at.desc(), ServiceDeskAttempt.id.desc()).all()
    return jsonable_encoder([{"id": a.id, "scenario_title": s.title, "mode": a.mode, "status": a.status, "score": a.score,
             "passed": a.passed, "started_at": a.started_at, "completed_at": a.completed_at} for a, s in rows]
    )
