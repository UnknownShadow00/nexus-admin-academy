"""Minimal administrator inspection APIs for the Service Desk foundation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from datetime import datetime, timezone

from app.models.service_desk import ServiceDeskAssignment, ServiceDeskAttempt, ServiceDeskBetaEnrollment, ServiceDeskKnowledgeArticle, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.student import Student
from app.schemas.service_desk import AssignmentRequest, BetaEnrollmentRequest, KnowledgeArticleRequest, ValidateScenarioRequest
from app.services.admin_auth import verify_admin
from app.services.service_desk_definitions import (
    ScenarioDefinitionError,
    publish_definition,
    validate_scenario_definition,
    validation_report,
)
from app.services.service_desk_engine import (
    ScenarioTransitionError,
    admin_attempt_inspection,
    reset_simulation_attempt,
)
from app.services.service_desk_features import require_service_desk_admin_enabled
from app.services.service_desk_health import run_published_scenario_health
from app.services.service_desk_lab import audit, public_article, seed_knowledge_articles
from app.utils.responses import ok


router = APIRouter(
    prefix="/api/admin/service-desk",
    tags=["admin-service-desk"],
    dependencies=[Depends(verify_admin)],
)


def _admin_definition(version: ServiceDeskScenarioVersion) -> dict:
    return {
        "id": version.id,
        "scenario_id": version.scenario_id,
        "version_number": version.version_number,
        "definition_hash": version.definition_hash,
        "validation_status": version.validation_status,
        "status": version.status,
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "published_by": version.published_by,
        "definition": version.definition_json,
        "health": run_published_scenario_health(version) if version.status == "published" else None,
    }


@router.get("/scenarios")
def list_scenarios(db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    rows = db.query(ServiceDeskScenario).order_by(ServiceDeskScenario.stable_key).all()
    result = []
    for row in rows:
        versions = (
            db.query(ServiceDeskScenarioVersion)
            .filter(ServiceDeskScenarioVersion.scenario_id == row.id)
            .order_by(ServiceDeskScenarioVersion.version_number)
            .all()
        )
        result.append({
            "id": row.id,
            "stable_key": row.stable_key,
            "title": row.title,
            "category": row.category,
            "difficulty": row.difficulty,
            "status": row.status,
            "versions": [
                {
                    "version_number": version.version_number,
                    "status": version.status,
                    "validation_status": version.validation_status,
                    "health_valid": run_published_scenario_health(version)["valid"]
                    if version.status == "published"
                    else None,
                }
                for version in versions
            ],
        })
    return ok(result)


def _safe_scenario_version_details(
    scenario: ServiceDeskScenario,
    version: ServiceDeskScenarioVersion,
) -> dict:
    """Project administrator-useful metadata without scenario answers or secrets."""
    definition = validate_scenario_definition(version.definition_json)
    health_valid = (
        run_published_scenario_health(version)["valid"]
        if version.status == "published"
        else None
    )
    supported_modes = {mode.value for mode in definition.supported_modes}
    return {
        "version": version.version_number,
        "status": version.status,
        "published": version.status == "published",
        "active": scenario.status == "active" and version.status == "published",
        "health_status": (
            "passing" if health_valid is True else "failing" if health_valid is False else "not run"
        ),
        "learning_mode_available": "learning" in supported_modes,
        "simulation_mode_available": "simulation" in supported_modes,
        "difficulty": definition.difficulty,
        "skill_tags": definition.skill_tags,
        "allowed_tools": sorted({action.tool for action in definition.actions}),
        "validation_result": {
            "status": version.validation_status,
            "valid": version.validation_status == "valid",
        },
        "metadata": {
            "category": definition.category,
            "learning_objectives": definition.learning_objectives,
            "definition_hash": version.definition_hash,
            "published_at": version.published_at.isoformat() if version.published_at else None,
            "published_by": version.published_by,
        },
    }


@router.get("/scenarios/{scenario_id}")
def get_scenario_details(scenario_id: int, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    scenario = db.query(ServiceDeskScenario).filter(ServiceDeskScenario.id == scenario_id).first()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    versions = (
        db.query(ServiceDeskScenarioVersion)
        .filter(ServiceDeskScenarioVersion.scenario_id == scenario.id)
        .order_by(ServiceDeskScenarioVersion.version_number)
        .all()
    )
    return ok({
        "id": scenario.id,
        "name": scenario.title,
        "stable_id": scenario.stable_key,
        "description": scenario.description,
        "category": scenario.category,
        "difficulty": scenario.difficulty,
        "status": scenario.status,
        "active": scenario.status == "active",
        "versions": [
            _safe_scenario_version_details(scenario, version) for version in versions
        ],
    })


@router.get("/scenarios/{scenario_id}/versions")
def list_scenario_versions(scenario_id: int, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    scenario = db.query(ServiceDeskScenario).filter(ServiceDeskScenario.id == scenario_id).first()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    versions = (
        db.query(ServiceDeskScenarioVersion)
        .filter(ServiceDeskScenarioVersion.scenario_id == scenario.id)
        .order_by(ServiceDeskScenarioVersion.version_number)
        .all()
    )
    return ok([_admin_definition(version) for version in versions])


@router.post("/scenarios/validate")
def validate_scenario(payload: ValidateScenarioRequest):
    require_service_desk_admin_enabled()
    return ok(validation_report(payload.definition))


@router.post("/scenarios/publish", status_code=201)
def publish_scenario(payload: ValidateScenarioRequest, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    try:
        version = publish_definition(db, payload.definition, published_by="admin")
        db.commit()
        db.refresh(version)
        return ok(_admin_definition(version))
    except ScenarioDefinitionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail={"code": "INVALID_SCENARIO_DEFINITION", "message": str(exc)}) from exc


@router.get("/attempts/{attempt_id}/events")
def inspect_attempt_events(attempt_id: int, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    return ok(admin_attempt_inspection(db, attempt_id))


@router.post("/attempts/{attempt_id}/reset")
def reset_attempt(attempt_id: int, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    try:
        attempt = reset_simulation_attempt(db, attempt_id)
        audit(db, actor="admin", action="attempt_reset", target_type="attempt", target_id=attempt.id)
        db.commit()
        return ok(admin_attempt_inspection(db, attempt.id))
    except ScenarioTransitionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
@router.get("/attempts")
def list_attempts(db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    rows = db.query(ServiceDeskAttempt).order_by(ServiceDeskAttempt.id.desc()).limit(200).all()
    return ok([{"id": row.id, "student_id": row.student_id, "scenario_version_id": row.scenario_version_id, "mode": row.mode, "status": row.status, "score": row.score, "passed": row.passed} for row in rows])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    versions = db.query(ServiceDeskScenarioVersion).filter(ServiceDeskScenarioVersion.status == "published").all()
    reports = [{"version_id": version.id, "stable_key": db.query(ServiceDeskScenario).filter(ServiceDeskScenario.id == version.scenario_id).one().stable_key, **run_published_scenario_health(version)} for version in versions]
    return ok({"published_count": len(reports), "valid": all(row["valid"] for row in reports), "scenarios": reports})


@router.get("/beta-enrollments")
def list_beta_enrollments(db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    rows = db.query(ServiceDeskBetaEnrollment).order_by(ServiceDeskBetaEnrollment.enrolled_at.desc()).all()
    return ok([{"id": row.id, "student_id": row.student_id, "enabled": row.enabled, "enrolled_by": row.enrolled_by, "removed_at": row.removed_at.isoformat() if row.removed_at else None, "note": row.note} for row in rows])


@router.post("/beta-enrollments", status_code=201)
def add_beta_enrollment(payload: BetaEnrollmentRequest, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    if not db.query(Student.id).filter(Student.id == payload.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    row = db.query(ServiceDeskBetaEnrollment).filter(ServiceDeskBetaEnrollment.student_id == payload.student_id).first()
    if row is None:
        row = ServiceDeskBetaEnrollment(student_id=payload.student_id, enabled=True, enrolled_by="admin", note=payload.note)
        db.add(row)
    else:
        row.enabled, row.removed_at, row.removed_by, row.note = True, None, None, payload.note
    audit(db, actor="admin", action="beta_enrolled", target_type="student", target_id=payload.student_id)
    db.commit()
    return ok({"student_id": row.student_id, "enabled": row.enabled})


@router.delete("/beta-enrollments/{student_id}")
def remove_beta_enrollment(student_id: int, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    row = db.query(ServiceDeskBetaEnrollment).filter(ServiceDeskBetaEnrollment.student_id == student_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Beta enrollment not found")
    row.enabled, row.removed_at, row.removed_by = False, datetime.now(timezone.utc), "admin"
    audit(db, actor="admin", action="beta_removed", target_type="student", target_id=student_id)
    db.commit()
    return ok({"student_id": student_id, "enabled": False})


@router.get("/assignments")
def list_assignments(db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    rows = db.query(ServiceDeskAssignment).order_by(ServiceDeskAssignment.assigned_at.desc()).all()
    return ok([{"id": row.id, "student_id": row.student_id, "scenario_id": row.scenario_id, "mode": row.mode, "is_required": row.is_required, "due_at": row.due_at.isoformat() if row.due_at else None, "maximum_attempts": row.maximum_attempts} for row in rows])


@router.post("/assignments", status_code=201)
def create_assignment(payload: AssignmentRequest, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    if not db.query(Student.id).filter(Student.id == payload.student_id).first() or not db.query(ServiceDeskScenario.id).filter(ServiceDeskScenario.id == payload.scenario_id).first():
        raise HTTPException(status_code=404, detail="Student or scenario not found")
    row = db.query(ServiceDeskAssignment).filter(ServiceDeskAssignment.student_id == payload.student_id, ServiceDeskAssignment.scenario_id == payload.scenario_id, ServiceDeskAssignment.mode == payload.mode.value).first()
    if row is None:
        row = ServiceDeskAssignment(student_id=payload.student_id, scenario_id=payload.scenario_id, mode=payload.mode.value, is_required=payload.is_required, due_at=payload.due_at, maximum_attempts=payload.maximum_attempts, assigned_by="admin")
        db.add(row)
    else:
        row.is_required, row.due_at, row.maximum_attempts = payload.is_required, payload.due_at, payload.maximum_attempts
    audit(db, actor="admin", action="assignment_saved", target_type="assignment", target_id=f"{payload.student_id}:{payload.scenario_id}:{payload.mode.value}")
    db.commit()
    return ok({"id": row.id})


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    row = db.query(ServiceDeskAssignment).filter(ServiceDeskAssignment.id == assignment_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    audit(db, actor="admin", action="assignment_removed", target_type="assignment", target_id=assignment_id)
    db.delete(row)
    db.commit()
    return ok({"removed": assignment_id})


@router.get("/knowledge")
def list_knowledge(db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    seed_knowledge_articles(db)
    db.commit()
    return ok([public_article(row) for row in db.query(ServiceDeskKnowledgeArticle).order_by(ServiceDeskKnowledgeArticle.title).all()])


@router.post("/knowledge", status_code=201)
def save_knowledge(payload: KnowledgeArticleRequest, db: Session = Depends(get_db)):
    require_service_desk_admin_enabled()
    row = db.query(ServiceDeskKnowledgeArticle).filter(ServiceDeskKnowledgeArticle.stable_id == payload.stable_id).first()
    if row is None:
        row = ServiceDeskKnowledgeArticle(**payload.model_dump())
        db.add(row)
    else:
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
    audit(db, actor="admin", action="knowledge_saved", target_type="knowledge_article", target_id=payload.stable_id)
    db.commit()
    return ok(public_article(row))
