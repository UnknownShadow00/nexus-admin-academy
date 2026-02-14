from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.command_reference import CommandReference

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.get("/search")
def search_commands(q: str = "", db: Session = Depends(get_db)):
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
