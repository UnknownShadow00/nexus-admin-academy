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



def _collab_multiplier(count_people: int) -> float:
    if count_people <= 1:
        return 1.0
    if count_people == 2:
        return 0.8
    return 0.6


@router.post("/tickets")
def create_ticket(payload: TicketCreateRequest, db: Session = Depends(get_db)):
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        difficulty=payload.difficulty,
        week_number=payload.week_number,
        category=payload.category or "general",
        domain_id=payload.domain_id,
        lesson_id=payload.lesson_id,
        root_cause=payload.root_cause,
        root_cause_type=payload.root_cause_type,
        required_checkpoints=payload.required_checkpoints or {},
        required_evidence=payload.required_evidence or {},
        scoring_anchors=payload.scoring_anchors or {},
        model_answer=payload.model_answer,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ok({"ticket_id": ticket.id, "title": ticket.title})

@router.get("/submissions")
def list_submissions(student_id: int | None = None, ticket_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(TicketSubmission).options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
    if student_id is not None:
        query = query.filter(TicketSubmission.student_id == student_id)
    if ticket_id is not None:
        query = query.filter(TicketSubmission.ticket_id == ticket_id)

    submissions = query.order_by(TicketSubmission.submitted_at.desc()).all()
    data = [
        {
            "id": s.id,
            "student_name": s.student.name,
            "ticket_title": s.ticket.title,
            "ai_score": s.final_score if s.final_score is not None else s.ai_score,
            "submitted_at": s.submitted_at,
            "admin_reviewed": s.admin_reviewed,
            "collaborator_ids": s.collaborator_ids,
            "status": s.status,
            "xp_granted": s.xp_granted,
        }
        for s in submissions
    ]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)

@router.get("/submissions/{submission_id}")
def submission_details(submission_id: int, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket)).filter(TicketSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return ok(
        {
            "id": submission.id,
            "student_name": submission.student.name,
            "ticket_title": submission.ticket.title,
            "writeup": submission.writeup,
            "commands_used": submission.commands_used,
            "ai_score": submission.final_score if submission.final_score is not None else submission.ai_score,
            "ai_feedback": submission.ai_feedback,
            "xp_awarded": submission.xp_awarded,
            "before_screenshot_id": submission.before_screenshot_id,
            "after_screenshot_id": submission.after_screenshot_id,
            "evidence_complete": submission.evidence_complete,
            "collaborator_ids": submission.collaborator_ids,
            "admin_reviewed": submission.admin_reviewed,
            "admin_comment": submission.admin_comment,
            "status": submission.status,
            "xp_granted": submission.xp_granted,
        }
    )

@router.put("/submissions/{submission_id}/override")
def override_grade(submission_id: int, payload: OverrideRequest, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).filter(TicketSubmission.id == submission_id).first()
    if not submission or submission.ai_score is None:
        raise HTTPException(status_code=400, detail="Submission not found or not graded")

    participants = [submission.student_id] + [int(x) for x in (submission.collaborator_ids or [])]
    multiplier = _collab_multiplier(len(participants))

    old_score = submission.final_score if submission.final_score is not None else submission.ai_score
    old_xp_each = submission.xp_awarded
    new_xp_each = int(payload.new_score * 10 * multiplier)
    delta = new_xp_each - old_xp_each

    submission.ai_score = payload.new_score
    submission.final_score = payload.new_score
    submission.override_score = payload.new_score
    submission.overridden = True
    submission.admin_reviewed = True
    submission.admin_comment = payload.comment
    submission.xp_awarded = new_xp_each

    if submission.xp_granted and delta != 0:
        for sid in participants:
            award_xp(
                db,
                student_id=sid,
                delta=delta,
                source_type="admin_override",
                source_id=submission.id,
                description=f"Manual review adjustment for ticket {submission.ticket_id}",
            )
    elif not submission.xp_granted:
        submission.status = "pending"

    db.commit()
    log_activity(
        db,
        submission.student_id,
        "ticket_override",
        submission.ticket.title if submission.ticket else f"Ticket {submission.ticket_id}",
        f"Score adjusted to {payload.new_score}/10",
    )
    return ok({"submission_id": submission.id, "old_score": old_score, "new_score": payload.new_score, "xp_difference_per_student": delta})

@router.get("/review")
def review_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(TicketSubmission)
        .options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
        .filter(TicketSubmission.ai_score.isnot(None))
        .order_by(TicketSubmission.submitted_at.desc())
        .all()
    )
    data = [
        {
            "submission_id": row.id,
            "student_name": row.student.name,
            "ticket_title": row.ticket.title,
            "ai_score": row.final_score if row.final_score is not None else row.ai_score,
            "admin_reviewed": row.admin_reviewed,
            "status": row.status,
            "xp_granted": row.xp_granted,
            "submitted_at": row.submitted_at,
        }
        for row in rows
    ]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)

@router.put("/review/{submission_id}")
def manual_review(submission_id: int, payload: ManualReviewRequest, db: Session = Depends(get_db)):
    return override_grade(submission_id, OverrideRequest(new_score=payload.new_score, comment=payload.comment), db)

