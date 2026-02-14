from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_rate_limit import AIRateLimit

RATE_LIMITS = {
    "quiz_generation": {"per_hour": 2, "per_day": 5},
    "ticket_grading": {"per_minute": 3, "per_day": 8},
    "ticket_description": {"per_hour": 2, "per_day": 10},
}


def check_rate_limit(user_id: int, endpoint: str, db: Session) -> None:
    limits = RATE_LIMITS.get(endpoint)
    if not limits:
        return

    now = datetime.utcnow()
    user_id = int(user_id or 0)

    if "per_minute" in limits:
        minute_count = (
            db.query(func.count(AIRateLimit.id))
            .filter(
                AIRateLimit.user_id == user_id,
                AIRateLimit.endpoint == endpoint,
                AIRateLimit.window_start > now - timedelta(minutes=1),
            )
            .scalar()
            or 0
        )
        if minute_count >= limits["per_minute"]:
            raise HTTPException(status_code=429, detail=f"Rate limit: Max {limits['per_minute']} calls per minute")

    if "per_hour" in limits:
        hour_count = (
            db.query(func.count(AIRateLimit.id))
            .filter(
                AIRateLimit.user_id == user_id,
                AIRateLimit.endpoint == endpoint,
                AIRateLimit.window_start > now - timedelta(hours=1),
            )
            .scalar()
            or 0
        )
        if hour_count >= limits["per_hour"]:
            raise HTTPException(status_code=429, detail=f"Rate limit: Max {limits['per_hour']} calls per hour")

    if "per_day" in limits:
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_count = (
            db.query(func.count(AIRateLimit.id))
            .filter(
                AIRateLimit.user_id == user_id,
                AIRateLimit.endpoint == endpoint,
                AIRateLimit.window_start >= day_start,
            )
            .scalar()
            or 0
        )
        if day_count >= limits["per_day"]:
            raise HTTPException(status_code=429, detail=f"Rate limit: Max {limits['per_day']} calls per day")

    db.add(AIRateLimit(user_id=user_id, endpoint=endpoint, call_count=1, window_start=now))
    db.commit()
