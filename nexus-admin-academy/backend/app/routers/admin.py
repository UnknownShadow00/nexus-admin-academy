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

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)


def _ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None):
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload


def _collab_multiplier(count_people: int) -> float:
    if count_people <= 1:
        return 1.0
    if count_people == 2:
        return 0.8
    return 0.6


@router.post("/quiz/generate")
async def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db)):
    try:
        questions = await generate_quiz_from_video(
            str(payload.source_url),
            payload.title,
            payload.week_number,
            db,
            admin_id=0,
            domain_id=payload.domain_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Quiz generation failed: {exc}") from exc

    quiz = Quiz(
        title=payload.title,
        source_url=str(payload.source_url),
        week_number=payload.week_number,
        domain_id=payload.domain_id,
        lesson_id=payload.lesson_id,
    )
    db.add(quiz)
    db.flush()

    for q in questions:
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
            )
        )

    db.commit()
    logger.info("admin_quiz_generated quiz_id=%s week=%s title=%s", quiz.id, payload.week_number, payload.title)
    return _ok({"quiz_id": quiz.id, "message": f"Quiz '{payload.title}' created with 10 questions"})


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
    return _ok({"ticket_id": ticket.id, "title": ticket.title})


@router.post("/resources")
def create_resource(payload: ResourceCreateRequest, db: Session = Depends(get_db)):
    resource = Resource(
        title=payload.title,
        url=str(payload.url),
        resource_type=payload.resource_type,
        week_number=payload.week_number,
        category=payload.category,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return _ok({"resource_id": resource.id})


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(resource)
    db.commit()
    return _ok({"deleted": True})


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
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/submissions/{submission_id}")
def submission_details(submission_id: int, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket)).filter(TicketSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return _ok(
        {
            "id": submission.id,
            "student_name": submission.student.name,
            "ticket_title": submission.ticket.title,
            "writeup": submission.writeup,
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
    return _ok({"submission_id": submission.id, "old_score": old_score, "new_score": payload.new_score, "xp_difference_per_student": delta})


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
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


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
    if submission.status == "verified" and submission.xp_granted:
        return _ok({"submission_id": submission.id, "status": "verified", "message": "Already verified"})

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
    submission.status = "verified"
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

    return _ok(
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

    submission.status = "rejected"
    submission.admin_reviewed = True
    submission.admin_comment = comment or submission.admin_comment
    db.commit()
    return _ok({"submission_id": submission.id, "status": submission.status})


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
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/students/{student_id}/activity")
def student_activity(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    entries = db.query(XPLedger).filter(XPLedger.student_id == student_id).order_by(XPLedger.created_at.desc()).limit(50).all()
    return _ok(
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

        return _ok(generated)
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
    return _ok(created, total=len(created), page=1, per_page=len(created) or 1)


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
        return _ok(generated)
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


@router.post("/weekly-domain-leads/recompute")
def recompute_leads(db: Session = Depends(get_db)):
    created = recompute_weekly_domain_leads(db)
    return _ok(created, total=len(created), page=1, per_page=len(created) or 1)


@router.get("/weekly-domain-leads")
def list_weekly_leads(week_key: str | None = None, db: Session = Depends(get_db)):
    leads = get_weekly_domain_leads(db, week_key=week_key)
    return _ok(leads, total=len(leads), page=1, per_page=len(leads) or 1)


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
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/ai-test")
async def ai_test(db: Session = Depends(get_db)):
    try:
        result = await ai_health_test(db, user_id=0)
        return {"success": True, **result}
    except HTTPException as exc:
        return {"success": False, "error": exc.detail}
    except Exception as exc:
        logger.exception("ai_test_failed")
        return {"success": False, "error": str(exc)}


@router.get("/ai-usage")
def get_ai_usage_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    daily_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    monthly_cutoff = now - timedelta(days=30)

    daily = db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0)).filter(AIUsageLog.created_at > daily_cutoff).scalar() or 0
    monthly = db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0)).filter(AIUsageLog.created_at > monthly_cutoff).scalar() or 0
    total = db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0)).scalar() or 0

    breakdown_rows = (
        db.query(
            AIUsageLog.feature.label("feature"),
            func.count(AIUsageLog.id).label("call_count"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AIUsageLog.cost_estimate), 0).label("total_cost"),
            func.coalesce(func.avg(AIUsageLog.cost_estimate), 0).label("avg_cost_per_call"),
        )
        .group_by(AIUsageLog.feature)
        .order_by(func.sum(AIUsageLog.cost_estimate).desc())
        .all()
    )

    recent = db.query(AIUsageLog).order_by(AIUsageLog.created_at.desc()).limit(20).all()

    return _ok(
        {
            "summary": {
                "daily_cost": float(Decimal(str(daily))),
                "monthly_cost": float(Decimal(str(monthly))),
                "total_cost": float(Decimal(str(total))),
            },
            "breakdown": [
                {
                    "feature": row.feature,
                    "calls": int(row.call_count),
                    "tokens": int(row.total_tokens or 0),
                    "cost": float(Decimal(str(row.total_cost or 0))),
                    "avg_per_call": float(Decimal(str(row.avg_cost_per_call or 0))),
                }
                for row in breakdown_rows
            ],
            "recent_calls": [
                {
                    "feature": row.feature,
                    "model": row.model,
                    "tokens": row.total_tokens,
                    "cost": float(Decimal(str(row.cost_estimate))),
                    "timestamp": row.created_at.isoformat() if row.created_at else None,
                }
                for row in recent
            ],
        }
    )


