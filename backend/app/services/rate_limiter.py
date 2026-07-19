import os
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_rate_limit import AIRateLimit

RATE_LIMITS = {
    "quiz_generation": {"per_hour": 2, "per_day": 5},
    "ticket_grading": {"per_minute": 3, "per_day": 8},
    "ticket_description": {"per_hour": 2, "per_day": 10},
}
RATE_LIMIT_RETENTION_DAYS = int(os.getenv("AI_RATE_LIMIT_RETENTION_DAYS", "7"))
RATE_LIMIT_CLEANUP_INTERVAL_SECONDS = int(os.getenv("AI_RATE_LIMIT_CLEANUP_INTERVAL_SECONDS", "3600"))
RATE_LIMIT_CLEANUP_BATCH_SIZE = int(os.getenv("AI_RATE_LIMIT_CLEANUP_BATCH_SIZE", "1000"))
_cleanup_lock = threading.Lock()
_last_cleanup_monotonic = 0.0


def prune_old_rate_limits(
    db: Session,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> int:
    """Delete one bounded batch of expired counters at most once per interval."""
    global _last_cleanup_monotonic

    monotonic_now = time.monotonic()
    if not force and monotonic_now - _last_cleanup_monotonic < RATE_LIMIT_CLEANUP_INTERVAL_SECONDS:
        return 0

    with _cleanup_lock:
        monotonic_now = time.monotonic()
        if not force and monotonic_now - _last_cleanup_monotonic < RATE_LIMIT_CLEANUP_INTERVAL_SECONDS:
            return 0
        _last_cleanup_monotonic = monotonic_now

        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=RATE_LIMIT_RETENTION_DAYS)
        expired_ids = [
            row.id
            for row in (
                db.query(AIRateLimit.id)
                .filter(AIRateLimit.window_start < cutoff)
                .order_by(AIRateLimit.window_start.asc())
                .limit(RATE_LIMIT_CLEANUP_BATCH_SIZE)
                .all()
            )
        ]
        if not expired_ids:
            return 0
        deleted = (
            db.query(AIRateLimit)
            .filter(AIRateLimit.id.in_(expired_ids))
            .delete(synchronize_session=False)
        )
        db.commit()
        return int(deleted or 0)


def check_rate_limit(user_id: int, endpoint: str, db: Session) -> None:
    limits = RATE_LIMITS.get(endpoint)
    if not limits:
        return

    now = datetime.now(timezone.utc)
    user_id = int(user_id or 0)
    prune_old_rate_limits(db, now=now)

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
