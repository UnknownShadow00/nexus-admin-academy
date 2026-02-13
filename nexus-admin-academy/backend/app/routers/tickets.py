import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.schemas.ticket import (
    TicketDetailResponse,
    TicketListItem,
    TicketListResponse,
    TicketSubmitRequest,
    TicketSubmitResponse,
)
from app.services.ai_service import grade_ticket_submission
from app.services.xp_calculator import ticket_xp

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
logger = logging.getLogger(__name__)


@router.get("", response_model=TicketListResponse)
def get_tickets(week_number: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Ticket)
    if week_number is not None:
        query = query.filter(Ticket.week_number == week_number)
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return TicketListResponse(
        tickets=[
            TicketListItem(
                id=t.id,
                title=t.title,
                difficulty=t.difficulty,
                week_number=t.week_number,
            )
            for t in tickets
        ]
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_details(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketDetailResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        difficulty=ticket.difficulty,
        week_number=ticket.week_number,
    )


@router.post("/{ticket_id}/submit", response_model=TicketSubmitResponse)
def submit_ticket(ticket_id: int, payload: TicketSubmitRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ai_result = grade_ticket_submission(ticket.title, ticket.description, payload.writeup)
    ai_score = max(0, min(10, int(ai_result["ai_score"])))
    feedback = ai_result["feedback"]
    awarded_xp = ticket_xp(ai_score)

    student.total_xp += awarded_xp
    submission = TicketSubmission(
        student_id=student.id,
        ticket_id=ticket.id,
        writeup=payload.writeup,
        ai_score=ai_score,
        ai_feedback=feedback,
        xp_awarded=awarded_xp,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    logger.info(
        "ticket_submission student_id=%s ticket_id=%s ai_score=%s xp_awarded=%s submission_id=%s",
        student.id,
        ticket.id,
        ai_score,
        awarded_xp,
        submission.id,
    )

    return TicketSubmitResponse(
        submission_id=submission.id,
        ai_score=ai_score,
        xp_awarded=awarded_xp,
        feedback=feedback,
    )
