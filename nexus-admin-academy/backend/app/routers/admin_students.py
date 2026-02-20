import logging
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.activity_service import get_recent_activity
from app.services.admin_auth import verify_admin
from app.utils.responses import ok

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)


class StudentCreateRequest(BaseModel):
    name: str
    email: str


class StudentUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    admin_notes: str | None = None


@router.get("/students/overview")
def student_overview(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.total_xp.desc(), Student.id.asc()).all()
    total_quizzes = db.query(Quiz).count()
    total_tickets = db.query(Ticket).count()

    data = []
    for rank, student in enumerate(students, start=1):
        quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student.id).all()
        ticket_subs = db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id, TicketSubmission.ai_score.isnot(None)).all()
        data.append(
            {
                "rank": rank,
                "student_id": student.id,
                "name": student.name,
                "email": student.email,
                "admin_notes": student.admin_notes,
                "xp": student.total_xp,
                "quiz_done": len(quiz_attempts),
                "quiz_total": total_quizzes,
                "avg_quiz": round(mean([q.score for q in quiz_attempts]), 2) if quiz_attempts else 0,
                "ticket_done": len(ticket_subs),
                "ticket_total": total_tickets,
                "avg_ticket": round(mean([t.ai_score for t in ticket_subs if t.ai_score is not None]), 2) if ticket_subs else 0,
            }
        )
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/students/{student_id}/activity")
def student_activity(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    entries = db.query(XPLedger).filter(XPLedger.student_id == student_id).order_by(XPLedger.created_at.desc()).limit(50).all()
    return ok(
        {
            "student": {"id": student.id, "name": student.name, "total_xp": student.total_xp},
            "activity": [
                {
                    "id": e.id,
                    "source_type": e.source_type,
                    "source_id": e.source_id,
                    "delta": e.delta,
                    "description": e.description,
                    "created_at": e.created_at,
                }
                for e in entries
            ],
        }
    )


@router.post("/students")
def create_student(payload: StudentCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A student with this email already exists")

    student = Student(name=payload.name, email=payload.email, total_xp=0)
    db.add(student)
    db.flush()

    from app.models.progression import MethodologyFramework, Role, StudentMethodologyProgress

    first_role = db.query(Role).filter(Role.rank_order == 1).first()
    if first_role:
        student.current_role_id = first_role.id

    for fw in db.query(MethodologyFramework).all():
        db.add(
            StudentMethodologyProgress(
                student_id=student.id,
                framework_id=fw.id,
                completed=True,
                practice_passed=True,
                quiz_score=100,
            )
        )

    db.commit()
    db.refresh(student)
    return ok({"student_id": student.id, "name": student.name, "email": student.email})


@router.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdateRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if payload.name is not None:
        student.name = payload.name
    if payload.email is not None:
        student.email = payload.email
    if payload.admin_notes is not None:
        student.admin_notes = payload.admin_notes

    db.commit()
    return ok({"student_id": student.id})


@router.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
    return ok({"deleted": True})


@router.get("/squad/activity")
def admin_squad_activity(limit: int = 30, db: Session = Depends(get_db)):
    rows = get_recent_activity(db, limit=max(1, min(limit, 100)))
    data = []
    for row in rows:
        student = db.query(Student).filter(Student.id == row.student_id).first()
        data.append(
            {
                "id": row.id,
                "student_id": row.student_id,
                "student_name": student.name if student else f"Student {row.student_id}",
                "activity_type": row.activity_type,
                "title": row.title,
                "detail": row.detail,
                "created_at": row.created_at,
            }
        )
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)
