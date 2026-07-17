from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.curriculum_video import CurriculumVideo
from app.services.admin_auth import verify_admin
from app.utils.responses import ok

router = APIRouter(
    prefix="/api/admin/curriculum",
    tags=["admin-curriculum"],
    dependencies=[Depends(verify_admin)],
)

ALLOWED_JOB_RELEVANCE = {"job_critical", "know_it", "awareness"}


class JobRelevancePatch(BaseModel):
    job_relevance: str


@router.get("/videos")
def get_curriculum_videos(db: Session = Depends(get_db)):
    rows = (
        db.query(CurriculumVideo)
        .order_by(CurriculumVideo.section_order.asc(), CurriculumVideo.video_order.asc(), CurriculumVideo.id.asc())
        .all()
    )
    return ok(
        [
            {
                "id": row.id,
                "title": row.title,
                "section": row.section,
                "job_relevance": row.job_relevance,
            }
            for row in rows
        ]
    )


@router.patch("/videos/{video_id}")
def update_curriculum_video_job_relevance(
    video_id: int,
    payload: JobRelevancePatch,
    db: Session = Depends(get_db),
):
    value = (payload.job_relevance or "").strip()
    if value not in ALLOWED_JOB_RELEVANCE:
        raise HTTPException(status_code=400, detail="job_relevance must be one of: job_critical, know_it, awareness")

    row = db.query(CurriculumVideo).filter(CurriculumVideo.id == video_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")

    row.job_relevance = value
    db.commit()
    return ok({"id": row.id, "job_relevance": row.job_relevance})
