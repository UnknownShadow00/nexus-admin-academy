from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.xp_ledger import XPLedger


def award_xp(
    db: Session,
    *,
    student_id: int,
    delta: int,
    source_type: str,
    source_id: int | None,
    description: str,
) -> None:
    if delta == 0:
        return

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise ValueError("Student not found")

    entry = XPLedger(
        student_id=student_id,
        source_type=source_type,
        source_id=source_id,
        delta=delta,
        description=description,
    )
    db.add(entry)
    student.total_xp += delta
