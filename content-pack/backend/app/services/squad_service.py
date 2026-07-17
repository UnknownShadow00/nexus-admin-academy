from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.mastery import StudentDomainMastery
from app.models.student import Student
from app.models.weekly_lead import WeeklyDomainLead
from app.services.mastery_service import DOMAIN_LABELS


def _week_key() -> str:
    now = datetime.utcnow()
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def recompute_weekly_domain_leads(db: Session) -> list[dict]:
    week_key = _week_key()
    db.query(WeeklyDomainLead).filter(WeeklyDomainLead.week_key == week_key).delete()
    db.commit()

    domains = list(DOMAIN_LABELS.keys())
    created = []

    for domain_id in domains:
        top = (
            db.query(StudentDomainMastery)
            .filter(StudentDomainMastery.domain_id == domain_id)
            .order_by(desc(StudentDomainMastery.mastery_percent))
            .first()
        )
        if not top:
            continue

        lead = WeeklyDomainLead(
            week_key=week_key,
            domain_id=domain_id,
            student_id=top.student_id,
            xp_value=int(top.mastery_percent),
            badge_name=f"Lead {DOMAIN_LABELS.get(domain_id, domain_id)} Admin",
        )
        db.add(lead)
        db.flush()

        student = db.query(Student).filter(Student.id == top.student_id).first()
        created.append(
            {
                "week_key": week_key,
                "domain_id": domain_id,
                "domain_name": DOMAIN_LABELS.get(domain_id, domain_id),
                "student_id": top.student_id,
                "student_name": student.name if student else f"Student {top.student_id}",
                "badge_name": lead.badge_name,
                "mastery_percent": round(float(top.mastery_percent or 0), 1),
            }
        )

    db.commit()
    return created


def get_weekly_domain_leads(db: Session, week_key: str | None = None) -> list[dict]:
    wk = week_key or _week_key()
    rows = db.query(WeeklyDomainLead).filter(WeeklyDomainLead.week_key == wk).all()
    out = []
    for row in rows:
        student = db.query(Student).filter(Student.id == row.student_id).first()
        out.append(
            {
                "week_key": row.week_key,
                "domain_id": row.domain_id,
                "domain_name": DOMAIN_LABELS.get(row.domain_id, row.domain_id),
                "student_id": row.student_id,
                "student_name": student.name if student else f"Student {row.student_id}",
                "badge_name": row.badge_name,
                "xp_value": row.xp_value,
            }
        )
    return out
