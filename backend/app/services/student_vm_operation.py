"""Database-backed serialization for student deletion and VM assignment creation."""

import uuid

from sqlalchemy.orm import Session

from app.models.student import Student


def acquire_student_vm_operation(db: Session, student_id: int) -> str | None:
    """Atomically acquire a durable per-student lease, including on SQLite."""
    token = str(uuid.uuid4())
    acquired = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.vm_operation_lock.is_(None),
        )
        .update({Student.vm_operation_lock: token}, synchronize_session=False)
    )
    db.commit()
    return token if acquired == 1 else None


def release_student_vm_operation(db: Session, student_id: int, token: str) -> None:
    """Release only the lease owned by this operation."""
    db.query(Student).filter(
        Student.id == student_id,
        Student.vm_operation_lock == token,
    ).update({Student.vm_operation_lock: None}, synchronize_session=False)
    db.commit()
