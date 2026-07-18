from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.models.curriculum_video import CurriculumVideo
from app.models.student import Student
from app.models.video_watch import VideoWatch

A_PLUS_EXAM_CODES = ("220-1201", "220-1202")
A_PLUS_UNLOCK_THRESHOLD_KEY = "a_plus_unlock_threshold_pct"
DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT = 40


def get_a_plus_unlock_threshold(db: Session) -> int:
    """Read the current threshold from the database on every call."""
    row = db.query(AppSetting).filter(AppSetting.key == A_PLUS_UNLOCK_THRESHOLD_KEY).first()
    if row is None:
        return DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT
    try:
        threshold = int(row.value)
    except (TypeError, ValueError):
        return DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT
    return max(0, min(100, threshold))


def set_a_plus_unlock_threshold(db: Session, threshold: int) -> int:
    row = db.query(AppSetting).filter(AppSetting.key == A_PLUS_UNLOCK_THRESHOLD_KEY).first()
    if row is None:
        row = AppSetting(key=A_PLUS_UNLOCK_THRESHOLD_KEY, value=threshold)
        db.add(row)
    else:
        row.value = threshold
    db.commit()
    return threshold


def get_a_plus_progress(db: Session, student: Student) -> dict:
    threshold = get_a_plus_unlock_threshold(db)
    if student.is_mentor:
        return {
            "a_plus_progress_pct": 100,
            "a_plus_unlock_threshold_pct": threshold,
            "a_plus_unlocked": True,
        }

    total, watched = (
        db.query(
            func.count(func.distinct(CurriculumVideo.video_key)),
            func.count(func.distinct(VideoWatch.video_key)),
        )
        .select_from(CurriculumVideo)
        .outerjoin(
            VideoWatch,
            and_(
                VideoWatch.video_key == CurriculumVideo.video_key,
                VideoWatch.student_id == student.id,
            ),
        )
        .filter(
            CurriculumVideo.active.is_(True),
            CurriculumVideo.exam_code.in_(A_PLUS_EXAM_CODES),
        )
        .one()
    )
    total = int(total or 0)
    watched = int(watched or 0)

    # An empty A+ catalog is a deployment/configuration issue, not a student
    # failure. Keep existing hands-on behavior open until content is tagged.
    progress_pct = 100 if total == 0 else round((watched / total) * 100)
    return {
        "a_plus_progress_pct": progress_pct,
        "a_plus_unlock_threshold_pct": threshold,
        "a_plus_unlocked": progress_pct >= threshold,
    }


def require_a_plus_unlocked(db: Session, student: Student) -> dict:
    progress = get_a_plus_progress(db, student)
    if progress["a_plus_unlocked"]:
        return progress
    threshold = progress["a_plus_unlock_threshold_pct"]
    current = progress["a_plus_progress_pct"]
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"Complete {threshold}% of A+ Study Tracker to unlock hands-on work "
            f"— you're at {current}%."
        ),
    )
