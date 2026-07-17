from sqlalchemy.orm import Session

from app.models.mastery import StudentDomainMastery

DOMAIN_LABELS = {
    "1.0": "Hardware",
    "2.0": "Networking",
    "3.0": "Software Troubleshooting",
    "4.0": "Security / Procedures",
}


def _get_or_create(db: Session, student_id: int, domain_id: str) -> StudentDomainMastery:
    row = (
        db.query(StudentDomainMastery)
        .filter(StudentDomainMastery.student_id == student_id, StudentDomainMastery.domain_id == domain_id)
        .first()
    )
    if row:
        return row
    row = StudentDomainMastery(student_id=student_id, domain_id=domain_id)
    db.add(row)
    db.flush()
    return row


def _recalc(row: StudentDomainMastery) -> None:
    quiz_avg = (row.quiz_score_total / row.quiz_attempts) if row.quiz_attempts else 0
    ticket_avg = (row.ticket_score_total / row.ticket_attempts) if row.ticket_attempts else 0
    weighted = ((quiz_avg * 1) + (ticket_avg * 2)) / 3
    row.mastery_percent = min(100.0, max(0.0, weighted * 10))


def record_quiz_mastery(db: Session, student_id: int, domain_id: str, score: int) -> None:
    row = _get_or_create(db, student_id, domain_id)
    row.quiz_score_total += float(score)
    row.quiz_attempts += 1
    _recalc(row)
    db.commit()


def record_ticket_mastery_verified(db: Session, student_id: int, domain_id: str, score: int) -> None:
    row = _get_or_create(db, student_id, domain_id)
    row.ticket_score_total += float(score)
    row.ticket_attempts += 1
    _recalc(row)
    db.commit()


def list_student_mastery(db: Session, student_id: int) -> list[dict]:
    rows = db.query(StudentDomainMastery).filter(StudentDomainMastery.student_id == student_id).all()
    output = []
    for row in rows:
        output.append(
            {
                "domain_id": row.domain_id,
                "domain_name": DOMAIN_LABELS.get(row.domain_id, row.domain_id),
                "mastery_percent": round(float(row.mastery_percent or 0), 1),
                "quiz_attempts": row.quiz_attempts,
                "ticket_attempts": row.ticket_attempts,
            }
        )
    return output
