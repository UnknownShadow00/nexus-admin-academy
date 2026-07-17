from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.squad_activity import SquadActivity
from app.models.student import Student


def mark_student_active(db: Session, student_id: int) -> None:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return
    student.last_active_at = datetime.utcnow()
    db.commit()


def log_activity(db: Session, student_id: int, activity_type: str, title: str, detail: str | None = None) -> None:
    db.add(SquadActivity(student_id=student_id, activity_type=activity_type, title=title[:200], detail=(detail or "")[:500] or None))
    db.commit()


def get_recent_activity(db: Session, limit: int = 50) -> list[SquadActivity]:
    return db.query(SquadActivity).order_by(desc(SquadActivity.created_at)).limit(limit).all()
