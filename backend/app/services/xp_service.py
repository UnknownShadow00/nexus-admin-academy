from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.student import Student
from app.models.xp_ledger import XPLedger
from app.services.discord_service import check_and_post_milestones


def award_xp(
    db: Session,
    *,
    student_id: int,
    delta: int,
    source_type: str,
    source_id: int | None,
    description: str,
    idempotent: bool = False,
) -> bool:
    if delta == 0:
        return False

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
    if idempotent:
        try:
            # The savepoint contains the uniqueness failure without rolling
            # back the caller's grade/attempt transaction.
            with db.begin_nested():
                db.add(entry)
                db.flush()
        except IntegrityError:
            return False
    else:
        db.add(entry)
    student.total_xp += delta
    check_and_post_milestones(db, student_id, delta)
    return True
