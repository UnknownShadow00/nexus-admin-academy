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
    ServiceDeskCompleteCreate, ServiceDeskEventCreate, ServiceDeskHintCreate,
)
from app.services.auth_service import ensure_student_access, get_current_student

router = APIRouter(prefix="/api/service-desk", tags=["service-desk"])


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
                       "scenario": {"title": scenario.title, "description": scenario.description,
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
                  payload: dict, resulting_state: dict, success: bool):
    existing = db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt.id, idempotency_key=key).first()
    if existing:
        return _event_dict(existing), 200
    sequence = (db.query(func.max(ServiceDeskAttemptEvent.sequence_number)).filter_by(attempt_id=attempt.id).scalar() or 0) + 1
    event = ServiceDeskAttemptEvent(attempt_id=attempt.id, sequence_number=sequence, idempotency_key=key,
                                    event_type=event_type, tool=tool, payload_json=payload,
                                    previous_state_hash=attempt.current_state_hash,
                                    resulting_state_hash=_hash_state(resulting_state), success=success)
    db.add(event)
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
    data, code = _record_event(db, attempt, key=body.idempotency_key, event_type=body.event_type, tool=body.tool,
                               payload=body.payload, resulting_state=body.resulting_state, success=body.success)
    return _json_response(data, code)


@router.post("/attempts/{attempt_id}/hints")
def record_hint(attempt_id: int, body: ServiceDeskHintCreate, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    attempt = _owned_attempt(db, attempt_id, current_student)
    if attempt.status != "in_progress":
        raise HTTPException(409, "Attempt is no longer in progress")
    data, code = _record_event(db, attempt, key=body.idempotency_key, event_type="hint_requested", tool=body.tool,
                            payload=body.payload, resulting_state=attempt.current_state, success=True)
    return _json_response(data, code)


@router.post("/attempts/{attempt_id}/complete")
def complete_attempt(attempt_id: int, body: ServiceDeskCompleteCreate, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    attempt = _owned_attempt(db, attempt_id, current_student)
    existing = db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt.id).first()
    if attempt.status != "in_progress" and existing:
        return _json_response(_grade_dict(existing), 200)
    if attempt.status != "in_progress":
        raise HTTPException(409, "Attempt is no longer in progress")
    grade = ServiceDeskAttemptGrade(attempt_id=attempt.id, scenario_version_id=attempt.scenario_version_id,
                                    rubric_version=body.rubric_version, technical_complete=body.technical_complete,
                                    critical_failure=body.critical_failure, overall_score=body.overall_score,
                                    passed=body.passed, feedback_summary=body.feedback_summary, details_json=body.details)
    db.add(grade)
    attempt.status = "completed" if body.passed else "failed"
    attempt.completed_at = datetime.now(timezone.utc)
    attempt.score = body.overall_score
    attempt.passed = body.passed
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