@router.get("/modules")
def list_modules(db: Session = Depends(get_db)):
    rows = db.query(Module).order_by(Module.module_order.asc().nullslast(), Module.id.asc()).all()
    return _ok(
        [
            {
                "id": row.id,
                "code": row.code,
                "title": row.title,
                "description": row.description,
                "target_role": row.target_role,
                "difficulty_band": row.difficulty_band,
                "estimated_hours": row.estimated_hours,
                "prerequisite_module_id": row.prerequisite_module_id,
                "unlock_threshold": row.unlock_threshold,
                "module_order": row.module_order,
                "active": row.active,
            }
            for row in rows
        ]
    )


@router.post("/modules")
def create_module(payload: dict, db: Session = Depends(get_db)):
    row = Module(
        code=payload.get("code"),
        title=payload.get("title"),
        description=payload.get("description"),
        target_role=payload.get("target_role"),
        difficulty_band=payload.get("difficulty_band"),
        estimated_hours=payload.get("estimated_hours"),
        prerequisite_module_id=payload.get("prerequisite_module_id"),
        unlock_threshold=payload.get("unlock_threshold", 70),
        module_order=payload.get("module_order"),
        active=payload.get("active", True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ok({"module_id": row.id})


@router.put("/modules/{module_id}")
def update_module(module_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(Module).filter(Module.id == module_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Module not found")
    for field in [
        "code",
        "title",
        "description",
        "target_role",
        "difficulty_band",
        "estimated_hours",
        "prerequisite_module_id",
        "unlock_threshold",
        "module_order",
        "active",
    ]:
        if field in payload:
            setattr(row, field, payload[field])
    db.commit()
    return _ok({"module_id": row.id})


@router.get("/lessons")
def list_lessons(module_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Lesson)
    if module_id is not None:
        q = q.filter(Lesson.module_id == module_id)
    rows = q.order_by(Lesson.module_id.asc(), Lesson.lesson_order.asc()).all()
    return _ok(
        [
            {
                "id": row.id,
                "module_id": row.module_id,
                "title": row.title,
                "summary": row.summary,
                "lesson_order": row.lesson_order,
                "outcomes": row.outcomes,
                "estimated_minutes": row.estimated_minutes,
                "required_notes_template": row.required_notes_template,
                "status": row.status,
            }
            for row in rows
        ]
    )


@router.post("/lessons")
def create_lesson(payload: dict, db: Session = Depends(get_db)):
    row = Lesson(
        module_id=payload.get("module_id"),
        title=payload.get("title"),
        summary=payload.get("summary"),
        lesson_order=payload.get("lesson_order"),
        outcomes=payload.get("outcomes") or [],
        estimated_minutes=payload.get("estimated_minutes"),
        required_notes_template=payload.get("required_notes_template"),
        status=payload.get("status", "draft"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ok({"lesson_id": row.id})


@router.put("/tickets/{ticket_id}/answer-key")
def update_ticket_answer_key(ticket_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for field in [
        "root_cause",
        "root_cause_type",
        "required_checkpoints",
        "required_evidence",
        "scoring_anchors",
        "model_answer",
        "lesson_id",
        "domain_id",
    ]:
        if field in payload:
            setattr(row, field, payload[field])
    db.commit()
    return _ok({"ticket_id": row.id})


@router.get("/evidence")
def list_evidence(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(EvidenceArtifact)
    if status:
        q = q.filter(EvidenceArtifact.validation_status == status)
    rows = q.order_by(EvidenceArtifact.uploaded_at.desc()).limit(200).all()
    return _ok(
        [
            {
                "id": row.id,
                "submission_type": row.submission_type,
                "submission_id": row.submission_id,
                "artifact_type": row.artifact_type,
                "storage_key": row.storage_key,
                "validation_status": row.validation_status,
                "validation_notes": row.validation_notes,
                "uploaded_at": row.uploaded_at,
            }
            for row in rows
        ]
    )


@router.put("/evidence/{artifact_id}")
def review_evidence(artifact_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(EvidenceArtifact).filter(EvidenceArtifact.id == artifact_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if "validation_status" in payload:
        row.validation_status = payload["validation_status"]
    if "validation_notes" in payload:
        row.validation_notes = payload["validation_notes"]
    row.validated_at = datetime.utcnow()
    row.validated_by = payload.get("validated_by")
    db.commit()
    return _ok({"artifact_id": row.id})


@router.get("/methodology/frameworks")
def list_methodology_frameworks(db: Session = Depends(get_db)):
    rows = db.query(MethodologyFramework).order_by(MethodologyFramework.id.asc()).all()
    return _ok(
        [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "steps": row.steps,
                "required_for_role": row.required_for_role,
            }
            for row in rows
        ]
    )


@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    rows = db.query(Role).order_by(Role.rank_order.asc()).all()
    return _ok([{"id": r.id, "name": r.name, "rank_order": r.rank_order, "description": r.description} for r in rows])


@router.get("/promotion-gates")
def list_promotion_gates(role_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(PromotionGate)
    if role_id:
        q = q.filter(PromotionGate.role_id == role_id)
    rows = q.order_by(PromotionGate.role_id.asc(), PromotionGate.id.asc()).all()
    return _ok(
        [
            {
                "id": row.id,
                "role_id": row.role_id,
                "requirement_type": row.requirement_type,
                "requirement_config": row.requirement_config,
                "effective_from": row.effective_from,
                "effective_to": row.effective_to,
            }
            for row in rows
        ]
    )


@router.get("/labs/templates")
def list_lab_templates(lesson_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(LabTemplate)
    if lesson_id is not None:
        q = q.filter(LabTemplate.lesson_id == lesson_id)
    rows = q.order_by(LabTemplate.created_at.desc()).all()
    return _ok(
        [
            {
                "id": r.id,
                "lesson_id": r.lesson_id,
                "title": r.title,
                "description": r.description,
                "lab_type": r.lab_type,
                "difficulty": r.difficulty,
                "estimated_minutes": r.estimated_minutes,
                "success_criteria": r.success_criteria,
                "required_evidence": r.required_evidence,
            }
            for r in rows
        ]
    )


@router.post("/labs/templates")
def create_lab_template(payload: dict, db: Session = Depends(get_db)):
    row = LabTemplate(
        lesson_id=payload.get("lesson_id"),
        title=payload.get("title"),
        description=payload.get("description"),
        lab_type=payload.get("lab_type"),
        difficulty=payload.get("difficulty", 1),
        estimated_minutes=payload.get("estimated_minutes"),
        environment_requirements=payload.get("environment_requirements") or {},
        setup_instructions=payload.get("setup_instructions"),
        break_script=payload.get("break_script"),
        success_criteria=payload.get("success_criteria") or {},
        required_evidence=payload.get("required_evidence") or {},
        hints=payload.get("hints") or {},
        model_solution=payload.get("model_solution"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ok({"lab_template_id": row.id})


@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    rows = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return _ok(
        [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "incident_type": r.incident_type,
                "severity": r.severity,
                "impacted_services": r.impacted_services,
                "rca_required": r.rca_required,
                "root_cause_id": r.root_cause_id,
            }
            for r in rows
        ]
    )


@router.post("/incidents")
def create_incident(payload: dict, db: Session = Depends(get_db)):
    root_cause_id = payload.get("root_cause_id")
    if not root_cause_id and payload.get("root_cause"):
        rc = RootCause(
            service_area=payload["root_cause"].get("service_area"),
            cause_type=payload["root_cause"].get("cause_type"),
            description=payload["root_cause"].get("description"),
            break_method=payload["root_cause"].get("break_method"),
            fix_method=payload["root_cause"].get("fix_method"),
            validation_steps=payload["root_cause"].get("validation_steps"),
        )
        db.add(rc)
        db.flush()
        root_cause_id = rc.id

    row = Incident(
        title=payload.get("title"),
        description=payload.get("description"),
        incident_type=payload.get("incident_type"),
        impacted_services=payload.get("impacted_services") or [],
        root_cause_id=root_cause_id,
        start_time=payload.get("start_time"),
        end_time=payload.get("end_time"),
        rca_required=payload.get("rca_required", True),
        severity=payload.get("severity"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ok({"incident_id": row.id})


@router.post("/incidents/{incident_id}/tickets")
def link_incident_ticket(incident_id: int, payload: dict, db: Session = Depends(get_db)):
    row = IncidentTicket(
        incident_id=incident_id,
        ticket_id=payload.get("ticket_id"),
        symptom_role=payload.get("symptom_role"),
        dependency_order=payload.get("dependency_order"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ok({"incident_ticket_id": row.id})


@router.get("/capstones/templates")
def list_capstone_templates(db: Session = Depends(get_db)):
    rows = db.query(CapstoneTemplate).order_by(CapstoneTemplate.created_at.desc()).all()
    return _ok(
        [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "role_level": r.role_level,
                "requirements": r.requirements,
                "deliverables": r.deliverables,
                "estimated_hours": r.estimated_hours,
                "rubric": r.rubric,
            }
            for r in rows
        ]
    )


@router.post("/capstones/templates")
def create_capstone_template(payload: dict, db: Session = Depends(get_db)):
    row = CapstoneTemplate(
        title=payload.get("title"),
        description=payload.get("description"),
        role_level=payload.get("role_level"),
        requirements=payload.get("requirements") or {},
        deliverables=payload.get("deliverables") or {},
        estimated_hours=payload.get("estimated_hours"),
        rubric=payload.get("rubric") or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ok({"capstone_template_id": row.id})


@router.get("/ops/summary")
def operations_summary(db: Session = Depends(get_db)):
    return _ok(
        {
            "lab_templates": db.query(func.count(LabTemplate.id)).scalar() or 0,
            "lab_runs": db.query(func.count(LabRun.id)).scalar() or 0,
            "incidents": db.query(func.count(Incident.id)).scalar() or 0,
            "incident_participants": db.query(func.count(IncidentParticipant.id)).scalar() or 0,
            "rca_submissions": db.query(func.count(RCASubmission.id)).scalar() or 0,
            "capstone_templates": db.query(func.count(CapstoneTemplate.id)).scalar() or 0,
            "capstone_runs": db.query(func.count(CapstoneRun.id)).scalar() or 0,
        }
    )
