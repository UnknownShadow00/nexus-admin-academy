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
    return ok({"quiz_id": quiz.id, "message": f"Quiz '{payload.title}' created with 10 questions"})
