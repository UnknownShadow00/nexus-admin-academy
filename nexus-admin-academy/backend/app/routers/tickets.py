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
from app.services.ticket_grader import grade_ticket_submission
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
    path = Path(configured) if configured else Path(__file__).resolve().parents[2] / "uploads" / "screenshots"
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
            status, score, xp, submission_id = "not_started", None, None, None
        elif sub.ai_score is None:
            status, score, xp, submission_id = "submitted", None, None, sub.id
        else:
            status, score, xp, submission_id = "graded", sub.ai_score, sub.xp_awarded, sub.id

        data.append(
            {
                "id": t.id,
                "title": t.title,
                "difficulty": t.difficulty,
                "week_number": t.week_number,
                "category": t.category or "general",
                "status": status,
                "score": score,
                "xp": xp,
                "submission_id": submission_id,
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
            "category": ticket.category or "general",
        }
    )


@router.post("/{ticket_id}/submit")
async def submit_ticket(ticket_id: int, payload: TicketSubmitRequest, db: Session = Depends(get_db)):
    student_id = payload.student_id
    writeup = payload.writeup
    collaborators = _validate_collaborators(db, student_id, payload.collaborator_ids or [])
    screenshots = payload.screenshots or []
    duration_minutes = payload.duration_minutes

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    existing = db.query(TicketSubmission).filter(TicketSubmission.student_id == student_id, TicketSubmission.ticket_id == ticket_id).first()
    if existing and existing.ai_score is not None:
        raise HTTPException(status_code=400, detail="This ticket has already been graded. Contact instructor for review.")

    try:
        grading = await grade_ticket_submission(
            ticket_id=ticket_id,
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            student_writeup=writeup,
            difficulty=ticket.difficulty,
            db=db,
            student_id=student_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI grading failed: {exc}") from exc

    ai_score = grading["score"]
    ai_feedback = {
        "strengths": grading["strengths"],
        "weaknesses": grading["weaknesses"],
        "feedback": grading["feedback"],
    }

    base_xp = ai_score * 10
    num_people = 1 + len(collaborators)
    multiplier = _collab_multiplier(num_people)
    xp_per_person = int(base_xp * multiplier)

    if existing:
        submission_id = existing.id
        existing.writeup = writeup
        existing.screenshots = screenshots
        existing.collaborator_ids = collaborators
        existing.ai_score = ai_score
        existing.ai_feedback = ai_feedback
        existing.xp_awarded = xp_per_person
        existing.duration_minutes = duration_minutes
        if duration_minutes is not None and existing.started_at is None:
            existing.started_at = existing.submitted_at
    else:
        new_sub = TicketSubmission(
            student_id=student_id,
            ticket_id=ticket_id,
            writeup=writeup,
            screenshots=screenshots,
            collaborator_ids=collaborators,
            ai_score=ai_score,
            ai_feedback=ai_feedback,
            xp_awarded=xp_per_person,
            duration_minutes=duration_minutes,
        )
        db.add(new_sub)
        db.flush()
        submission_id = new_sub.id

    for participant_id in [student_id] + collaborators:
        award_xp(
            db,
            student_id=participant_id,
            delta=xp_per_person,
            source_type="ticket",
            source_id=submission_id,
            description=f"Ticket: {ticket.title} (Score: {ai_score}/10, {num_people} collaborators)",
        )

    db.commit()

    return _ok(
        {
            "submission_id": submission_id,
            "ai_score": ai_score,
            "xp_awarded": xp_per_person,
            "feedback": ai_feedback,
            "num_collaborators": len(collaborators),
            "screenshots": screenshots,
            "duration_minutes": duration_minutes,
        }
    )
