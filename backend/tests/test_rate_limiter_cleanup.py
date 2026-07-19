from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.ai_rate_limit import AIRateLimit
from app.services import rate_limiter


def _row(db, *, when, endpoint="ticket_grading"):
    row = AIRateLimit(user_id=1, endpoint=endpoint, window_start=when, call_count=1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_prune_removes_expired_rows_and_keeps_active_rows(db):
    now = datetime.now(timezone.utc)
    expired = _row(db, when=now - timedelta(days=8))
    active = _row(db, when=now - timedelta(minutes=1))
    expired_id = expired.id
    active_id = active.id

    deleted = rate_limiter.prune_old_rate_limits(db, now=now, force=True)

    assert deleted == 1
    assert db.query(AIRateLimit).filter(AIRateLimit.id == expired_id).count() == 0
    assert db.query(AIRateLimit).filter(AIRateLimit.id == active_id).count() == 1


def test_cleanup_is_throttled_between_intervals(db, monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(rate_limiter, "_last_cleanup_monotonic", 0.0)
    rate_limiter.prune_old_rate_limits(db, now=now)
    expired = _row(db, when=now - timedelta(days=8))

    deleted = rate_limiter.prune_old_rate_limits(db, now=now)

    assert deleted == 0
    assert db.get(AIRateLimit, expired.id) is not None


def test_active_rate_limit_calculation_still_blocks(db, monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(rate_limiter, "_last_cleanup_monotonic", 0.0)
    for seconds in (10, 20, 30):
        _row(db, when=now - timedelta(seconds=seconds))

    with pytest.raises(HTTPException) as exc_info:
        rate_limiter.check_rate_limit(1, "ticket_grading", db)

    assert exc_info.value.status_code == 429
