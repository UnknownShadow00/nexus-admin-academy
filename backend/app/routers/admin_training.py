from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.training import TRAINING_ACTIVITY_TYPES, TrainingWeek, TrainingWeekActivity
from app.services.admin_auth import verify_admin
from app.services.training_service import (
    UNTRACKED_ACTIVITY_TYPES,
    validate_training_activity_reference,
    validate_training_curriculum,
)
from app.utils.responses import ok


router = APIRouter(
    prefix="/api/admin/training",
    tags=["admin-training"],
    dependencies=[Depends(verify_admin)],
)


class WeekCreate(BaseModel):
    week_number: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    learning_goals: list[str] = Field(default_factory=list)
    estimated_minutes: int | None = Field(default=None, ge=0)
    is_active: bool = True
    requires_previous_week: bool = True


class WeekPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    learning_goals: list[str] | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    requires_previous_week: bool | None = None


class ActivityCreate(BaseModel):
    stable_id: str = Field(min_length=1, max_length=160)
    activity_type: str
    content_ref: str = Field(min_length=1, max_length=160)
    is_required: bool = True
    estimated_minutes: int | None = Field(default=None, ge=0)
    prerequisite_activity_id: int | None = None
    prerequisite_mode: Literal["soft", "hard"] = "soft"
    metadata_json: dict = Field(default_factory=dict)


class ActivityPatch(BaseModel):
    is_required: bool | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    prerequisite_activity_id: int | None = None
    prerequisite_mode: Literal["soft", "hard"] | None = None
    metadata_json: dict | None = None


class ReorderItem(BaseModel):
    id: int
    display_order: int = Field(ge=0)


class ReorderPayload(BaseModel):
    items: list[ReorderItem]


def _serialize_activity(row: TrainingWeekActivity) -> dict:
    return {
        "id": row.id,
        "stable_id": row.stable_id,
        "activity_type": row.activity_type,
        "content_ref": row.content_ref,
        "display_order": row.display_order,
        "is_required": row.is_required,
        "estimated_minutes": row.estimated_minutes,
        "prerequisite_activity_id": row.prerequisite_activity_id,
        "prerequisite_mode": row.prerequisite_mode,
        "metadata_json": row.metadata_json or {},
    }


def _serialize_week(row: TrainingWeek) -> dict:
    return {
        "id": row.id,
        "week_number": row.week_number,
        "display_order": row.display_order,
        "title": row.title,
        "description": row.description,
        "learning_goals": row.learning_goals or [],
        "estimated_minutes": row.estimated_minutes,
        "is_active": row.is_active,
        "requires_previous_week": row.requires_previous_week,
        "activities": [_serialize_activity(item) for item in sorted(row.activities, key=lambda item: (item.display_order, item.id))],
    }


