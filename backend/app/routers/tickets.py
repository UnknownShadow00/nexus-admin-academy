import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.models.evidence import EvidenceArtifact
from app.models.ticket import Ticket, TicketSubmission
from app.schemas.ticket import TicketSubmitRequest
from app.services.activity_service import log_activity, mark_student_active
from app.services.ticket_params import resolve_parameters, substitute, substitute_list
from app.services.auth_service import ensure_student_access, get_current_student
from app.services.ticket_grader import grade_ticket_submission, grade_ticket_with_answer_key
from app.services.a_plus_access import require_a_plus_unlocked
from app.utils.responses import ok

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 20 * 1024 * 1024


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
async def upload_screenshots(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    require_a_plus_unlocked(db, current_student)
    upload_dir = _get_upload_dir()
    saved = []
    total_size = 0

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type (jpg, jpeg, png, webp only)")
        if file.content_type not in ALLOWED_MIMES:
            raise HTTPException(status_code=400, detail="Invalid MIME type")

        contents = await file.read(MAX_FILE_SIZE + 1)
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")
        if total_size + len(contents) > MAX_TOTAL_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="Too many files or combined size too large")
        total_size += len(contents)

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
def get_tickets(week_number: int | None = None, student_id: int | None = None, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    scoped_student_id = student_id or current_student.id
    ensure_student_access(current_student, scoped_student_id)
    query = db.query(Ticket)
    if week_number is not None:
        query = query.filter(Ticket.week_number == week_number)
    tickets = query.order_by(Ticket.created_at.desc()).all()

    submissions = {}
    if scoped_student_id is not None:
        rows = db.query(TicketSubmission).filter(TicketSubmission.student_id == scoped_student_id).all()
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
def get_ticket_details(ticket_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    values = resolve_parameters(ticket.parameters, current_student.id)  # TB-05
    # Student-safe fields only: checkpoints are intentional guidance (Phase A
    # guided tickets); scoring_anchors/root_cause/model_answer stay server-side
    # because the five-anchor texts describe the expected root cause.
    checkpoints = ticket.required_checkpoints or {}
    if isinstance(checkpoints, dict) and checkpoints.get("checkpoints"):
        checkpoints = {
            "checkpoints": [
                {**c, "step": substitute(str(c.get("step", "")), values)}
                for c in checkpoints["checkpoints"]
            ]
        }
    sub = (
        db.query(TicketSubmission)
        .filter(TicketSubmission.student_id == current_student.id, TicketSubmission.ticket_id == ticket_id)
        .first()
    )
    hints = list(ticket.hints or [])
    hints_used = (sub.hints_used if sub else 0) or 0
    return ok(
        {
            "id": ticket.id,
            "title": substitute(ticket.title, values),
            "description": substitute(ticket.description, values),
            "difficulty": ticket.difficulty,
            "week_number": ticket.week_number,
            "category": ticket.category or "general",
            "domain_id": ticket.domain_id,
            "lesson_id": ticket.lesson_id,
            "required_evidence": ticket.required_evidence or {},
            "required_checkpoints": checkpoints,
            "grading_rubric": [
                "investigation", "root_cause", "safe_fix_or_escalation",
                "verification", "communication",
            ],
            "hints_total": len(hints),
            "hints_used": hints_used,
            "hints_revealed": substitute_list(hints[:hints_used], values),
        }
    )



# ---------------------------------------------------------------- TB-04: hints

HINT_PENALTIES = [0.05, 0.10, 0.20, 0.35]  # cumulative-by-count XP reduction
HINT_XP_FLOOR = 0.40  # student always keeps at least 40% of earned XP


def hint_multiplier(hints_used: int) -> float:
    """XP multiplier for a submission that revealed N hints.

    Penalty is the ladder value for the DEEPEST hint revealed (not summed):
    1 hint → −5%, 2 → −10%, 3 → −20%, 4 → −35%. Floor at 40%.
    """
    if hints_used <= 0:
        return 1.0
    idx = min(hints_used, len(HINT_PENALTIES)) - 1
    return max(1.0 - HINT_PENALTIES[idx], HINT_XP_FLOOR)


@router.post("/{ticket_id}/hint")
def reveal_hint(ticket_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    """Reveal the next hint for the current student's active work on this ticket.

    Tracks reveals on an in_progress submission row (created on first reveal)
    so the penalty survives refreshes and applies at grading time. The response
    always states the XP cost BEFORE the next hint can be requested.
    """
    require_a_plus_unlocked(db, current_student)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    hints = list(ticket.hints or [])
    if not hints:
        raise HTTPException(status_code=404, detail="This ticket has no hints")

    sub = (
        db.query(TicketSubmission)
        .filter(TicketSubmission.student_id == current_student.id, TicketSubmission.ticket_id == ticket_id)
        .first()
    )
    if sub and sub.status == "passed":
        raise HTTPException(status_code=400, detail="Ticket already passed — hints unavailable")

    if sub is None:
        sub = TicketSubmission(
            student_id=current_student.id,
            ticket_id=ticket_id,
            writeup="",
            xp_awarded=0,
            xp_granted=False,
            status="in_progress",
            hints_used=0,
        )
        db.add(sub)
        db.flush()

    already = sub.hints_used or 0
    if already >= len(hints):
        raise HTTPException(status_code=400, detail="All hints already revealed")

    sub.hints_used = already + 1
    db.commit()

    values = resolve_parameters(ticket.parameters, current_student.id)  # TB-05
    revealed = substitute_list(hints[: sub.hints_used], values)
    next_cost = None
    if sub.hints_used < len(hints):
        next_cost = int(round(HINT_PENALTIES[sub.hints_used] * 100))
    return ok(
        {
            "hints_revealed": revealed,
            "hints_used": sub.hints_used,
            "hints_total": len(hints),
            "current_xp_multiplier": hint_multiplier(sub.hints_used),
            "next_hint_xp_penalty_percent": next_cost,
        }
    )




def _verify_evidence_ownership(db: Session, student_id: int, *artifact_ids: int | None) -> None:
    """Part 9: a submission may only reference the submitter's own artifacts.
    Legacy rows (student_id NULL, pre-fix uploads) are rejected for NEW links —
    students re-upload rather than inherit unowned evidence."""
    for artifact_id in artifact_ids:
        if not artifact_id:
            continue
        row = db.query(EvidenceArtifact).filter(EvidenceArtifact.id == artifact_id).first()
        if row is None or row.student_id != student_id:
            raise HTTPException(status_code=403, detail=f"Evidence artifact {artifact_id} is not yours")

@router.post("/{ticket_id}/submit")
async def submit_ticket(ticket_id: int, payload: TicketSubmitRequest, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    require_a_plus_unlocked(db, current_student)
    student_id = payload.student_id
    ensure_student_access(current_student, student_id)
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

    _verify_evidence_ownership(db, student_id, payload.before_screenshot_id, payload.after_screenshot_id)  # Part 9
    param_values = resolve_parameters(ticket.parameters, student_id)  # TB-05
    try:
        if ticket.required_checkpoints or ticket.scoring_anchors or ticket.root_cause:
            grading = await grade_ticket_with_answer_key(
                ticket_id=ticket_id,
                ticket_title=substitute(ticket.title, param_values),
                root_cause=substitute(ticket.root_cause, param_values),
                required_checkpoints=[substitute(str(c), param_values) for c in (ticket.required_checkpoints or [])] if isinstance(ticket.required_checkpoints, list) else ticket.required_checkpoints,
                scoring_anchors=ticket.scoring_anchors,
                student_writeup=writeup,
                db=db,
                student_id=student_id,
            )
        else:
            grading = await grade_ticket_submission(
                ticket_id=ticket_id,
                ticket_title=substitute(ticket.title, param_values),
                ticket_description=substitute(ticket.description, param_values),
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
    hints_used_now = existing.hints_used if existing else 0
    xp_per_person = int(base_xp * multiplier * hint_multiplier(hints_used_now or 0))

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
        existing.graded_at = datetime.now(timezone.utc)
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
            graded_at=datetime.now(timezone.utc),
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
            "anchors": grading.get("anchors"),
            "checkpoints_met": grading.get("checkpoints_met", []),
            "checkpoints_missed": grading.get("checkpoints_missed", []),
            "num_collaborators": len(collaborators),
            "evidence_complete": bool(payload.before_screenshot_id and payload.after_screenshot_id),
            "before_screenshot_id": payload.before_screenshot_id,
            "after_screenshot_id": payload.after_screenshot_id,
            "duration_minutes": duration_minutes,
        }
    )
