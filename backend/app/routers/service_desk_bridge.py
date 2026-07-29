import hmac
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.squad_activity import SquadActivity
from app.models.student import Student
from app.models.xp_ledger import XPLedger
from app.services.activity_service import log_activity
from app.services.admin_auth import get_admin_api_key, has_valid_admin_session
from app.services.auth_service import get_current_student

router = APIRouter(prefix="/api/service-desk", tags=["service-desk-bridge"])

SERVICE_DESK_TICKET = "service_desk_ticket"
SERVICE_DESK_ACHIEVEMENT = "service_desk_achievement"
SERVICE_DESK_ACTIVITY_TYPES = (SERVICE_DESK_TICKET, SERVICE_DESK_ACHIEVEMENT)


class ServiceDeskProgressEvent(BaseModel):
    event_type: Literal["ticket_resolved", "achievement_unlocked"]
    ticket_id: str | None = Field(default=None, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    detail: str | None = Field(default=None, max_length=500)
    xp_delta: int | None = Field(
        default=None,
        ge=-(2**31),
        le=2**31 - 1,
    )


class RecentServiceDeskActivity(BaseModel):
    title: str
    detail: str | None
    created_at: str


class ServiceDeskProgressSummary(BaseModel):
    tickets_completed: int
    achievements_unlocked: int
    total_xp: int
    recent_activity: list[RecentServiceDeskActivity]


def _isoformat(value: datetime) -> str:
    return value.isoformat()


@router.post("/progress", status_code=status.HTTP_204_NO_CONTENT)
def record_service_desk_progress(
    body: ServiceDeskProgressEvent,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> Response:
    activity_type = (
        SERVICE_DESK_TICKET
        if body.event_type == "ticket_resolved"
        else SERVICE_DESK_ACHIEVEMENT
    )
    log_activity(
        db,
        current_student.id,
        activity_type,
        body.title,
        body.detail,
        commit=False,
    )
    if body.xp_delta is not None and body.xp_delta != 0:
        db.add(
            XPLedger(
                student_id=current_student.id,
                source_type="service_desk",
                source_id=None,
                delta=body.xp_delta,
                description=body.title,
            )
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/progress-summary", response_model=ServiceDeskProgressSummary)
def get_service_desk_progress_summary(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ServiceDeskProgressSummary:
    activity_counts = dict(
        db.query(SquadActivity.activity_type, func.count(SquadActivity.id))
        .filter(
            SquadActivity.student_id == current_student.id,
            SquadActivity.activity_type.in_(SERVICE_DESK_ACTIVITY_TYPES),
        )
        .group_by(SquadActivity.activity_type)
        .all()
    )
    total_xp = (
        db.query(func.coalesce(func.sum(XPLedger.delta), 0))
        .filter(
            XPLedger.student_id == current_student.id,
            XPLedger.source_type == "service_desk",
        )
        .scalar()
        or 0
    )
    recent_rows = (
        db.query(SquadActivity)
        .filter(
            SquadActivity.student_id == current_student.id,
            SquadActivity.activity_type.in_(SERVICE_DESK_ACTIVITY_TYPES),
        )
        .order_by(SquadActivity.created_at.desc(), SquadActivity.id.desc())
        .limit(5)
        .all()
    )
    return ServiceDeskProgressSummary(
        tickets_completed=int(activity_counts.get(SERVICE_DESK_TICKET, 0)),
        achievements_unlocked=int(activity_counts.get(SERVICE_DESK_ACHIEVEMENT, 0)),
        total_xp=int(total_xp),
        recent_activity=[
            RecentServiceDeskActivity(
                title=row.title,
                detail=row.detail,
                created_at=_isoformat(row.created_at),
            )
            for row in recent_rows
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
