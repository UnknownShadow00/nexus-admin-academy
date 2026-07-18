from datetime import UTC, datetime, timedelta
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.squad_activity import SquadActivity
from app.models.student import Student
from app.schemas.cli_lab import CliLabCompleteRequest
from app.services.auth_service import get_current_student
from app.services.a_plus_access import require_a_plus_unlocked
from app.services.xp_service import award_xp
from app.utils.responses import ok

router = APIRouter(prefix="/api/cli-labs", tags=["cli-labs"])

CLI_LAB_COMPLETION_XP = 50


def _redact_command(command: str | None) -> str:
    value = str(command or "")
    lower = value.lower()
    if lower.startswith("pc: "):
        return value
    if lower == "[enable password]":
        return "[enable password]"
    if lower.startswith("enable password "):
        return "enable password [redacted]"
    if lower.startswith("enable secret "):
        return "enable secret [redacted]"
    if lower.startswith("password "):
        return "password [redacted]"
    if lower.startswith("username ") and " password " in lower:
        return re.sub(r"(\s+password\s+)\S+", r"\1[redacted]", value, flags=re.IGNORECASE)
    return value


def _redact_command_log(command_log: list[dict]) -> list[dict]:
    return [{**entry, "cmd": _redact_command(entry.get("cmd"))} for entry in command_log]


def _completed_attempts(db: Session, student_id: int, lab_ids: list[str]) -> dict[str, CliLabAttempt]:
    if not lab_ids:
        return {}
    rows = (
        db.query(CliLabAttempt)
        .filter(
            CliLabAttempt.student_id == student_id,
            CliLabAttempt.lab_id.in_(lab_ids),
            CliLabAttempt.completed_at.isnot(None),
        )
        .order_by(CliLabAttempt.completed_at.desc(), CliLabAttempt.id.desc())
        .all()
    )
    attempts: dict[str, CliLabAttempt] = {}
    for row in rows:
        attempts.setdefault(row.lab_id, row)
    return attempts


def _serialize_lab(lab: CliLab, attempt: CliLabAttempt | None = None, include_content: bool = False) -> dict:
    data = {
        "id": lab.id,
        "compartment_id": lab.compartment_id,
        "vendor_id": lab.vendor_id,
        "title": lab.title,
        "difficulty": lab.difficulty,
        "estimated_minutes": lab.est_minutes,
        "order_index": lab.order_index,
        "completed": attempt is not None,
        "completed_at": attempt.completed_at if attempt else None,
        "xp_awarded": attempt.xp_awarded if attempt else 0,
    }
    if include_content:
        data["content"] = lab.content or {}
    return data


@router.get("")
def list_cli_labs(
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    labs = db.query(CliLab).order_by(CliLab.compartment_id.asc(), CliLab.order_index.asc()).all()
    attempts = _completed_attempts(db, current_student.id, [lab.id for lab in labs])
    data = [_serialize_lab(lab, attempts.get(lab.id)) for lab in labs]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{lab_id}")
def get_cli_lab(
    lab_id: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = db.query(CliLab).filter(CliLab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="CLI lab not found")
    attempt = _completed_attempts(db, current_student.id, [lab.id]).get(lab.id)
    return ok(_serialize_lab(lab, attempt, include_content=True))


@router.post("/{lab_id}/complete")
def complete_cli_lab(
    lab_id: str,
    payload: CliLabCompleteRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    require_a_plus_unlocked(db, current_student)
    lab = db.query(CliLab).filter(CliLab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="CLI lab not found")

    prior_completed = (
        db.query(CliLabAttempt)
        .filter(
            CliLabAttempt.student_id == current_student.id,
            CliLabAttempt.lab_id == lab.id,
            CliLabAttempt.completed_at.isnot(None),
        )
        .first()
    )

    now = datetime.now(UTC)
    started_at = None
    if payload.duration_ms is not None:
        started_at = now - timedelta(milliseconds=payload.duration_ms)

    xp_awarded = 0 if prior_completed else CLI_LAB_COMPLETION_XP
    attempt = CliLabAttempt(
        student_id=current_student.id,
        lab_id=lab.id,
        started_at=started_at,
        completed_at=now,
        xp_awarded=xp_awarded,
        duration_ms=payload.duration_ms,
        command_log=_redact_command_log(payload.command_log),
    )
    db.add(attempt)
    db.flush()

    if xp_awarded > 0:
        award_xp(
            db,
            student_id=current_student.id,
            delta=xp_awarded,
            source_type="cli_lab",
            source_id=None,
            description=f"CLI Lab: {lab.title}",
        )

    current_student.last_active_at = now
    db.add(
        SquadActivity(
            student_id=current_student.id,
            activity_type="cli_lab_completed",
            title=lab.title[:200],
            detail=f"{xp_awarded} XP awarded" if xp_awarded else "Completed again, no duplicate XP",
        )
    )
    db.commit()
    db.refresh(attempt)

    return ok(
        {
            "attempt_id": attempt.id,
            "lab_id": lab.id,
            "completed": True,
            "completed_at": attempt.completed_at,
            "xp_awarded": xp_awarded,
            "duplicate_completion": prior_completed is not None,
        }
    )