def _week_or_404(db: Session, week_id: int) -> TrainingWeek:
    row = db.query(TrainingWeek).filter(TrainingWeek.id == week_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Training week not found")
    return row


@router.get("/weeks")
def list_weeks(db: Session = Depends(get_db)):
    rows = db.query(TrainingWeek).options(selectinload(TrainingWeek.activities)).order_by(TrainingWeek.display_order, TrainingWeek.week_number).all()
    return ok([_serialize_week(row) for row in rows])


@router.post("/weeks", status_code=201)
def create_week(payload: WeekCreate, db: Session = Depends(get_db)):
    if db.query(TrainingWeek.id).filter(TrainingWeek.week_number == payload.week_number).first():
        raise HTTPException(status_code=409, detail="A training week with this number already exists")
    display_order = (db.query(func.max(TrainingWeek.display_order)).scalar() or 0) + 1
    row = TrainingWeek(display_order=display_order, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(_serialize_week(row))


@router.patch("/weeks/{week_id}")
def update_week(week_id: int, payload: WeekPatch, db: Session = Depends(get_db)):
    row = _week_or_404(db, week_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(_serialize_week(row))


@router.delete("/weeks/{week_id}")
def disable_week(week_id: int, db: Session = Depends(get_db)):
    row = _week_or_404(db, week_id)
    row.is_active = False
    db.commit()
    return ok({"id": row.id, "is_active": False})


@router.post("/weeks/{week_id}/activities", status_code=201)
def add_activity(week_id: int, payload: ActivityCreate, db: Session = Depends(get_db)):
    week = _week_or_404(db, week_id)
    if payload.activity_type not in TRAINING_ACTIVITY_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported activity type")
    if payload.is_required and payload.activity_type in UNTRACKED_ACTIVITY_TYPES:
        raise HTTPException(status_code=400, detail="This activity type has no verified completion record and must remain optional")
    if db.query(TrainingWeekActivity.id).filter(TrainingWeekActivity.stable_id == payload.stable_id).first():
        raise HTTPException(status_code=409, detail="An activity with this stable ID already exists")
    if payload.prerequisite_activity_id and not db.query(TrainingWeekActivity.id).filter(TrainingWeekActivity.id == payload.prerequisite_activity_id).first():
        raise HTTPException(status_code=400, detail="Prerequisite activity does not exist")
    next_order = max((item.display_order for item in week.activities), default=0) + 1
    row = TrainingWeekActivity(training_week_id=week.id, display_order=next_order, **payload.model_dump())
    db.add(row)
    db.flush()
    reference_issue = validate_training_activity_reference(db, row)
    if reference_issue and reference_issue["severity"] == "error":
        db.rollback()
        raise HTTPException(status_code=400, detail=reference_issue["message"])
    db.commit()
    db.refresh(row)
    return ok(_serialize_activity(row))


@router.patch("/activities/{activity_id}")
def update_activity(activity_id: int, payload: ActivityPatch, db: Session = Depends(get_db)):
    row = db.query(TrainingWeekActivity).filter(TrainingWeekActivity.id == activity_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Training activity not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("is_required") and row.activity_type in UNTRACKED_ACTIVITY_TYPES:
        raise HTTPException(status_code=400, detail="This activity type has no verified completion record and must remain optional")
    prerequisite_id = changes.get("prerequisite_activity_id")
    if prerequisite_id == row.id:
        raise HTTPException(status_code=400, detail="An activity cannot require itself")
    if prerequisite_id and not db.query(TrainingWeekActivity.id).filter(TrainingWeekActivity.id == prerequisite_id).first():
        raise HTTPException(status_code=400, detail="Prerequisite activity does not exist")
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(_serialize_activity(row))


@router.delete("/activities/{activity_id}")
def remove_activity(activity_id: int, db: Session = Depends(get_db)):
    row = db.query(TrainingWeekActivity).filter(TrainingWeekActivity.id == activity_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Training activity not found")
    db.delete(row)
    db.commit()
    return ok({"id": activity_id, "deleted": True})


@router.post("/weeks/reorder")
def reorder_weeks(payload: ReorderPayload, db: Session = Depends(get_db)):
    rows = {row.id: row for row in db.query(TrainingWeek).filter(TrainingWeek.id.in_([item.id for item in payload.items])).all()}
    if len(rows) != len(payload.items):
        raise HTTPException(status_code=400, detail="One or more training weeks do not exist")
    if len({item.display_order for item in payload.items}) != len(payload.items):
        raise HTTPException(status_code=400, detail="Week display orders must be unique")
    # Use temporary high values so uniqueness is preserved without violating the
    # non-negative display-order constraint.
    for index, item in enumerate(payload.items, start=1):
        rows[item.id].display_order = 1_000_000 + index
    db.flush()
    for item in payload.items:
        rows[item.id].display_order = item.display_order
    db.commit()
    return ok({"reordered": len(payload.items)})


@router.post("/activities/reorder")
def reorder_activities(payload: ReorderPayload, db: Session = Depends(get_db)):
    rows = {row.id: row for row in db.query(TrainingWeekActivity).filter(TrainingWeekActivity.id.in_([item.id for item in payload.items])).all()}
    if len(rows) != len(payload.items) or len({row.training_week_id for row in rows.values()}) > 1:
        raise HTTPException(status_code=400, detail="Activities must exist and belong to the same week")
    if len({item.display_order for item in payload.items}) != len(payload.items):
        raise HTTPException(status_code=400, detail="Activity display orders must be unique")
    for index, item in enumerate(payload.items, start=1):
        rows[item.id].display_order = 1_000_000 + index
    db.flush()
    for item in payload.items:
        rows[item.id].display_order = item.display_order
    db.commit()
    return ok({"reordered": len(payload.items)})


@router.get("/validation")
def validate_curriculum(db: Session = Depends(get_db)):
    return ok(validate_training_curriculum(db))
