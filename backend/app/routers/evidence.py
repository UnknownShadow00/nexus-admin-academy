import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.evidence import EvidenceArtifact
from app.models.student import Student
from app.models.ticket import Ticket
from app.services.auth_service import get_current_student
from app.services.evidence_validator import validate_evidence_artifact
from app.services.onboarding_service import get_orientation_lesson
from app.services.progression_service import require_week_reached
from app.utils.responses import ok

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "txt", "log"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "text/plain"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_EVIDENCE_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # Part 9: 10 MB cap


def _upload_dir() -> Path:
    configured = os.getenv("UPLOAD_DIR")
    path = Path(configured) if configured else Path(__file__).resolve().parents[2] / "uploads" / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    ticket_id: int = Form(...),
    artifact_type: str = Form(...),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        if not (ext in {"txt", "log"} and file.content_type == "application/octet-stream"):
            raise HTTPException(status_code=400, detail="Unsupported MIME type")

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    require_week_reached(db, current_student, ticket.week_number)

    storage_name = f"{uuid.uuid4()}.{ext}"
    dest = (_upload_dir() / storage_name).resolve()
    data = await file.read(MAX_UPLOAD_BYTES + 1)  # Part 9: bounded read
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")
    with open(dest, "wb") as handle:
        handle.write(data)

    evidence_types = (ticket.required_evidence or {}).get("evidence_types", [])
    validation_rules = next((e.get("validation", {}) for e in evidence_types if e.get("type") == artifact_type), {})
    validation = validate_evidence_artifact(
        file_path=str(dest),
        artifact_type=artifact_type,
        validation_rules=validation_rules,
        db=db,
    )

    row = EvidenceArtifact(
        student_id=current_student.id,  # Part 9: uploader ownership
        submission_type="ticket",
        submission_id=ticket_id,
        artifact_type=artifact_type,
        storage_key=storage_name,
        original_filename=file.filename,
        file_size_bytes=len(data),
        mime_type=file.content_type,
        checksum=validation["checksum"],
        metadata_json=validation["metadata"],
        validation_status="valid" if validation["valid"] else "suspicious",
        validation_notes="; ".join(validation["issues"]) if validation["issues"] else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ok(
        {
            "artifact_id": row.id,
            "validation": validation,
            "storage_key": row.storage_key,
            "validation_status": row.validation_status,
        }
    )


@router.post("/orientation-upload")
async def upload_orientation_evidence(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Store an optional sample artifact without creating ticket evidence.

    This deliberately bypasses ticket access and ticket-grading paths. The
    artifact remains visible only as a clearly scoped orientation upload.
    """
    lesson = get_orientation_lesson(db)
    if not lesson:
        raise HTTPException(status_code=404, detail="Orientation lesson not found")
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension")
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        if not (ext in {"txt", "log"} and file.content_type == "application/octet-stream"):
            raise HTTPException(status_code=400, detail="Unsupported MIME type")

    storage_name = f"{uuid.uuid4()}.{ext}"
    dest = (_upload_dir() / storage_name).resolve()
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024*1024)} MB limit")
    with open(dest, "wb") as handle:
        handle.write(data)

    validation = validate_evidence_artifact(
        file_path=str(dest),
        artifact_type="orientation_screenshot",
        validation_rules={},
        db=db,
    )
    row = EvidenceArtifact(
        student_id=current_student.id,
        submission_type="orientation",
        submission_id=lesson.id,
        artifact_type="orientation_screenshot",
        storage_key=storage_name,
        original_filename=file.filename,
        file_size_bytes=len(data),
        mime_type=file.content_type,
        checksum=validation["checksum"],
        metadata_json={"scope": "orientation-practice", **validation["metadata"]},
        validation_status="valid" if validation["valid"] else "suspicious",
        validation_notes="; ".join(validation["issues"]) if validation["issues"] else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(
        {
            "artifact_id": row.id,
            "validation_status": row.validation_status,
            "message": "Sample evidence saved. It is only for orientation and is not ticket evidence.",
        }
    )
