from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson, Module
from app.models.progression import PromotionGate, Role
from app.models.quiz import Quiz, QuizAttempt
from app.models.ticket import Ticket, TicketSubmission


def check_module_unlock(student_id: int, module_id: int, db: Session) -> dict:
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        return {"unlocked": False, "requirements_missing": ["Module not found"]}

    requirements_missing = []
    if module.prerequisite_module_id:
        prereq_mastery = get_module_mastery(student_id, module.prerequisite_module_id, db)
        if prereq_mastery < (module.unlock_threshold or 70):
            requirements_missing.append(
                f"Need {module.unlock_threshold}% mastery in prerequisite (current: {prereq_mastery}%)"
            )

    return {"unlocked": len(requirements_missing) == 0, "requirements_missing": requirements_missing}


def get_module_mastery(student_id: int, module_id: int, db: Session) -> float:
    lessons = db.query(Lesson).filter(Lesson.module_id == module_id).all()
    if not lessons:
        return 0.0

    total_score = 0.0
    for lesson in lessons:
        quiz_avg = (
            db.query(func.coalesce(func.avg(QuizAttempt.score), 0))
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .filter(QuizAttempt.student_id == student_id, Quiz.lesson_id == lesson.id)
            .scalar()
            or 0
        )

        ticket_avg = (
            db.query(func.coalesce(func.avg(TicketSubmission.final_score), 0))
            .join(Ticket, TicketSubmission.ticket_id == Ticket.id)
            .filter(TicketSubmission.student_id == student_id, Ticket.lesson_id == lesson.id, TicketSubmission.status == "verified")
            .scalar()
            or 0
        )

        lab_avg = (
            db.query(func.coalesce(func.avg(LabRun.final_score), 0))
            .join(LabTemplate, LabRun.lab_template_id == LabTemplate.id)
            .filter(LabRun.student_id == student_id, LabTemplate.lesson_id == lesson.id)
            .scalar()
            or 0
        )

        lesson_score = (float(quiz_avg) * 0.3) + (float(ticket_avg) * 0.4) + (float(lab_avg) * 0.3)
        total_score += lesson_score

    return round((total_score / len(lessons)) * 10, 1)


def check_promotion_eligibility(student_id: int, target_role_id: int, db: Session) -> dict:
    gates = db.query(PromotionGate).filter(PromotionGate.role_id == target_role_id).all()
    requirements_met = []
    requirements_missing = []

    for gate in gates:
        req_type = gate.requirement_type
        config = gate.requirement_config or {}
        if req_type == "min_verified_tickets_by_difficulty":
            result = _check_ticket_requirement(student_id, config, db)
        elif req_type == "min_mastery_by_domain":
            result = _check_mastery_requirement(student_id, config, db)
        else:
            continue

        if result["met"]:
            requirements_met.append(result)
        else:
            requirements_missing.append(result)

    completion_percent = (len(requirements_met) / len(gates) * 100) if gates else 0
    return {
        "eligible": len(requirements_missing) == 0,
        "requirements_met": requirements_met,
        "requirements_missing": requirements_missing,
        "completion_percent": round(completion_percent, 1),
    }


def get_promotion_status(student_id: int, db: Session) -> dict:
    from app.models.student import Student

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"current_role": None, "next_role": None, "eligibility": None}

    current_role = None
    if student.current_role_id:
        current_role = db.query(Role).filter(Role.id == student.current_role_id).first()
    if current_role is None:
        current_role = db.query(Role).order_by(Role.rank_order.asc()).first()

    next_role = None
    if current_role:
        next_role = db.query(Role).filter(Role.rank_order == current_role.rank_order + 1).first()

    eligibility = check_promotion_eligibility(student_id, next_role.id, db) if next_role else None
    return {
        "current_role": _role_dict(current_role),
        "next_role": _role_dict(next_role),
        "eligibility": eligibility,
    }


def _role_dict(role: Role | None) -> dict | None:
    if role is None:
        return None
    return {
        "id": role.id,
        "name": role.name,
        "rank_order": role.rank_order,
        "description": role.description,
    }


def _check_ticket_requirement(student_id: int, config: dict, db: Session) -> dict:
    thresholds = (config or {}).get("thresholds", {})
    progress = {}
    met = True
    for difficulty, required in thresholds.items():
        current = (
            db.query(func.count(TicketSubmission.id))
            .join(Ticket, TicketSubmission.ticket_id == Ticket.id)
            .filter(
                TicketSubmission.student_id == student_id,
                TicketSubmission.status == "verified",
                Ticket.difficulty == int(difficulty),
            )
            .scalar()
            or 0
        )
        progress[str(difficulty)] = {"current": int(current), "required": int(required)}
        if int(current) < int(required):
            met = False
    return {
        "type": "min_verified_tickets_by_difficulty",
        "description": "Verified tickets by difficulty",
        "progress": progress,
        "met": met,
    }


def _check_mastery_requirement(student_id: int, config: dict, db: Session) -> dict:
    from app.models.mastery import StudentDomainMastery

    thresholds = (config or {}).get("thresholds", {})
    aliases = {
        "hardware": "1.0",
        "networking": "2.0",
        "software_troubleshooting": "3.0",
        "security": "4.0",
        "procedures": "4.0",
    }
    progress = {}
    met = True
    for domain, required in thresholds.items():
        resolved_domain = aliases.get(str(domain).lower(), str(domain))
        row = (
            db.query(StudentDomainMastery)
            .filter(
                StudentDomainMastery.student_id == student_id,
                StudentDomainMastery.domain_id == resolved_domain,
            )
            .first()
        )
        current = float(row.mastery_percent) if row else 0.0
        progress[str(domain)] = {"current": round(current, 1), "required": int(required)}
        if current < int(required):
            met = False
    return {
        "type": "min_mastery_by_domain",
        "description": "Mastery by domain",
        "progress": progress,
        "met": met,
    }
