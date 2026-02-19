from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.command_reference import CommandReference
from app.models.learning import Lesson

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/global")
def global_search(q: str = "", db: Session = Depends(get_db)):
    term = (q or "").strip()
    if not term:
        return {"success": True, "data": {"lessons": [], "commands": []}}

    like = f"%{term}%"
    lessons = (
        db.query(Lesson)
        .filter(or_(Lesson.title.ilike(like), Lesson.summary.ilike(like)))
        .order_by(Lesson.lesson_order.asc())
        .limit(10)
        .all()
    )
    commands = (
        db.query(CommandReference)
        .filter(
            or_(
                CommandReference.command.ilike(like),
                CommandReference.syntax.ilike(like),
                CommandReference.description.ilike(like),
            )
        )
        .order_by(CommandReference.command.asc())
        .limit(10)
        .all()
    )
    return {
        "success": True,
        "data": {
            "lessons": [{"id": l.id, "title": l.title, "summary": l.summary} for l in lessons],
            "commands": [
                {
                    "id": c.id,
                    "command": c.command,
                    "syntax": c.syntax,
                    "description": c.description,
                    "category": c.category,
                }
                for c in commands
            ],
        },
    }

