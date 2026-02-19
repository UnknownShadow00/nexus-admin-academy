import logging
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.ai_usage_log import AIUsageLog
from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.command_reference import CommandReference
from app.models.evidence import EvidenceArtifact
from app.models.incident import Incident, IncidentParticipant, IncidentTicket, RCASubmission, RootCause
from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson, Module
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.progression import MethodologyFramework, PromotionGate, Role
from app.models.resource import Resource
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.schemas.quiz import BulkTicketGenerateRequest, QuizGenerateRequest
from app.schemas.resource import ResourceCreateRequest
from app.schemas.ticket import ManualReviewRequest, OverrideRequest, TicketCreateRequest
from app.services.activity_service import get_recent_activity, log_activity
from app.services.admin_auth import verify_admin
from app.services.ai_service import ai_health_test
from app.services.cve_service import fetch_recent_cves, generate_security_ticket_from_cve
from app.services.mastery_service import record_ticket_mastery_verified
from app.services.quiz_generator import generate_quiz_from_video
from app.services.squad_service import get_weekly_domain_leads, recompute_weekly_domain_leads
from app.services.ticket_generator import generate_ticket_description
from app.services.xp_service import award_xp
from app.utils.responses import ok

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)



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

@router.post("/weekly-domain-leads/recompute")
def recompute_leads(db: Session = Depends(get_db)):
    created = recompute_weekly_domain_leads(db)
    return ok(created, total=len(created), page=1, per_page=len(created) or 1)

@router.get("/weekly-domain-leads")
def list_weekly_leads(week_key: str | None = None, db: Session = Depends(get_db)):
    leads = get_weekly_domain_leads(db, week_key=week_key)
    return ok(leads, total=len(leads), page=1, per_page=len(leads) or 1)

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
