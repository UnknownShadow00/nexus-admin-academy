from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import Quiz
from app.models.student import Student
from app.models.training import TrainingWeekActivity
from app.services.auth_service import get_current_student
from app.services.curriculum_structure import module_for_week
from app.services.lesson_presentation import (
    learner_outcomes,
    learner_summary,
    presentation_for_lesson,
)
from app.services.progression_service import MODULE_WEEKS, require_week_reached
from app.utils.responses import ok

router = APIRouter(tags=["lesson-notes"])


class LessonNoteRequest(BaseModel):
    content: str = Field(default="", max_length=20000)
    base_content: str | None = Field(default=None, max_length=20000)


@router.get("/api/lessons/{lesson_id}")
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    row = (
        db.query(Lesson, Module)
        .join(Module, Module.id == Lesson.module_id)
        .filter(
            Lesson.id == lesson_id,
            Lesson.status == "published",
            Module.active.is_(True),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson, module = row
    if module.code in MODULE_WEEKS:
        require_week_reached(db, current_student, MODULE_WEEKS[module.code])
    progress = (
        db.query(StudentLessonProgress)
        .filter(
            StudentLessonProgress.student_id == current_student.id,
            StudentLessonProgress.lesson_id == lesson.id,
        )
        .first()
    )
    if progress is None:
        progress = StudentLessonProgress(
            student_id=current_student.id, lesson_id=lesson.id
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    raw_outcomes = lesson.outcomes or []
    outcomes = (
        [
            outcome.strip()
            for outcome in raw_outcomes
            if isinstance(outcome, str) and outcome.strip()
        ]
        if isinstance(raw_outcomes, list)
        else []
    )
    outcomes = learner_outcomes(lesson.title, outcomes)
    related_activity_type = None
    related_training_module = None
    if lesson.related_activity_stable_id:
        related_activity_type = (
            db.query(TrainingWeekActivity.activity_type)
            .filter(TrainingWeekActivity.stable_id == lesson.related_activity_stable_id)
            .scalar()
        )
        related_training_module = module_for_week(MODULE_WEEKS.get(module.code, -1))
    current_week_activity = (
        db.query(TrainingWeekActivity)
        .filter(
            TrainingWeekActivity.activity_type == "lesson",
            TrainingWeekActivity.content_ref == str(lesson.id),
        )
        .first()
    )
    next_activity = None
    if current_week_activity:
        next_row = (
            db.query(TrainingWeekActivity)
            .filter(
                TrainingWeekActivity.training_week_id
                == current_week_activity.training_week_id,
                TrainingWeekActivity.display_order
                > current_week_activity.display_order,
                TrainingWeekActivity.is_required.is_(True),
            )
            .order_by(TrainingWeekActivity.display_order.asc())
            .first()
        )
        if next_row and next_row.activity_type == "lesson":
            next_lesson = db.get(Lesson, int(next_row.content_ref))
            if next_lesson and next_lesson.status == "published":
                next_activity = {
                    "type": "lesson",
                    "title": next_lesson.title,
                    "route": f"/lessons/{next_lesson.id}",
                }
        elif next_row and next_row.activity_type == "quiz":
            next_quiz = db.get(Quiz, int(next_row.content_ref))
            if next_quiz:
                next_activity = {
                    "type": "quiz",
                    "title": next_quiz.title,
                    "route": f"/quizzes/{next_quiz.id}",
                }
    if next_activity is None:
        next_lesson = (
            db.query(Lesson)
            .filter(
                Lesson.module_id == module.id,
                Lesson.status == "published",
                Lesson.lesson_order > lesson.lesson_order,
            )
            .order_by(Lesson.lesson_order.asc())
            .first()
        )
        if next_lesson:
            next_activity = {
                "type": "lesson",
                "title": next_lesson.title,
                "route": f"/lessons/{next_lesson.id}",
            }
    return ok(
        {
            "id": lesson.id,
            "title": lesson.title,
            "summary": learner_summary(lesson.title, lesson.summary),
            "outcomes": outcomes,
            "video_url": lesson.video_url,
            "module_code": module.code,
            "module_title": module.title,
            "related_activity_stable_id": lesson.related_activity_stable_id,
            "related_activity_week_number": MODULE_WEEKS.get(module.code)
            if lesson.related_activity_stable_id
            else None,
            "related_training_module_id": related_training_module.stable_id
            if related_training_module
            else None,
            "related_activity_type": related_activity_type,
            "is_orientation": module.code == "MOD-000"
            and lesson.title == "Welcome to Nexus: Your First Week",
            "is_complete": progress.completed_at is not None,
            "presentation": presentation_for_lesson(lesson.title),
            "next_activity": next_activity,
        }
    )


@router.post("/api/lessons/{lesson_id}/complete")
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    row = (
        db.query(Lesson, Module)
        .join(Module, Module.id == Lesson.module_id)
        .filter(
            Lesson.id == lesson_id,
            Lesson.status == "published",
            Module.active.is_(True),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson, module = row
    if module.code in MODULE_WEEKS:
        require_week_reached(db, current_student, MODULE_WEEKS[module.code])
    progress = (
        db.query(StudentLessonProgress)
        .filter(
            StudentLessonProgress.student_id == current_student.id,
            StudentLessonProgress.lesson_id == lesson.id,
        )
        .first()
    )
    if progress is None:
        raise HTTPException(
            status_code=409, detail="Open the lesson before marking it complete"
        )
    if progress.completed_at is None:
        progress.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(progress)
    return ok(
        {
            "lesson_id": lesson.id,
            "is_complete": True,
            "completed_at": progress.completed_at,
        }
    )


@router.get("/api/lessons/{lesson_id}/notes")
def get_lesson_note(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    note = (
        db.query(StudentLessonNote)
        .filter(
            StudentLessonNote.student_id == current_student.id,
            StudentLessonNote.lesson_id == lesson_id,
        )
        .first()
    )
    return ok(
        {
            "note_id": note.id if note else None,
            "content": note.content if note else "",
            "updated_at": note.updated_at if note else None,
        }
    )


@router.put("/api/lessons/{lesson_id}/notes")
def save_lesson_note(
    lesson_id: int,
    payload: LessonNoteRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    note = (
        db.query(StudentLessonNote)
        .filter(
            StudentLessonNote.student_id == current_student.id,
            StudentLessonNote.lesson_id == lesson_id,
        )
        .first()
    )
    if note is None:
        note = StudentLessonNote(
            student_id=current_student.id, lesson_id=lesson_id, content=payload.content
        )
        db.add(note)
    else:
        if (
            payload.base_content is not None
            and (note.content or "") != payload.base_content
        ):
            raise HTTPException(
                status_code=409,
                detail="This note changed in another session. Reload before retrying so newer work is not overwritten.",
            )
        note.content = payload.content

    db.commit()
    db.refresh(note)
    return ok(
        {
            "note_id": note.id,
            "content": note.content or "",
            "updated_at": note.updated_at,
        }
    )
