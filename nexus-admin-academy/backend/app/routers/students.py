from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import QuizAttempt
from app.models.student import Student
from app.models.ticket import TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.xp_calculator import level_from_xp

router = APIRouter(tags=["students"])


def _ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None):
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload


@router.get("/api/students/{student_id}/dashboard")
def get_student_dashboard(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    level, level_name = level_from_xp(student.total_xp)

    recent_entries = (
        db.query(XPLedger)
        .filter(XPLedger.student_id == student_id)
        .order_by(XPLedger.created_at.desc())
        .limit(5)
        .all()
    )

    quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).all()
    ticket_subs = db.query(TicketSubmission).filter(TicketSubmission.student_id == student_id).all()

    data = {
        "student": {
            "id": student.id,
            "name": student.name,
            "total_xp": student.total_xp,
            "level": level,
            "level_name": level_name,
            "quiz_best_scores": [{"quiz_id": q.quiz_id, "best_score": q.best_score, "first_attempt_xp": q.first_attempt_xp} for q in quiz_attempts],
            "tickets_completed": sum(1 for t in ticket_subs if t.graded_at is not None),
        },
        "recent_activity": [
            {
                "type": entry.source_type,
                "delta": entry.delta,
                "description": entry.description,
                "timestamp": entry.created_at,
            }
            for entry in recent_entries
        ],
    }

    return _ok(data)


@router.get("/api/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.total_xp.desc(), Student.id.asc()).all()
    entries = []
    for rank, student in enumerate(students, start=1):
        level, _ = level_from_xp(student.total_xp)
        entries.append(
            {
                "rank": rank,
                "student_id": student.id,
                "name": student.name,
                "total_xp": student.total_xp,
                "level": level,
            }
        )
    return _ok(entries, total=len(entries), page=1, per_page=len(entries) or 1)
