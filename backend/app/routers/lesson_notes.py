from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.lesson_progress import StudentLessonProgress
from app.models.student import Student
from app.models.training import TrainingWeekActivity
from app.services.auth_service import get_current_student
from app.services.progression_service import MODULE_WEEKS, require_week_reached
from app.utils.responses import ok

router = APIRouter(tags=["lesson-notes"])


class LessonNoteRequest(BaseModel):
    content: str = Field(default="", max_length=20000)


@router.get("/api/lessons/{lesson_id}")
def get_lesson(lesson_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    row = (
        db.query(Lesson, Module)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Lesson.id == lesson_id, Lesson.status == "published", Module.active.is_(True))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson, module = row
    if module.code in MODULE_WEEKS:
        require_week_reached(db, current_student, MODULE_WEEKS[module.code])
    progress = (
        db.query(StudentLessonProgress)
        .filter(StudentLessonProgress.student_id == current_student.id, StudentLessonProgress.lesson_id == lesson.id)
        .first()
    )
    if progress is None:
        progress = StudentLessonProgress(student_id=current_student.id, lesson_id=lesson.id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    raw_outcomes = lesson.outcomes or []
    outcomes = (
        [outcome.strip() for outcome in raw_outcomes if isinstance(outcome, str) and outcome.strip()]
        if isinstance(raw_outcomes, list)
        else []
    )
    related_activity_type = None
    if lesson.related_activity_stable_id:
        related_activity_type = (
            db.query(TrainingWeekActivity.activity_type)
            .filter(TrainingWeekActivity.stable_id == lesson.related_activity_stable_id)
            .scalar()
        )
    return ok({
        "id": lesson.id,
        "title": lesson.title,
        "summary": lesson.summary,
        "outcomes": outcomes,
        "video_url": lesson.video_url,
        "module_code": module.code,
        "module_title": module.title,
        "related_activity_stable_id": lesson.related_activity_stable_id,
        "related_activity_week_number": MODULE_WEEKS.get(module.code) if lesson.related_activity_stable_id else None,
        "related_activity_type": related_activity_type,
        "is_orientation": module.code == "MOD-000" and lesson.title == "Welcome to Nexus: Your First Week",
        "is_complete": progress.completed_at is not None,
    })


@router.post("/api/lessons/{lesson_id}/complete")
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    row = (
        db.query(Lesson, Module)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Lesson.id == lesson_id, Lesson.status == "published", Module.active.is_(True))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson, module = row
    if module.code in MODULE_WEEKS:
        require_week_reached(db, current_student, MODULE_WEEKS[module.code])
    progress = (
        db.query(StudentLessonProgress)
        .filter(StudentLessonProgress.student_id == current_student.id, StudentLessonProgress.lesson_id == lesson.id)
        .first()
    )
    if progress is None:
        raise HTTPException(status_code=409, detail="Open the lesson before marking it complete")
    if progress.completed_at is None:
        progress.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(progress)
    return ok({"lesson_id": lesson.id, "is_complete": True, "completed_at": progress.completed_at})


@router.get("/api/lessons/{lesson_id}/notes")
def get_lesson_note(lesson_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    note = (
        db.query(StudentLessonNote)
        .filter(StudentLessonNote.student_id == current_student.id, StudentLessonNote.lesson_id == lesson_id)
        .first()
    )
    return ok({"note_id": note.id if note else None, "content": note.content if note else ""})


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
        .filter(StudentLessonNote.student_id == current_student.id, StudentLessonNote.lesson_id == lesson_id)
        .first()
    )
    if note is None:
        note = StudentLessonNote(student_id=current_student.id, lesson_id=lesson_id, content=payload.content)
        db.add(note)
    else:
        note.content = payload.content

    db.commit()
    db.refresh(note)
    return ok({"note_id": note.id, "content": note.content or ""})
