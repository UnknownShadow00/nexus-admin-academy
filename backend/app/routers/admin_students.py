import logging
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.service_desk import ServiceDeskAssignment, ServiceDeskScenario
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.activity_service import get_recent_activity
from app.services.onboarding_service import get_orientation_state
from app.services.quiz_progression import is_quiz_passed
from app.services.service_desk_progression import PACK_BY_SCENARIO
from app.services.admin_auth import verify_admin
from app.services.auth_service import hash_password, normalize_username
from app.services.student_deletion import delete_student_owned_data
from app.services.training_service import build_cohort_summary, build_training_progress
from app.utils.responses import ok

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)


class StudentCreateRequest(BaseModel):
    name: str
    email: str
    username: str
    password: str


class StudentUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    admin_notes: str | None = None
    username: str | None = None
    password: str | None = None
    is_mentor: bool | None = None


@router.get("/students/overview")
def student_overview(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.total_xp.desc(), Student.id.asc()).all()
    required_quizzes = db.query(Quiz).filter(
        Quiz.status == QUIZ_STATUS_PUBLISHED,
        Quiz.is_active.is_(True),
        Quiz.is_required.is_(True),
        Quiz.show_in_weekly_checklist.is_(True),
        Quiz.answer_keys_validated.is_(True),
    ).all()
    total_quizzes = len(required_quizzes)
    total_tickets = db.query(Ticket).count()

    data = []
    for rank, student in enumerate(students, start=1):
        required_ids = {quiz.id for quiz in required_quizzes}
        quiz_attempts = db.query(QuizAttempt).filter(
            QuizAttempt.student_id == student.id,
            QuizAttempt.quiz_id.in_(required_ids),
        ).all() if required_ids else []
        completed_required = sum(is_quiz_passed(db, student.id, quiz) for quiz in required_quizzes)
        ticket_subs = db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id, TicketSubmission.ai_score.isnot(None)).all()
        data.append(
            {
                "rank": rank,
                "student_id": student.id,
                "name": student.name,
                "email": student.email,
                "username": student.username,
                "admin_notes": student.admin_notes,
                "is_mentor": bool(student.is_mentor),
                "xp": student.total_xp,
                "quiz_done": completed_required,
                "quiz_total": total_quizzes,
                "avg_quiz": round(mean([q.score for q in quiz_attempts]), 2) if quiz_attempts else 0,
                "ticket_done": len(ticket_subs),
                "ticket_total": total_tickets,
                "avg_ticket": round(mean([t.ai_score for t in ticket_subs if t.ai_score is not None]), 2) if ticket_subs else 0,
            }
        )
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/students/cohort-summary")
def cohort_summary(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.id.asc()).all()
    return ok(build_cohort_summary(db, students))


@router.get("/students/{student_id}/training-progress")
def student_training_progress(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return ok(build_training_progress(db, student))


@router.get("/students/{student_id}/activity")
def student_activity(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    entries = db.query(XPLedger).filter(XPLedger.student_id == student_id).order_by(XPLedger.created_at.desc()).limit(50).all()
    return ok(
        {
            "student": {"id": student.id, "name": student.name, "total_xp": student.total_xp},
            "onboarding": get_orientation_state(db, student),
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

    username = payload.username.strip()
    existing_username = (
        db.query(Student).filter(func.lower(Student.username) == normalize_username(username)).first()
    )
    if existing_username:
        raise HTTPException(status_code=400, detail="A student with this username already exists")

    student = Student(
        name=payload.name,
        email=payload.email,
        total_xp=0,
        username=username,
        password_hash=hash_password(payload.password),
    )
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

    # New accounts receive the same managed scenario catalog as seeded
    # accounts. Student-facing availability is still filtered by the
    # server-authoritative pack progression; these rows are assignment
    # inventory, not an unlock shortcut.
    managed_scenarios = db.query(ServiceDeskScenario).filter(
        ServiceDeskScenario.status == "active",
        ServiceDeskScenario.stable_key.in_(set(PACK_BY_SCENARIO)),
    ).all()
    for scenario in managed_scenarios:
        db.add(ServiceDeskAssignment(
            student_id=student.id,
            scenario_id=scenario.id,
            mode="simulation",
            is_required=False,
            assigned_by="student-create",
        ))

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("student_create_integrity_conflict")
        raise HTTPException(status_code=409, detail="Student account could not be created") from exc
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
    if payload.username is not None:
        student.username = payload.username
    if payload.password is not None:
        student.password_hash = hash_password(payload.password)
    if payload.is_mentor is not None:
        student.is_mentor = payload.is_mentor

    db.commit()
    return ok({"student_id": student.id})


@router.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    try:
        delete_student_owned_data(db, student_id)
        db.delete(student)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("student_delete_integrity_conflict student_id=%s", student_id)
        raise HTTPException(status_code=409, detail="Student account has protected records") from exc
    except Exception:
        db.rollback()
        logger.exception("student_delete_failed student_id=%s", student_id)
        raise
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
