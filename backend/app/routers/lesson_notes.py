from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.services.progression_service import check_module_unlock
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
    if not check_module_unlock(current_student.id, module.id, db)["unlocked"]:
        raise HTTPException(status_code=403, detail="Lesson is locked")
    return ok({
        "id": lesson.id,
        "title": lesson.title,
        "summary": lesson.summary,
        "video_url": lesson.video_url,
        "module_code": module.code,
        "module_title": module.title,
        "is_orientation": module.code == "MOD-000" and lesson.title == "Welcome to Nexus: Your First Week",
    })


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
