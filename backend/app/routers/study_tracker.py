from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.curriculum_video import CurriculumVideo
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.admin_auth import allow_admin_or_student, verify_admin
from app.services.a_plus_access import get_a_plus_progress
from app.services.auth_service import ensure_student_access, get_current_student
from app.services.quiz_visibility import student_visible_quiz_filters
from app.utils.responses import ok


def _title_key(t: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _merge_scores_with_curriculum_titles(
    scores_by_title: dict[str, dict],
    scores_by_title_key: dict[str, dict],
    curriculum_titles: list[str],
) -> dict[str, dict]:
    merged_scores = dict(scores_by_title)
    for quiz_title in curriculum_titles:
        if not quiz_title or quiz_title in merged_scores:
            continue
        fallback = scores_by_title_key.get(_title_key(quiz_title))
        if fallback:
            merged_scores[quiz_title] = fallback
    return merged_scores


router = APIRouter(prefix="/api/study-tracker", tags=["study-tracker"])


def _get_student_or_admin(auth_check: bool = Depends(allow_admin_or_student)):
    """Allow either authenticated student or admin to access."""
    return auth_check


@router.get("/curriculum")
def get_curriculum(db: Session = Depends(get_db), _: bool = Depends(_get_student_or_admin)):
    """Return all curriculum videos grouped by section."""
    videos = (
        db.query(CurriculumVideo)
        .filter(CurriculumVideo.active.is_(True))
        .order_by(CurriculumVideo.section_order, CurriculumVideo.video_order)
        .all()
    )

    mapped_rows = (
        db.query(TrainingWeekActivity)
        .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
        .filter(TrainingWeek.is_active.is_(True), TrainingWeekActivity.activity_type == "video")
        .all()
    )
    mapping_by_video_id = {
        int(row.content_ref): row.metadata_json or {}
        for row in mapped_rows
        if row.content_ref.isdigit()
    }
    mapped_quiz_ids = {
        int(metadata["quiz_id"])
        for metadata in mapping_by_video_id.values()
        if str(metadata.get("quiz_id", "")).isdigit()
    }
    quizzes = {
        row.id: row
        for row in db.query(Quiz).filter(Quiz.id.in_(mapped_quiz_ids), *student_visible_quiz_filters()).all()
    } if mapped_quiz_ids else {}

    sections = {}
    for video in videos:
        if video.section not in sections:
            sections[video.section] = {"section": video.section, "videos": []}
        mapping = mapping_by_video_id.get(video.id, {})
        quiz_id = int(mapping["quiz_id"]) if str(mapping.get("quiz_id", "")).isdigit() else None
        quiz = quizzes.get(quiz_id)
        sections[video.section]["videos"].append(
            {
                "id": video.id,
                "key": video.video_key,
                "title": video.title,
                "duration": video.duration,
                "url": video.url,
                "quiz_title": video.quiz_title,
                "quiz_id": quiz.id if quiz else None,
                "mapped_quiz_title": quiz.title if quiz else None,
                "quiz_mapping_basis": mapping.get("quiz_mapping_basis"),
                "quiz_mapping_confidence": mapping.get("quiz_mapping_confidence"),
                "exam_code": video.exam_code,
                "job_relevance": video.job_relevance,
            }
        )

    return ok(list(sections.values()))


@router.get("/curriculum/link-status")
def get_curriculum_link_status(db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    videos = (
        db.query(CurriculumVideo)
        .filter(CurriculumVideo.active.is_(True))
        .order_by(CurriculumVideo.section_order, CurriculumVideo.video_order)
        .all()
    )

    activity_rows = (
        db.query(TrainingWeekActivity)
        .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
        .filter(TrainingWeek.is_active.is_(True), TrainingWeekActivity.activity_type == "video")
        .all()
    )
    mapping_by_video_id = {
        int(row.content_ref): row.metadata_json or {}
        for row in activity_rows
        if row.content_ref.isdigit()
    }
    quiz_ids = {
        int(metadata["quiz_id"])
        for metadata in mapping_by_video_id.values()
        if str(metadata.get("quiz_id", "")).isdigit()
    }
    approved_quiz_ids = {
        row.id for row in db.query(Quiz.id).filter(Quiz.id.in_(quiz_ids), *student_visible_quiz_filters()).all()
    } if quiz_ids else set()

    data = []
    for video in videos:
        mapping = mapping_by_video_id.get(video.id, {})
        mapped_quiz_id = int(mapping["quiz_id"]) if str(mapping.get("quiz_id", "")).isdigit() else None
        matched_quiz_id = mapped_quiz_id if mapped_quiz_id in approved_quiz_ids else None
        data.append(
            {
                "id": video.id,
                "title": video.title,
                "quiz_title": video.quiz_title,
                "linked": matched_quiz_id is not None,
                "quiz_id": matched_quiz_id,
                "mapping_basis": mapping.get("quiz_mapping_basis"),
                "mapping_confidence": mapping.get("quiz_mapping_confidence"),
            }
        )

    return ok(data)


@router.get("/{student_id}")
def get_study_tracker(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    """Return watched video keys and best quiz scores for this student."""
    ensure_student_access(current_student, student_id)
    watches = db.query(VideoWatch).filter(VideoWatch.student_id == student_id).all()
    watched = {watch.video_key: watch.watched_at.isoformat() for watch in watches}

    attempts = (
        db.query(QuizAttempt, Quiz)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .filter(QuizAttempt.student_id == student_id, Quiz.status == QUIZ_STATUS_PUBLISHED)
        .all()
    )
    scores_by_title = {}
    scores_by_title_key = {}
    scores_by_quiz_id = {}
    for attempt, quiz in attempts:
        qcount = quiz.question_count or len(quiz.questions) or 10
        pct = round((attempt.best_score / qcount) * 100) if attempt.best_score is not None else None
        existing = scores_by_title.get(quiz.title, {})
        if pct is not None and pct > (existing.get("pct") or -1):
            entry = {
                "score": attempt.best_score,
                "total": qcount,
                "pct": pct,
                "quiz_id": attempt.quiz_id,
            }
            scores_by_title[quiz.title] = entry
            scores_by_title_key[_title_key(quiz.title)] = entry
            scores_by_quiz_id[str(quiz.id)] = entry

    curriculum_rows = (
        db.query(CurriculumVideo.quiz_title)
        .filter(
            CurriculumVideo.active.is_(True),
            CurriculumVideo.quiz_title.isnot(None),
            CurriculumVideo.quiz_title != "",
        )
        .all()
    )
    curriculum_titles = [row.quiz_title for row in curriculum_rows]
    merged_scores = _merge_scores_with_curriculum_titles(scores_by_title, scores_by_title_key, curriculum_titles)

    return ok({"watched": watched, "scores": merged_scores, "quiz_scores": scores_by_quiz_id})


@router.post("/{student_id}/watch/{video_key:path}")
def mark_watched(student_id: int, video_key: str, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    exists = (
        db.query(VideoWatch)
        .filter(VideoWatch.student_id == student_id, VideoWatch.video_key == video_key)
        .first()
    )
    if not exists:
        db.add(VideoWatch(student_id=student_id, video_key=video_key))
        db.commit()
    return ok({"watched": True, **get_a_plus_progress(db, current_student)})


@router.delete("/{student_id}/watch/{video_key:path}")
def unmark_watched(student_id: int, video_key: str, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    db.query(VideoWatch).filter(
        VideoWatch.student_id == student_id,
        VideoWatch.video_key == video_key,
    ).delete()
    db.commit()
    return ok({"watched": False, **get_a_plus_progress(db, current_student)})


class VideoUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    quiz_title: str | None = None
    duration: str | None = None
    active: bool | None = None


@router.patch("/curriculum/{video_id}")
def update_curriculum_video(video_id: int, body: VideoUpdate, db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    """Admin: edit a video's title, URL, or linked quiz."""
    video = db.query(CurriculumVideo).filter(CurriculumVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if body.title is not None:
        video.title = body.title
    if body.url is not None:
        video.url = body.url
    if body.quiz_title is not None:
        video.quiz_title = body.quiz_title
    if body.duration is not None:
        video.duration = body.duration
    if body.active is not None:
        video.active = body.active
    db.commit()
    return ok(
        {
            "id": video.id,
            "title": video.title,
            "url": video.url,
            "quiz_title": video.quiz_title,
            "job_relevance": video.job_relevance,
        }
    )
