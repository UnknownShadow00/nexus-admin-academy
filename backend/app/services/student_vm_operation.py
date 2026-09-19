"""Database-backed serialization for student deletion and VM assignment creation."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.student import Student

_LEASE_TTL = timedelta(minutes=30)


def acquire_student_vm_operation(db: Session, student_id: int) -> str | None:
    """Atomically acquire or reclaim a per-student lease, including on SQLite."""
    token = str(uuid.uuid4())
    now = datetime.now(UTC)
    expired_before = now - _LEASE_TTL
    acquired = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            or_(
                Student.vm_operation_lock.is_(None),
                Student.vm_operation_lock_at.is_(None),
                Student.vm_operation_lock_at < expired_before,
            ),
        )
        .update(
            {
                Student.vm_operation_lock: token,
                Student.vm_operation_lock_at: now,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    return token if acquired == 1 else None


def release_student_vm_operation(db: Session, student_id: int, token: str) -> None:
    """Release only the lease owned by this operation."""
    db.query(Student).filter(
        Student.id == student_id,
        Student.vm_operation_lock == token,
    ).update(
        {
            Student.vm_operation_lock: None,
            Student.vm_operation_lock_at: None,
        },
        synchronize_session=False,
    )
    db.commit()
