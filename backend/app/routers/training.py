from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.curriculum_video import CurriculumVideo
from app.models.training import TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.auth_service import get_current_student
from app.services.training_service import (
    build_training_overview,
    build_training_progress,
    build_training_week,
)
from app.utils.responses import ok


router = APIRouter(prefix="/api/training", tags=["training"])


@router.get("")
def get_training_dashboard(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    return ok(build_training_overview(db, current_student))


@router.get("/weeks")
def list_training_weeks(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    return ok(build_training_overview(db, current_student)["weeks"])


@router.get("/weeks/{week_number}")
def get_training_week(
    week_number: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    week = build_training_week(db, current_student, week_number)
    if week is None:
        raise HTTPException(status_code=404, detail="Training week not found")
    if week["locked"] and not current_student.is_mentor:
        raise HTTPException(status_code=403, detail=week["lock_reason"] or "Training week is locked")
    return ok(week)


@router.get("/next-activity")
def get_next_training_activity(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    overview = build_training_overview(db, current_student)
    return ok(
        {
            "current_week": overview["current_week"],
            "next_activity": overview["next_activity"],
            "training_complete": overview["training_complete"],
        }
    )


@router.get("/progress")
def get_training_progress(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    return ok(build_training_progress(db, current_student))


@router.post("/activities/{activity_id}/video-watch")
def mark_training_video_watched(
    activity_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    activity = db.query(TrainingWeekActivity).filter(TrainingWeekActivity.id == activity_id).first()
    if activity is None or activity.activity_type != "video":
        raise HTTPException(status_code=404, detail="Training video activity not found")
    week = build_training_week(db, current_student, activity.week.week_number)
    if week is None or (week["locked"] and not current_student.is_mentor):
        raise HTTPException(status_code=403, detail="Training week is locked")
    try:
        video_id = int(activity.content_ref)
    except ValueError:
        raise HTTPException(status_code=400, detail="Training video reference is invalid") from None
    video = db.query(CurriculumVideo).filter(CurriculumVideo.id == video_id, CurriculumVideo.active.is_(True)).first()
    if video is None:
        raise HTTPException(status_code=404, detail="Training video not found")
    watch = db.query(VideoWatch).filter(VideoWatch.student_id == current_student.id, VideoWatch.video_key == video.video_key).first()
    if watch is None:
        db.add(VideoWatch(student_id=current_student.id, video_key=video.video_key))
        db.commit()
    return ok({"activity_id": activity.id, "watched": True})
