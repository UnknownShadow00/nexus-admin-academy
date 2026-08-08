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
    ServiceDeskScenarioCreate,
    ServiceDeskScenarioDraftUpdate,
    ServiceDeskScenarioVersionCreate,
)
from app.services.admin_auth import get_admin_username, verify_admin
from app.services.service_desk_scenario_validation import validate_scenario_definition

router = APIRouter(
    prefix="/api/admin/service-desk",
    tags=["admin"],
    dependencies=[Depends(verify_admin)],
)


def _definition_hash(definition: dict) -> str:
    return hashlib.sha256(
        json.dumps(definition, sort_keys=True).encode()
    ).hexdigest()


def _validation(definition: dict) -> tuple[str, list[str]]:
    errors = validate_scenario_definition(definition)
    return ("invalid" if errors else "valid", errors)


def _version(version: ServiceDeskScenarioVersion, include_definition: bool = True):
    result = {
        "id": version.id,
        "scenario_id": version.scenario_id,
        "version_number": version.version_number,
        "definition_hash": version.definition_hash,
        "validation_status": version.validation_status,
        "status": version.status,
        "published_at": version.published_at,
        "published_by": version.published_by,
        "created_at": version.created_at,
    }
    if include_definition:
        result["definition_json"] = version.definition_json
        result["validation_errors"] = validate_scenario_definition(
            version.definition_json or {}
        )
    return result


def _scenario(db: Session, scenario: ServiceDeskScenario):
    versions = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id)
        .order_by(ServiceDeskScenarioVersion.version_number)
        .all()
    )
    return {
        "id": scenario.id,
        "stable_key": scenario.stable_key,
        "title": scenario.title,
        "description": scenario.description,
        "category": scenario.category,
        "difficulty": scenario.difficulty,
        "status": scenario.status,
        "created_by": scenario.created_by,
        "created_at": scenario.created_at,
        "updated_at": scenario.updated_at,
        "versions": [_version(version) for version in versions],
    }


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
                "trusted": e.trusted,
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
    rows = db.query(ServiceDeskScenario).order_by(ServiceDeskScenario.id).all()
    return jsonable_encoder([_scenario(db, scenario) for scenario in rows])


@router.get("/scenarios/{scenario_id}")
def scenario_detail(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(ServiceDeskScenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return jsonable_encoder(_scenario(db, scenario))


@router.post("/scenarios", status_code=201)
def create_scenario(
    body: ServiceDeskScenarioCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    definition = body.definition_json
    validation_status, _errors = _validation(definition)
    scenario = ServiceDeskScenario(
        stable_key=body.stable_key,
        title=body.title,
        description=body.description,
        category=body.category,
        difficulty=body.difficulty,
        status="active",
        created_by=get_admin_username() or "admin",
    )
    db.add(scenario)
    try:
        db.flush()
        db.add(
            ServiceDeskScenarioVersion(
                scenario_id=scenario.id,
                version_number=1,
                definition_json=definition,
                definition_hash=_definition_hash(definition),
                validation_status=validation_status,
                status="draft",
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A scenario with this slug already exists") from exc
    db.refresh(scenario)
    return jsonable_encoder(_scenario(db, scenario))


@router.post("/scenarios/{scenario_id}/versions", status_code=201)
def create_version(
    scenario_id: int,
    body: ServiceDeskScenarioVersionCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    if not db.query(ServiceDeskScenario).filter_by(id=scenario_id).first():
        raise HTTPException(404, "Scenario not found")
    if db.query(ServiceDeskScenarioVersion).filter_by(
        scenario_id=scenario_id, status="draft"
    ).first():
        raise HTTPException(409, "This scenario already has an editable draft")
    definition_hash = _definition_hash(body.definition_json)
    validation_status, _errors = _validation(body.definition_json)
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
        validation_status=validation_status,
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
    return jsonable_encoder(_version(version))


@router.put("/scenarios/{scenario_id}/versions/{version_id}")
def update_draft_version(
    scenario_id: int,
    version_id: int,
    body: ServiceDeskScenarioDraftUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    scenario = db.query(ServiceDeskScenario).filter_by(id=scenario_id).first()
    version = db.query(ServiceDeskScenarioVersion).filter_by(
        id=version_id, scenario_id=scenario_id
    ).first()
    if not scenario or not version:
        raise HTTPException(404, "Draft scenario version not found")
    if version.status != "draft":
        raise HTTPException(
            409, "Published scenario versions are immutable; create a new draft version"
        )

    definition_hash = _definition_hash(body.definition_json)
    duplicate = db.query(ServiceDeskScenarioVersion.id).filter(
        ServiceDeskScenarioVersion.scenario_id == scenario_id,
        ServiceDeskScenarioVersion.definition_hash == definition_hash,
        ServiceDeskScenarioVersion.id != version.id,
    ).first()
    if duplicate:
        raise HTTPException(409, "An identical scenario definition already exists")

    validation_status, _errors = _validation(body.definition_json)
    scenario.stable_key = body.stable_key
    scenario.title = body.title
    scenario.description = body.description
    scenario.category = body.category
    scenario.difficulty = body.difficulty
    version.definition_json = body.definition_json
    version.definition_hash = definition_hash
    version.validation_status = validation_status
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A scenario with this slug already exists") from exc
    db.refresh(scenario)
    return jsonable_encoder(_scenario(db, scenario))


@router.post("/scenarios/{scenario_id}/versions/{version_id}/validate")
def validate_version(
    scenario_id: int,
    version_id: int,
    db: Session = Depends(get_db),
):
    version = db.query(ServiceDeskScenarioVersion).filter_by(
        id=version_id, scenario_id=scenario_id
    ).first()
    if not version:
        raise HTTPException(404, "Scenario version not found")
    errors = validate_scenario_definition(version.definition_json or {})
    return {"valid": not errors, "errors": errors}


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
    validation_errors = validate_scenario_definition(version.definition_json or {})
    if validation_errors:
        raise HTTPException(
            422,
            {"message": "Scenario validation failed", "errors": validation_errors},
        )
    version.validation_status = "valid"
    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    version.published_by = get_admin_username() or "admin"
    try:
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    db.refresh(version)
    return jsonable_encoder(_version(version))


@router.delete("/scenarios/{scenario_id}", status_code=204)
def delete_draft_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    scenario = db.query(ServiceDeskScenario).filter_by(id=scenario_id).first()
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    versions = db.query(ServiceDeskScenarioVersion).filter_by(scenario_id=scenario_id).all()
    if any(version.status != "draft" for version in versions):
        raise HTTPException(
            409, "Published scenario history cannot be deleted; disable the scenario instead"
        )
    if db.query(ServiceDeskAssignment.id).filter_by(scenario_id=scenario_id).first():
        raise HTTPException(409, "Assigned scenarios cannot be deleted")
    for version in versions:
        db.delete(version)
    db.delete(scenario)
    db.commit()
