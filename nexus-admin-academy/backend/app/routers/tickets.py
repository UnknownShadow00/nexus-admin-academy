import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.schemas.ticket import TicketSubmitRequest
from app.services.ai_service import grade_ticket_submission
from app.services.xp_service import award_xp

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024


def _ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None):
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload


def _get_upload_dir() -> Path:
    configured = os.getenv("UPLOAD_DIR")
    if configured:
        path = Path(configured)
    else:
        path = Path(__file__).resolve().parents[2] / "uploads" / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _collab_multiplier(count_people: int) -> float:
    if count_people <= 1:
        return 1.0
    if count_people == 2:
        return 0.8
    return 0.6


def _validate_collaborators(db: Session, owner_student_id: int, collaborator_ids: list[int]) -> list[int]:
    deduped = []
    for cid in collaborator_ids:
        if cid == owner_student_id:
            continue
        if cid not in deduped:
            deduped.append(cid)

    if not deduped:
        return []

    found = db.query(Student).filter(Student.id.in_(deduped)).all()
    found_ids = {s.id for s in found}
    missing = [cid for cid in deduped if cid not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Collaborator(s) not found: {missing}")
    return deduped


@router.post("/uploads")
async def upload_screenshots(files: list[UploadFile] = File(...)):
    upload_dir = _get_upload_dir()
    saved = []

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type (jpg, jpeg, png, webp only)")
        if file.content_type not in ALLOWED_MIMES:
            raise HTTPException(status_code=400, detail="Invalid MIME type")

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        safe_name = f"{uuid.uuid4()}.{ext}"
        destination = (upload_dir / safe_name).resolve()
        try:
            destination.relative_to(upload_dir.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid file path") from exc

        destination.write_bytes(contents)
        logger.info("upload_saved filename=%s size=%s", safe_name, len(contents))
        saved.append(safe_name)

    return _ok({"files": saved})


@router.get("")
def get_tickets(week_number: int | None = None, student_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Ticket)
    if week_number is not None:
        query = query.filter(Ticket.week_number == week_number)
    tickets = query.order_by(Ticket.created_at.desc()).all()

    submissions = {}
    if student_id is not None:
        rows = db.query(TicketSubmission).filter(TicketSubmission.student_id == student_id).all()
        submissions = {row.ticket_id: row for row in rows}

    data = []
    for t in tickets:
        sub = submissions.get(t.id)
        if sub is None:
            status = "not_started"
            score = None
            xp = None
        elif sub.graded_at is None:
            status = "submitted"
            score = None
            xp = None
        else:
            status = "graded"
            score = sub.ai_score
            xp = sub.xp_awarded

        data.append(
            {
                "id": t.id,
                "title": t.title,
                "difficulty": t.difficulty,
                "week_number": t.week_number,
                "status": status,
                "score": score,
                "xp": xp,
            }
        )

    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{ticket_id}")
def get_ticket_details(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ok(
        {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "difficulty": ticket.difficulty,
            "week_number": ticket.week_number,
        }
    )


@router.post("/{ticket_id}/submit")
def submit_ticket(ticket_id: int, payload: TicketSubmitRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    collaborator_ids = _validate_collaborators(db, student.id, payload.collaborator_ids)

    submission = (
        db.query(TicketSubmission)
        .filter(TicketSubmission.student_id == student.id, TicketSubmission.ticket_id == ticket.id)
        .first()
    )

    if submission and submission.graded_at is not None:
        raise HTTPException(status_code=400, detail="This ticket has already been graded. Contact your instructor to review.")

    if submission is None:
        submission = TicketSubmission(
            student_id=student.id,
            ticket_id=ticket.id,
            writeup=payload.writeup,
            ai_score=None,
            ai_feedback={},
            xp_awarded=0,
            screenshots=payload.screenshots,
            collaborator_ids=collaborator_ids,
        )
        db.add(submission)
    else:
        submission.writeup = payload.writeup
        submission.screenshots = payload.screenshots
        submission.collaborator_ids = collaborator_ids

    db.flush()

    if not payload.grade_now:
        db.commit()
        return _ok(
            {
                "submission_id": submission.id,
                "status": "pending",
                "message": "Submission saved. You can still edit before grading.",
            }
        )

    ai_result = grade_ticket_submission(ticket.title, ticket.description, payload.writeup)
    ai_score = max(0, min(10, int(ai_result["ai_score"])))
    feedback = ai_result["feedback"]

    participant_ids = [student.id] + collaborator_ids
    multiplier = _collab_multiplier(len(participant_ids))
    xp_per_person = int(ai_score * 10 * multiplier)

    submission.ai_score = ai_score
    submission.ai_feedback = feedback
    submission.graded_at = submission.submitted_at
    submission.xp_awarded = xp_per_person

    for target_student_id in participant_ids:
        award_xp(
            db,
            student_id=target_student_id,
            delta=xp_per_person,
            source_type="ticket",
            source_id=submission.id,
            description=f"Ticket: {ticket.title} (Score: {ai_score}/10, participants={len(participant_ids)})",
        )

    db.commit()
    db.refresh(submission)

    logger.info(
        "ticket_submission_graded submission_id=%s ticket_id=%s student_id=%s ai_score=%s xp_per_person=%s participants=%s",
        submission.id,
        ticket.id,
        student.id,
        ai_score,
        xp_per_person,
        len(participant_ids),
    )

    return _ok(
        {
            "submission_id": submission.id,
            "ai_score": ai_score,
            "xp_awarded": xp_per_person,
            "collaboration_multiplier": multiplier,
            "participants": len(participant_ids),
            "feedback": feedback,
            "screenshots": submission.screenshots,
            "collaborator_ids": collaborator_ids,
        }
    )
