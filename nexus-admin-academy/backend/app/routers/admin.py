import logging
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.ai_usage_log import AIUsageLog
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.resource import Resource
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.schemas.quiz import BulkTicketGenerateRequest, QuizGenerateRequest
from app.schemas.resource import ResourceCreateRequest
from app.schemas.ticket import ManualReviewRequest, OverrideRequest, TicketCreateRequest
from app.services.admin_auth import verify_admin
from app.services.ai_service import ai_health_test
from app.services.cve_service import fetch_recent_cves, generate_security_ticket_from_cve
from app.services.quiz_generator import generate_quiz_from_video
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
        questions = await generate_quiz_from_video(str(payload.source_url), payload.title, payload.week_number, db, admin_id=0)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Quiz generation failed: {exc}") from exc

    quiz = Quiz(title=payload.title, source_url=str(payload.source_url), week_number=payload.week_number)
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
            "ai_score": s.ai_score,
            "submitted_at": s.submitted_at,
            "admin_reviewed": s.admin_reviewed,
            "collaborator_ids": s.collaborator_ids,
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
            "ai_score": submission.ai_score,
            "ai_feedback": submission.ai_feedback,
            "xp_awarded": submission.xp_awarded,
            "screenshots": submission.screenshots,
            "collaborator_ids": submission.collaborator_ids,
            "admin_reviewed": submission.admin_reviewed,
            "admin_comment": submission.admin_comment,
        }
    )


@router.put("/submissions/{submission_id}/override")
def override_grade(submission_id: int, payload: OverrideRequest, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).filter(TicketSubmission.id == submission_id).first()
    if not submission or submission.ai_score is None:
        raise HTTPException(status_code=400, detail="Submission not found or not graded")

    participants = [submission.student_id] + [int(x) for x in (submission.collaborator_ids or [])]
    multiplier = _collab_multiplier(len(participants))

    old_score = submission.ai_score
    old_xp_each = submission.xp_awarded
    new_xp_each = int(payload.new_score * 10 * multiplier)
    delta = new_xp_each - old_xp_each

    submission.ai_score = payload.new_score
    submission.override_score = payload.new_score
    submission.overridden = True
    submission.admin_reviewed = True
    submission.admin_comment = payload.comment
    submission.xp_awarded = new_xp_each

    for sid in participants:
        award_xp(
            db,
            student_id=sid,
            delta=delta,
            source_type="admin_override",
            source_id=submission.id,
            description=f"Manual review adjustment for ticket {submission.ticket_id}",
        )

    db.commit()
    return _ok({"submission_id": submission.id, "old_score": old_score, "new_score": payload.new_score, "xp_difference_per_student": delta})


@router.get("/review")
def review_queue(db: Session = Depends(get_db)):
    rows = db.query(TicketSubmission).options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket)).filter(TicketSubmission.ai_score.isnot(None)).order_by(TicketSubmission.submitted_at.desc()).all()
    data = [
        {
            "submission_id": row.id,
            "student_name": row.student.name,
            "ticket_title": row.ticket.title,
            "ai_score": row.ai_score,
            "admin_reviewed": row.admin_reviewed,
            "submitted_at": row.submitted_at,
        }
        for row in rows
    ]
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.put("/review/{submission_id}")
def manual_review(submission_id: int, payload: ManualReviewRequest, db: Session = Depends(get_db)):
    return override_grade(submission_id, OverrideRequest(new_score=payload.new_score, comment=payload.comment), db)


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
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {"success": True, "ticket_id": ticket.id}


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
