import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.schemas.ticket import TicketSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.methodology_enforcer import can_access_tickets
from app.services.ticket_grader import grade_ticket_submission, grade_ticket_with_answer_key
from app.utils.responses import ok

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024


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


def _build_itil_writeup(payload: TicketSubmitRequest) -> str:
    return (
        f"Symptom:\n{payload.symptom.strip()}\n\n"
        f"Root Cause:\n{payload.root_cause.strip()}\n\n"
        f"Resolution:\n{payload.resolution.strip()}\n\n"
        f"Verification:\n{payload.verification.strip()}"
    )


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

    return ok({"files": saved})


@router.get("")
def get_tickets(week_number: int | None = None, student_id: int | None = None, db: Session = Depends(get_db)):
    if student_id is not None:
        access_check = can_access_tickets(student_id, db)
        if not access_check["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Complete troubleshooting methodology training first",
                    "code": "METHODOLOGY_REQUIRED",
                    "missing_frameworks": access_check["missing_frameworks"],
                },
            )

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
        else:
            status = sub.status or "pending"
            score = sub.final_score if sub.final_score is not None else sub.ai_score
            xp = sub.xp_awarded if sub.xp_granted else 0
            submission_id = sub.id

        data.append(
            {
                "id": t.id,
                "title": t.title,
                "difficulty": t.difficulty,
                "week_number": t.week_number,
                "category": t.category or "general",
                "domain_id": t.domain_id,
                "lesson_id": t.lesson_id,
                "status": status,
                "score": score,
                "xp": xp,
                "xp_granted": sub.xp_granted if sub else False,
                "submission_id": submission_id,
            }
        )

    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{ticket_id}")
def get_ticket_details(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ok(
        {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "difficulty": ticket.difficulty,
            "week_number": ticket.week_number,
            "category": ticket.category or "general",
            "domain_id": ticket.domain_id,
            "lesson_id": ticket.lesson_id,
            "required_evidence": ticket.required_evidence or {},
        }
    )


@router.post("/{ticket_id}/submit")
async def submit_ticket(ticket_id: int, payload: TicketSubmitRequest, db: Session = Depends(get_db)):
    student_id = payload.student_id
    access_check = can_access_tickets(student_id, db)
    if not access_check["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Complete troubleshooting methodology training first",
                "code": "METHODOLOGY_REQUIRED",
                "missing_frameworks": access_check["missing_frameworks"],
            },
        )

    collaborators = _validate_collaborators(db, student_id, payload.collaborator_ids or [])
    duration_minutes = payload.duration_minutes

    writeup = _build_itil_writeup(payload)

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    mark_student_active(db, student_id)

    existing = db.query(TicketSubmission).filter(TicketSubmission.student_id == student_id, TicketSubmission.ticket_id == ticket_id).first()
    if existing and existing.status == "passed":
        raise HTTPException(status_code=400, detail="This ticket has already been passed. Contact instructor for review.")

    try:
        if ticket.required_checkpoints or ticket.scoring_anchors or ticket.root_cause:
            grading = await grade_ticket_with_answer_key(
                ticket_id=ticket_id,
                ticket_title=ticket.title,
                root_cause=ticket.root_cause,
                required_checkpoints=ticket.required_checkpoints,
                scoring_anchors=ticket.scoring_anchors,
                student_writeup=writeup,
                db=db,
                student_id=student_id,
            )
        else:
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

    ai_score = grading["final_score"]
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
        existing.commands_used = payload.commands_used
        existing.before_screenshot_id = payload.before_screenshot_id
        existing.after_screenshot_id = payload.after_screenshot_id
        existing.evidence_complete = bool(payload.before_screenshot_id and payload.after_screenshot_id)
        existing.collaborator_ids = collaborators
        existing.ai_score = ai_score
        existing.structure_score = grading["structure_score"]
        existing.technical_score = grading["technical_score"]
        existing.communication_score = grading["communication_score"]
        existing.final_score = grading["final_score"]
        existing.ai_feedback = ai_feedback
        existing.xp_awarded = xp_per_person
        existing.xp_granted = False
        existing.status = "pending"
        existing.graded_at = datetime.utcnow()
        existing.verified_at = None
        existing.verified_by = None
        existing.duration_minutes = duration_minutes
        if duration_minutes is not None and existing.started_at is None:
            existing.started_at = existing.submitted_at
    else:
        new_sub = TicketSubmission(
            student_id=student_id,
            ticket_id=ticket_id,
            writeup=writeup,
            commands_used=payload.commands_used,
            before_screenshot_id=payload.before_screenshot_id,
            after_screenshot_id=payload.after_screenshot_id,
            evidence_complete=bool(payload.before_screenshot_id and payload.after_screenshot_id),
            collaborator_ids=collaborators,
            ai_score=ai_score,
            structure_score=grading["structure_score"],
            technical_score=grading["technical_score"],
            communication_score=grading["communication_score"],
            final_score=grading["final_score"],
            ai_feedback=ai_feedback,
            xp_awarded=xp_per_person,
            xp_granted=False,
            status="pending",
            graded_at=datetime.utcnow(),
            duration_minutes=duration_minutes,
        )
        db.add(new_sub)
        db.flush()
        submission_id = new_sub.id

    log_activity(
        db,
        student_id,
        "ticket_submitted",
        ticket.title,
        "Awaiting instructor verification",
    )

    return ok(
        {
            "submission_id": submission_id,
            "ai_score": ai_score,
            "structure_score": grading["structure_score"],
            "technical_score": grading["technical_score"],
            "communication_score": grading["communication_score"],
            "final_score": grading["final_score"],
            "xp_awarded": xp_per_person,
            "xp_granted": False,
            "status": "pending",
            "message": "Awaiting Instructor Verification",
            "feedback": ai_feedback,
            "checkpoints_met": grading.get("checkpoints_met", []),
            "checkpoints_missed": grading.get("checkpoints_missed", []),
            "num_collaborators": len(collaborators),
            "evidence_complete": bool(payload.before_screenshot_id and payload.after_screenshot_id),
            "before_screenshot_id": payload.before_screenshot_id,
            "after_screenshot_id": payload.after_screenshot_id,
            "duration_minutes": duration_minutes,
        }
    )
