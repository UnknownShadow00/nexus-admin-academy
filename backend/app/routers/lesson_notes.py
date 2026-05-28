from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.learning import Lesson
from app.models.lesson_notes import StudentLessonNote
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.utils.responses import ok

router = APIRouter(tags=["lesson-notes"])


class LessonNoteRequest(BaseModel):
    content: str = Field(default="", max_length=20000)


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
