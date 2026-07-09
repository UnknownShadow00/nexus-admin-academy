from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.command_reference import CommandReference
from app.models.student import Student
from app.services.auth_service import get_current_student

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.get("/search")
def search_commands(q: str = "", db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    query = db.query(CommandReference)
    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(or_(CommandReference.command.ilike(like), CommandReference.description.ilike(like)))
    rows = query.order_by(CommandReference.command.asc()).limit(25).all()

    return {
        "success": True,
        "commands": [
            {
                "id": row.id,
                "command": row.command,
                "description": row.description,
                "syntax": row.syntax,
                "example": row.example,
                "category": row.category or "general",
                "os": row.os,
            }
            for row in rows
        ],
    }


@router.get("")
def list_commands(
    search: str = "",
    category: str = "",
    os: str = "",
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    query = db.query(CommandReference)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                CommandReference.command.ilike(like),
                CommandReference.description.ilike(like),
                CommandReference.syntax.ilike(like),
                CommandReference.example.ilike(like),
            )
        )
    if category and category != "all":
        query = query.filter(CommandReference.category == category)
    if os and os != "all":
        if os == "both":
            query = query.filter(CommandReference.os == "both")
        else:
            query = query.filter(CommandReference.os.in_([os, "both"]))

    rows = query.order_by(CommandReference.category.asc(), CommandReference.command.asc()).all()
    category_rows = db.query(CommandReference.category).distinct().order_by(CommandReference.category.asc()).all()
    commands = [
        {
            "id": row.id,
            "command": row.command,
            "description": row.description,
            "syntax": row.syntax,
            "example": row.example,
            "category": row.category or "general",
            "os": row.os,
        }
        for row in rows
    ]
    categories = sorted({row.category or "general" for row in category_rows})
    return {"success": True, "data": commands, "categories": categories}
