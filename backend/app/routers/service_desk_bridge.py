import hmac
import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptGrade,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.models.xp_ledger import XPLedger
from app.services.admin_auth import get_admin_api_key, has_valid_admin_session
from app.services.auth_service import STUDENT_SESSION_COOKIE, decode_token, get_current_student

router = APIRouter(prefix="/api/service-desk", tags=["service-desk-bridge"])

logger = logging.getLogger(__name__)


class ServiceDeskProgressEvent(BaseModel):
    event_type: Literal["ticket_resolved", "achievement_unlocked"]
    ticket_id: str | None = Field(default=None, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = Field(default=None, max_length=500)


class RecentServiceDeskActivity(BaseModel):
    title: str
    detail: str | None
    created_at: str


class ServiceDeskSkillCount(BaseModel):
    name: str
    completed: int


class ServiceDeskProgressSummary(BaseModel):
    tickets_completed: int
    passed_first_try: int
    needed_revision: int
    achievements_unlocked: int
    total_xp: int
    skills: list[ServiceDeskSkillCount]
    needs_practice: list[str]
    recent_activity: list[RecentServiceDeskActivity]


def _isoformat(value: datetime) -> str:
    return value.isoformat()


@router.post("/progress", status_code=status.HTTP_204_NO_CONTENT)
def record_service_desk_progress(
    body: ServiceDeskProgressEvent,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> Response:
    """Compatibility no-op for pre-authoritative simulator clients.

    The payload is browser-authored and has no trusted attempt, event, or
    grade reference. It therefore cannot create progress or XP. Current
    clients use the attempt action/completion endpoints for authoritative
    grading; keeping this as 204 avoids crashing older browser bundles.
    """
    logger.info(
        "ignored_untrusted_service_desk_progress student_id=%s event_type=%s ticket_id=%s",
        current_student.id,
        body.event_type,
        body.ticket_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/progress-summary", response_model=ServiceDeskProgressSummary)
def get_service_desk_progress_summary(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ServiceDeskProgressSummary:
    completed_rows = (
        db.query(ServiceDeskAttemptGrade, ServiceDeskScenario)
        .join(
            ServiceDeskAttempt,
            ServiceDeskAttempt.id == ServiceDeskAttemptGrade.attempt_id,
        )
        .join(
            ServiceDeskScenarioVersion,
            ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id,
        )
        .join(
            ServiceDeskScenario,
            ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id,
        )
        .filter(
            ServiceDeskAttempt.student_id == current_student.id,
            ServiceDeskAttemptGrade.passed.is_(True),
        )
        .order_by(
            ServiceDeskAttemptGrade.calculated_at.desc(),
            ServiceDeskAttemptGrade.id.desc(),
        )
        .all()
    )
    attempt_rows = (
        db.query(ServiceDeskAttempt, ServiceDeskScenario)
        .join(
            ServiceDeskScenarioVersion,
            ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id,
        )
        .join(
            ServiceDeskScenario,
            ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id,
        )
        .filter(ServiceDeskAttempt.student_id == current_student.id)
        .order_by(ServiceDeskAttempt.started_at, ServiceDeskAttempt.id)
        .all()
    )
    attempts_by_scenario: dict[
        str, list[tuple[ServiceDeskAttempt, ServiceDeskScenario]]
    ] = {}
    for attempt, scenario in attempt_rows:
        attempts_by_scenario.setdefault(scenario.stable_key, []).append(
            (attempt, scenario)
        )
    passed_scenarios = {
        key
        for key, rows in attempts_by_scenario.items()
        if any(attempt.passed is True for attempt, _ in rows)
    }
    passed_first_try = sum(
        bool(rows and rows[0][0].passed is True)
        for key, rows in attempts_by_scenario.items()
        if key in passed_scenarios
    )
    skill_names = {
        "access": "Accounts & Access",
        "hardware": "Desktop & Hardware",
        "network": "Networking",
        "software": "Windows & Applications",
    }
    skill_counts: dict[str, int] = {}
    for key in passed_scenarios:
        scenario = attempts_by_scenario[key][0][1]
        name = skill_names.get(scenario.category.lower(), scenario.category.title())
        skill_counts[name] = skill_counts.get(name, 0) + 1
    recent_unique = []
    recent_seen = set()
    for grade, scenario in completed_rows:
        if scenario.stable_key in recent_seen:
            continue
        recent_seen.add(scenario.stable_key)
        recent_unique.append((grade, scenario))
    total_xp = (
        db.query(func.coalesce(func.sum(XPLedger.delta), 0))
        .filter(
            XPLedger.student_id == current_student.id,
            XPLedger.source_type == "service_desk_attempt",
        )
        .scalar()
        or 0
    )
    return ServiceDeskProgressSummary(
        tickets_completed=len(passed_scenarios),
        passed_first_try=passed_first_try,
        needed_revision=len(passed_scenarios) - passed_first_try,
        achievements_unlocked=0,
        total_xp=int(total_xp),
        skills=[
            ServiceDeskSkillCount(name=name, completed=count)
            for name, count in sorted(skill_counts.items())
        ],
        needs_practice=[
            rows[0][1].title
            for key, rows in attempts_by_scenario.items()
            if key not in passed_scenarios
            and any(attempt.status == "failed" for attempt, _ in rows)
        ],
        recent_activity=[
            RecentServiceDeskActivity(
                title=scenario.title,
                detail=f"Passed with {grade.overall_score} points",
                created_at=_isoformat(grade.calculated_at),
            )
            for grade, scenario in recent_unique[:5]
        ],
    )


@router.get("/admin-check")
def get_service_desk_admin_check(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict[str, bool]:
    is_admin = has_valid_admin_session(request)
    if not is_admin and x_admin_key:
        expected_api_key = get_admin_api_key()
        is_admin = bool(expected_api_key) and hmac.compare_digest(
            x_admin_key.strip(),
            expected_api_key,
        )
    return {"is_admin": is_admin}


@router.get("/admin-authorize", status_code=status.HTTP_204_NO_CONTENT)
def authorize_service_desk_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Authorize the nginx auth subrequest for simulator builder routes."""
    if has_valid_admin_session(request):
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    token = request.cookies.get(STUDENT_SESSION_COOKIE)
    if token:
        try:
            payload = decode_token(token)
            student_id = int(payload["sub"])
        except (HTTPException, KeyError, TypeError, ValueError):
            student_id = None

        if student_id is not None:
            mentor = (
                db.query(Student)
                .filter(Student.id == student_id, Student.is_mentor.is_(True))
                .first()
            )
            if mentor:
                return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
