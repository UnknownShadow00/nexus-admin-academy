"""Minimal administrator inspection APIs for the Service Desk foundation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.schemas.service_desk import ValidateScenarioRequest
from app.services.admin_auth import verify_admin
from app.services.service_desk_definitions import (
    ScenarioDefinitionError,
    publish_definition,
    validation_report,
)
from app.services.service_desk_engine import (
    ScenarioTransitionError,
    admin_attempt_inspection,
    reset_simulation_attempt,
)
from app.services.service_desk_features import require_service_desk_admin_enabled
from app.services.service_desk_health import run_published_scenario_health
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
    return ok([
        {
            "id": row.id,
            "stable_key": row.stable_key,
            "title": row.title,
            "category": row.category,
            "difficulty": row.difficulty,
            "status": row.status,
        }
        for row in rows
    ])


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
        return ok(admin_attempt_inspection(db, reset_simulation_attempt(db, attempt_id).id))
    except ScenarioTransitionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
