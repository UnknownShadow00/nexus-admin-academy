from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evidence import EvidenceArtifact
from app.models.student import Student
from app.models.ticket import TicketSubmission

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _ok(data):
    return {"success": True, "data": data}


@router.get("/{submission_id}")
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).filter(TicketSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    collaborators = []
    ids = [int(x) for x in (submission.collaborator_ids or [])]
    if ids:
        collaborators = [s.name for s in db.query(Student).filter(Student.id.in_(ids)).all()]

    avg_duration = (
        db.query(TicketSubmission.duration_minutes)
        .filter(TicketSubmission.ticket_id == submission.ticket_id, TicketSubmission.duration_minutes.isnot(None))
        .all()
    )
    avg_val = 0
    if avg_duration:
        avg_val = round(sum(x[0] for x in avg_duration if x[0] is not None) / max(1, len(avg_duration)), 1)

    payload = {
        "id": submission.id,
        "ticket_id": submission.ticket_id,
        "ticket_title": submission.ticket.title if submission.ticket else "Ticket",
        "writeup": submission.writeup,
        "ai_score": submission.final_score if submission.final_score is not None else submission.ai_score,
        "structure_score": submission.structure_score,
        "technical_score": submission.technical_score,
        "communication_score": submission.communication_score,
        "final_score": submission.final_score,
        "ai_feedback": submission.ai_feedback,
        "xp_awarded": submission.xp_awarded,
        "xp_granted": submission.xp_granted,
        "status": submission.status,
        "before_screenshot_id": submission.before_screenshot_id,
        "after_screenshot_id": submission.after_screenshot_id,
        "evidence_complete": submission.evidence_complete,
        "collaborator_names": collaborators,
        "duration_minutes": submission.duration_minutes,
        "avg_duration": avg_val,
        "admin_comment": submission.admin_comment,
        "verified_at": submission.verified_at,
    }
    evidence_ids = [x for x in [submission.before_screenshot_id, submission.after_screenshot_id] if x]
    if evidence_ids:
        artifacts = db.query(EvidenceArtifact).filter(EvidenceArtifact.id.in_(evidence_ids)).all()
        payload["evidence_artifacts"] = [
            {
                "id": a.id,
                "artifact_type": a.artifact_type,
                "storage_key": a.storage_key,
                "validation_status": a.validation_status,
            }
            for a in artifacts
        ]
    else:
        payload["evidence_artifacts"] = []

    return _ok(payload)
