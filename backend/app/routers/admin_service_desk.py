import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
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
    ServiceDeskAssignmentCreate,
    ServiceDeskFeedbackCreate,
    ServiceDeskScenarioVersionCreate,
)
from app.services.admin_auth import get_admin_username, verify_admin

router = APIRouter(
    prefix="/api/admin/service-desk",
    tags=["admin"],
    dependencies=[Depends(verify_admin)],
)


def _grade(grade):
    if not grade:
        return None
    return {
        "id": grade.id,
        "attempt_id": grade.attempt_id,
        "scenario_version_id": grade.scenario_version_id,
        "rubric_version": grade.rubric_version,
        "technical_complete": grade.technical_complete,
        "critical_failure": grade.critical_failure,
        "overall_score": grade.overall_score,
        "passed": grade.passed,
        "feedback_summary": grade.feedback_summary,
        "details": grade.details_json,
        "calculated_at": grade.calculated_at,
        "mentor_feedback": grade.mentor_feedback,
        "mentor_feedback_by": grade.mentor_feedback_by,
        "mentor_feedback_at": grade.mentor_feedback_at,
    }


def _full(db, attempt):
    grade = db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt.id).first()
    events = (
        db.query(ServiceDeskAttemptEvent)
        .filter_by(attempt_id=attempt.id)
        .order_by(ServiceDeskAttemptEvent.sequence_number)
        .all()
    )
    return {
        "id": attempt.id,
        "student_id": attempt.student_id,
        "scenario_version_id": attempt.scenario_version_id,
        "mode": attempt.mode,
        "status": attempt.status,
        "current_state": attempt.current_state,
        "current_state_hash": attempt.current_state_hash,
        "state_version": attempt.state_version,
        "attempt_number": attempt.attempt_number,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "score": attempt.score,
        "passed": attempt.passed,
        "created_at": attempt.created_at,
        "updated_at": attempt.updated_at,
        "events": [
            {
                "id": e.id,
                "sequence_number": e.sequence_number,
                "event_type": e.event_type,
                "tool": e.tool,
                "idempotency_key": e.idempotency_key,
                "payload": e.payload_json,
                "success": e.success,
                "created_at": e.created_at,
            }
            for e in events
        ],
        "grade": _grade(grade),
    }


@router.get("/attempts")
def attempts(
    student_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    query = (
        db.query(ServiceDeskAttempt, Student, ServiceDeskScenario)
        .join(Student, Student.id == ServiceDeskAttempt.student_id)
        .join(
            ServiceDeskScenarioVersion,
            ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id,
        )
        .join(
            ServiceDeskScenario,
            ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id,
        )
    )
    if student_id is not None:
        query = query.filter(ServiceDeskAttempt.student_id == student_id)
    rows = (
        query.order_by(
            ServiceDeskAttempt.started_at.desc(), ServiceDeskAttempt.id.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonable_encoder(
        [
            {
                "id": a.id,
                "student_id": st.id,
                "student_name": st.name,
                "student_email": st.email,
                "scenario_title": sc.title,
                "mode": a.mode,
                "status": a.status,
                "score": a.score,
                "passed": a.passed,
                "started_at": a.started_at,
                "completed_at": a.completed_at,
            }
            for a, st, sc in rows
        ]
    )


@router.get("/attempts/{attempt_id}")
def attempt_detail(attempt_id: int, db: Session = Depends(get_db)):
    attempt = db.query(ServiceDeskAttempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    return jsonable_encoder(_full(db, attempt))


@router.post("/attempts/{attempt_id}/feedback")
def feedback(
    attempt_id: int,
    body: ServiceDeskFeedbackCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    attempt = db.query(ServiceDeskAttempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(404, "Attempt not found")
    grade = db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt.id).first()
    if not grade:
        raise HTTPException(
            404,
            "No grade exists yet; wait for completion before adding mentor feedback",
        )
    grade.mentor_feedback = body.mentor_feedback
    grade.mentor_feedback_by = get_admin_username() or "admin"
    grade.mentor_feedback_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(grade)
    return jsonable_encoder(_grade(grade))


@router.post("/assignments", status_code=201)
def create_assignment(
    body: ServiceDeskAssignmentCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    assignment = ServiceDeskAssignment(
        **body.model_dump(),
        assigned_by=get_admin_username() or "admin",
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "This assignment already exists for the student, scenario, and mode"
        ) from exc
    db.refresh(assignment)
    return jsonable_encoder(
        {
            "id": assignment.id,
            "student_id": assignment.student_id,
            "scenario_id": assignment.scenario_id,
            "mode": assignment.mode,
            "is_required": assignment.is_required,
            "due_at": assignment.due_at,
            "maximum_attempts": assignment.maximum_attempts,
            "assigned_by": assignment.assigned_by,
            "assigned_at": assignment.assigned_at,
        }
    )


@router.get("/scenarios")
def scenarios(db: Session = Depends(get_db)):
    result = []
    for scenario in (
        db.query(ServiceDeskScenario).order_by(ServiceDeskScenario.id).all()
    ):
        versions = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id)
            .order_by(ServiceDeskScenarioVersion.version_number)
            .all()
        )
        result.append(
            {
                "id": scenario.id,
                "stable_key": scenario.stable_key,
                "title": scenario.title,
                "description": scenario.description,
                "category": scenario.category,
                "difficulty": scenario.difficulty,
                "status": scenario.status,
                "versions": [
                    {
                        "id": v.id,
                        "version_number": v.version_number,
                        "status": v.status,
                        "definition_hash": v.definition_hash,
                        "published_at": v.published_at,
                    }
                    for v in versions
                ],
            }
        )
    return jsonable_encoder(result)


@router.post("/scenarios/{scenario_id}/versions", status_code=201)
def create_version(
    scenario_id: int,
    body: ServiceDeskScenarioVersionCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    if not db.query(ServiceDeskScenario).filter_by(id=scenario_id).first():
        raise HTTPException(404, "Scenario not found")
    definition_hash = hashlib.sha256(
        json.dumps(body.definition_json, sort_keys=True).encode()
    ).hexdigest()
    number = (
        db.query(func.max(ServiceDeskScenarioVersion.version_number))
        .filter_by(scenario_id=scenario_id)
        .scalar()
        or 0
    ) + 1
    version = ServiceDeskScenarioVersion(
        scenario_id=scenario_id,
        version_number=number,
        definition_json=body.definition_json,
        definition_hash=definition_hash,
        status="draft",
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "An identical scenario definition already exists"
        ) from exc
    db.refresh(version)
    return jsonable_encoder(
        {
            "id": version.id,
            "scenario_id": version.scenario_id,
            "version_number": version.version_number,
            "definition_json": version.definition_json,
            "definition_hash": version.definition_hash,
            "status": version.status,
            "published_at": version.published_at,
            "published_by": version.published_by,
        }
    )


@router.post("/scenarios/{scenario_id}/versions/{version_id}/publish")
def publish_version(
    scenario_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    version = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(id=version_id, scenario_id=scenario_id)
        .first()
    )
    if not version:
        raise HTTPException(404, "Draft scenario version not found")
    if version.status == "published":
        raise HTTPException(409, "Scenario version is already published")
    if version.status == "disabled":
        raise HTTPException(409, "Disabled scenario versions cannot be published")
    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    version.published_by = get_admin_username() or "admin"
    try:
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    db.refresh(version)
    return jsonable_encoder(
        {
            "id": version.id,
            "scenario_id": version.scenario_id,
            "version_number": version.version_number,
            "definition_hash": version.definition_hash,
            "status": version.status,
            "published_at": version.published_at,
            "published_by": version.published_by,
        }
    )