@router.put("/submissions/{submission_id}/verify-proof")
def verify_proof(submission_id: int, comment: str | None = None, db: Session = Depends(get_db)):
    submission = (
        db.query(TicketSubmission)
        .options(selectinload(TicketSubmission.ticket))
        .filter(TicketSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.ai_score is None:
        raise HTTPException(status_code=400, detail="Submission has not been graded yet")
    if submission.status == "passed" and submission.xp_granted:
        return ok({"submission_id": submission.id, "status": "passed", "message": "Already passed"})

    submission.status = "in_review"
    participants = [submission.student_id] + [int(x) for x in (submission.collaborator_ids or [])]
    for sid in participants:
        award_xp(
            db,
            student_id=sid,
            delta=submission.xp_awarded,
            source_type="ticket",
            source_id=submission.id,
            description=f"Ticket verified: {submission.ticket.title if submission.ticket else submission.ticket_id}",
        )

    submission.xp_granted = True
    submission.status = "passed"
    submission.admin_reviewed = True
    submission.admin_comment = comment or submission.admin_comment
    submission.verified_at = datetime.utcnow()
    submission.verified_by = 0
    db.commit()

    ticket_domain = submission.ticket.domain_id if submission.ticket else "1.0"
    score_for_mastery = int(submission.final_score if submission.final_score is not None else submission.ai_score or 0)
    for sid in participants:
        record_ticket_mastery_verified(db, sid, ticket_domain, score_for_mastery)

    log_activity(
        db,
        submission.student_id,
        "ticket_verified",
        submission.ticket.title if submission.ticket else f"Ticket {submission.ticket_id}",
        f"Verified score {score_for_mastery}/10",
    )

    return ok(
        {
            "submission_id": submission.id,
            "status": submission.status,
            "xp_awarded_each": submission.xp_awarded,
            "participants": participants,
        }
    )

@router.put("/submissions/{submission_id}/reject-proof")
def reject_proof(submission_id: int, comment: str | None = None, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).filter(TicketSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.xp_granted:
        raise HTTPException(status_code=400, detail="Cannot reject after XP was granted")

    submission.status = "needs_revision"
    submission.admin_reviewed = True
    submission.admin_comment = comment or submission.admin_comment
    db.commit()
    return ok({"submission_id": submission.id, "status": submission.status})

@router.post("/tickets/bulk-generate")
async def bulk_generate_tickets(payload: BulkTicketGenerateRequest, db: Session = Depends(get_db)):
    try:
        generated = []
        for raw in payload.titles:
            title = raw.strip()
            if not title:
                continue

            try:
                description = await generate_ticket_description(title, payload.week_number, payload.difficulty, db, user_id=0)
                generated.append(
                    {
                        "title": title,
                        "description": description,
                        "difficulty": payload.difficulty,
                        "week_number": payload.week_number,
                        "success": True,
                    }
                )
            except Exception as exc:
                logger.exception("bulk_ticket_generate_item_failed title=%s", title)
                generated.append({"title": title, "error": str(exc), "success": False})

        return ok(generated)
    except Exception as exc:
        logger.exception("bulk_ticket_generate_failed")
        return {"success": False, "error": str(exc)}

@router.post("/tickets/bulk-publish")
def bulk_publish_tickets(payload: list[TicketCreateRequest], db: Session = Depends(get_db)):
    created = []
    for item in payload:
        ticket = Ticket(
            title=item.title,
            description=item.description,
            difficulty=item.difficulty,
            week_number=item.week_number,
            category=item.category or "general",
            domain_id=item.domain_id,
            lesson_id=item.lesson_id,
            root_cause=item.root_cause,
            root_cause_type=item.root_cause_type,
            required_checkpoints=item.required_checkpoints or {},
            required_evidence=item.required_evidence or {},
            scoring_anchors=item.scoring_anchors or {},
            model_answer=item.model_answer,
        )
        db.add(ticket)
        db.flush()
        created.append({"ticket_id": ticket.id, "title": ticket.title})
    db.commit()
    return ok(created, total=len(created), page=1, per_page=len(created) or 1)

@router.post("/tickets/bulk")
async def bulk_generate_with_ai(payload: BulkTicketGenerateRequest, db: Session = Depends(get_db)):
    try:
        generated = []
        for raw in payload.titles:
            title = raw.strip()
            if not title:
                continue
            try:
                description = await generate_ticket_description(title, payload.week_number, payload.difficulty, db, user_id=0)
                generated.append({
                    "title": title,
                    "description": description,
                    "week_number": payload.week_number,
                    "difficulty": payload.difficulty,
                    "success": True,
                })
            except Exception as exc:
                logger.exception("bulk_ticket_ai_item_failed title=%s", title)
                generated.append({"title": title, "error": str(exc), "success": False})
        return ok(generated)
    except Exception as exc:
        logger.exception("bulk_ticket_ai_failed")
        return {"success": False, "error": str(exc)}

@router.get("/cve/recent")
async def get_recent_cves(keyword: str = "windows"):
    cves = await fetch_recent_cves(keyword=keyword)
    return {"success": True, "cves": cves}

@router.post("/tickets/from-cve")
async def create_ticket_from_cve(cve_id: str, db: Session = Depends(get_db)):
    ticket_data = await generate_security_ticket_from_cve(cve_id)
    if not ticket_data:
        raise HTTPException(status_code=404, detail="CVE not found")

    ticket = Ticket(
        title=ticket_data["title"],
        description=ticket_data["description"],
        difficulty=ticket_data["difficulty"],
        week_number=ticket_data["week_number"],
        category=ticket_data.get("category", "security"),
        domain_id="4.0",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {"success": True, "ticket_id": ticket.id}
