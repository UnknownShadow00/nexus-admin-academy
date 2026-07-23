"""Student APIs for the disabled-by-default Service Desk foundation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service_desk import ServiceDeskKnowledgeArticle, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.student import Student
from app.schemas.service_desk import AttemptActionRequest, StartAttemptRequest
from app.services.auth_service import get_current_student
from app.services.service_desk_engine import (
    ScenarioTransitionError,
    apply_attempt_action,
    get_owned_attempt,
    start_attempt,
    student_projection,
)
from app.services.service_desk_features import require_service_desk_student_access, service_desk_student_enabled, student_has_service_desk_beta_access
from app.services.service_desk_definitions import published_definition
from app.services.service_desk_lab import overview, performance, public_article, queue
from app.utils.responses import ok


router = APIRouter(prefix="/api/service-desk", tags=["service-desk"])


def _raise_transition(error: ScenarioTransitionError):
    raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message})


@router.get("/access")
def service_desk_access(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    """A safe navigation capability probe; all workspace endpoints remain gated."""
    return ok({"available": service_desk_student_enabled() and student_has_service_desk_beta_access(db, current_student)})


@router.get("/overview")
def get_overview(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    require_service_desk_student_access(db, current_student)
    return ok(overview(db, current_student))


@router.get("/queue")
def get_queue(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    require_service_desk_student_access(db, current_student)
    return ok(queue(db, current_student))


@router.get("/performance")
def get_performance(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    require_service_desk_student_access(db, current_student)
    return ok(performance(db, current_student))


@router.get("/knowledge")
def search_knowledge(q: str = "", db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    require_service_desk_student_access(db, current_student)
    query = db.query(ServiceDeskKnowledgeArticle).filter(ServiceDeskKnowledgeArticle.status == "published")
    if q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter((ServiceDeskKnowledgeArticle.title.ilike(pattern)) | (ServiceDeskKnowledgeArticle.content.ilike(pattern)))
    return ok([public_article(row) for row in query.order_by(ServiceDeskKnowledgeArticle.title).all()])


@router.get("/knowledge/{article_id}")
def get_knowledge(article_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    require_service_desk_student_access(db, current_student)
    article = db.query(ServiceDeskKnowledgeArticle).filter(ServiceDeskKnowledgeArticle.id == article_id, ServiceDeskKnowledgeArticle.status == "published").first()
    if article is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found")
    return ok(public_article(article))


@router.get("/scenarios")
def list_scenarios(
    db: Session = Depends(get_db),
    _: Student = Depends(get_current_student),
):
    require_service_desk_student_access(db, _)
    rows = (
        db.query(ServiceDeskScenario, ServiceDeskScenarioVersion)
        .join(ServiceDeskScenarioVersion, ServiceDeskScenarioVersion.scenario_id == ServiceDeskScenario.id)
        .filter(
            ServiceDeskScenario.status == "active",
            ServiceDeskScenarioVersion.status == "published",
            ServiceDeskScenarioVersion.validation_status == "valid",
        )
        .order_by(ServiceDeskScenario.stable_key, ServiceDeskScenarioVersion.version_number.desc())
        .all()
    )
    latest: dict[int, tuple[ServiceDeskScenario, ServiceDeskScenarioVersion]] = {}
    for scenario, version in rows:
        latest.setdefault(scenario.id, (scenario, version))
    return ok([
        {
            "id": scenario.id,
            "stable_key": scenario.stable_key,
            "title": scenario.title,
            "description": scenario.description,
            "category": scenario.category,
            "difficulty": scenario.difficulty,
            "supported_modes": sorted(mode.value for mode in published_definition(version).supported_modes),
        }
        for scenario, version in latest.values()
    ])


@router.post("/scenarios/{scenario_id}/attempts", status_code=201)
def create_attempt(
    scenario_id: int,
    payload: StartAttemptRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    try:
        attempt = start_attempt(db, current_student, scenario_id, payload.mode)
        _, definition = get_owned_attempt(db, current_student, attempt.id)
        return ok(student_projection(db, attempt, definition))
    except ScenarioTransitionError as exc:
        _raise_transition(exc)


@router.get("/attempts/{attempt_id}")
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    attempt, definition = get_owned_attempt(db, current_student, attempt_id)
    return ok(student_projection(db, attempt, definition))


@router.post("/attempts/{attempt_id}/actions")
def post_attempt_action(
    attempt_id: int,
    payload: AttemptActionRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    try:
        attempt, outcome, idempotent = apply_attempt_action(db, current_student, attempt_id, payload)
        _, definition = get_owned_attempt(db, current_student, attempt.id)
        return ok({
            "idempotent": idempotent,
            "action_success": outcome.success,
            "feedback": outcome.feedback,
            "attempt": student_projection(db, attempt, definition),
        })
    except ScenarioTransitionError as exc:
        _raise_transition(exc)


@router.get("/attempts/{attempt_id}/result")
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    attempt, definition = get_owned_attempt(db, current_student, attempt_id)
    projection = student_projection(db, attempt, definition)
    return ok({"id": attempt.id, "status": attempt.status, "result": projection["result"]})
