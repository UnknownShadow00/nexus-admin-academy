from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson, Module
from app.models.progression import PromotionGate, Role
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.services.curriculum_structure import module_for_week
from app.services.quiz_progression import is_quiz_passed, required_quizzes_for_week


# CLI packs and modules carry curriculum timing outside their database models.
# Keep this mapping alongside the derived-week rule so all progression checks
# use one source of truth.
CLI_PACK_WEEKS = {
    "meet-the-cli": 1,
    "network-foundations": 9,
    "learn-switching": 10,
}

MODULE_WEEKS = {
    "MOD-000": 0,
    "MOD-001": 1,
    "MOD-002": 2,
    "MOD-003": 3,
    "MOD-004": 4,
    "MOD-005": 5,
    "MOD-006": 6,
    "MOD-007": 7,
    "MOD-008": 8,
    "MOD-009": 9,
    "MOD-010": 10,
    "MOD-011": 11,
    "MOD-012": 12,
    "MOD-013": 13,
    "MOD-014": 14,
    "MOD-015": 15,
    "MOD-016": 16,
    "MOD-017": 17,
    "MOD-018": 18,
    "MOD-019": 19,
    "MOD-020": 20,
    "MOD-021": 21,
    "MOD-022": 22,
    "MOD-023": 23,
    "MOD-024": 24,
    # Phase 4B.1 Microsoft Workplace stage. New week_number values only --
    # existing MOD-000..024/week 0-24 are never renumbered. See
    # docs/MICROSOFT_WORKPLACE_CURRICULUM.md "Dual progression systems" for
    # why this range must stay derived from MODULE_WEEKS rather than
    # hardcoded: legacy System B (this module, and
    # service_desk_progression.SERVICE_DESK_PACKS/curriculum_unlocked_keys)
    # previously assumed valid curriculum ended at week 24, which would have
    # made required Microsoft-stage content silently unreachable/ungraded by
    # every check in this file.
    "MOD-025": 25,
    "MOD-026": 26,
    "MOD-027": 27,
    "MOD-028": 28,
    "MOD-029": 29,
    # Phase 4B.2 (Intune & endpoint management) -- same reasoning as above,
    # range(max(MODULE_WEEKS.values()) + 1) below already generalizes, so
    # this extension needs no other code change here.
    "MOD-030": 30,
    "MOD-031": 31,
    "MOD-032": 32,
    "MOD-033": 33,
    "MOD-034": 34,
}


def derive_current_week(student_id: int, db: Session) -> int:
    """Return the earliest curriculum week with incomplete required work."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is not None:
        # Local import avoids the training_service -> progression_service
        # module cycle. The helper disables Service Desk availability lookup,
        # so this call cannot recurse through service_desk_progression.
        from app.services.training_service import derive_training_current_week

        current_week = derive_training_current_week(db, student)
        if current_week is not None:
            return current_week

    # Compatibility for pre-0032 databases and focused unit fixtures that do
    # not have TrainingWeek rows yet.
    from app.models.lesson_progress import StudentLessonProgress

    for week in range(max(MODULE_WEEKS.values()) + 1):
        codes = [code for code, mapped_week in MODULE_WEEKS.items() if mapped_week == week]
        lesson_ids = set()
        if codes:
            module_ids = {row.id for row in db.query(Module.id).filter(Module.code.in_(codes))}
            if module_ids:
                lesson_ids = {
                    row.id
                    for row in db.query(Lesson.id).filter(
                        Lesson.module_id.in_(module_ids), Lesson.status == "published"
                    )
                }
        done = set()
        if lesson_ids:
            done = {
                row.lesson_id
                for row in db.query(StudentLessonProgress.lesson_id).filter(
                    StudentLessonProgress.student_id == student_id,
                    StudentLessonProgress.lesson_id.in_(lesson_ids),
                    StudentLessonProgress.completed_at.isnot(None),
                )
            }
        required_incomplete = any(
            not is_quiz_passed(db, student_id, quiz)
            for quiz in required_quizzes_for_week(db, week)
        )
        if lesson_ids - done or required_incomplete:
            return week
    return max(MODULE_WEEKS.values())


def week_has_been_reached(db: Session, current_week: int, required_week: int) -> bool:
    """Compare source weeks by the canonical TrainingWeek display sequence."""
    from app.models.training import TrainingWeek

    rows = (
        db.query(TrainingWeek.week_number, TrainingWeek.display_order)
        .filter(
            TrainingWeek.is_active.is_(True),
            TrainingWeek.week_number.in_({int(current_week), int(required_week)}),
        )
        .all()
    )
    positions = {week_number: display_order for week_number, display_order in rows}
    if current_week in positions and required_week in positions:
        return positions[required_week] <= positions[current_week]
    return int(required_week) <= int(current_week)


def has_reached_week(db: Session, student_id: int, required_week: int) -> bool:
    return week_has_been_reached(
        db, derive_current_week(student_id, db), int(required_week or 0)
    )


def _week_is_beyond_next(db: Session, current_week: int, required_week: int) -> bool:
    """Return whether required_week is more than one curriculum step ahead."""
    from app.models.training import TrainingWeek

    ordered = [
        week_number
        for (week_number,) in db.query(TrainingWeek.week_number)
        .filter(TrainingWeek.is_active.is_(True))
        .order_by(TrainingWeek.display_order, TrainingWeek.week_number)
        .all()
    ]
    if current_week in ordered and required_week in ordered:
        return ordered.index(required_week) > ordered.index(current_week) + 1
    return int(required_week) > int(current_week) + 1


def require_week_reached(db: Session, student, required_week: int) -> dict:
    """Require the student to have reached an item's curriculum week.

    The raised detail is deliberately a complete API contract; the application
    HTTP exception handler returns it as the JSON response body.
    """
    required_week = int(required_week or 0)
    if student.is_mentor:
        return {"required_week": required_week, "current_week": required_week}

    current_week = derive_current_week(student.id, db)
    if week_has_been_reached(db, current_week, required_week):
        return {"required_week": required_week, "current_week": current_week}

    from app.models.lesson_progress import StudentLessonProgress

    codes = [code for code, mapped_week in MODULE_WEEKS.items() if mapped_week == current_week]
    week_lesson_ids = {
        row.id
        for row in db.query(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.code.in_(codes), Lesson.status == "published")
    } if codes else set()
    completed_lesson_ids = {
        row.lesson_id
        for row in db.query(StudentLessonProgress.lesson_id).filter(
            StudentLessonProgress.student_id == student.id,
            StudentLessonProgress.lesson_id.in_(week_lesson_ids),
            StudentLessonProgress.completed_at.isnot(None),
        )
    } if week_lesson_ids else set()
    lesson_incomplete = bool(week_lesson_ids - completed_lesson_ids)
    incomplete_quiz = next(
        (quiz for quiz in required_quizzes_for_week(db, current_week) if not is_quiz_passed(db, student.id, quiz)),
        None,
    )
    current_module = module_for_week(current_week)
    required_module = module_for_week(required_week)
    current_label = current_module.title if current_module else "the current training section"
    required_label = required_module.title if required_module else "the requested training section"
    if lesson_incomplete and incomplete_quiz is not None:
        error = f"Complete the required lesson and quiz in {current_label} first."
        next_action_route = "/training"
    elif incomplete_quiz is not None:
        error = f"Complete the required quiz in {current_label} first."
        next_action_route = f"/quizzes/{incomplete_quiz.id}"
    elif _week_is_beyond_next(db, current_week, required_week):
        error = f"You'll unlock this when you reach {required_label}."
        next_action_route = "/training"
    elif lesson_incomplete:
        error = f"Complete the required lesson in {current_label} first."
        next_action_route = "/training"
    else:
        error = f"Complete the required work in {current_label} first."
        next_action_route = "/training"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "success": False,
            "code": "PREREQUISITE_NOT_MET",
            "error": error,
            "data": {
                "required_week": required_week,
                "current_week": current_week,
                "required_module_id": required_module.stable_id if required_module else None,
                "required_module_title": required_module.title if required_module else None,
                "current_module_id": current_module.stable_id if current_module else None,
                "current_module_title": current_module.title if current_module else None,
                "next_action_route": next_action_route,
            },
        },
    )


def check_module_unlock(student_id: int, module_id: int, db: Session) -> dict:
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        return {"unlocked": False, "requirements_missing": ["Module not found"]}

    requirements_missing = []
    student = db.query(Student).filter(Student.id == student_id).first()
    mapped_week = MODULE_WEEKS.get(module.code)
    if student and not student.is_mentor and mapped_week is not None:
        current_week = derive_current_week(student_id, db)
        if not week_has_been_reached(db, current_week, mapped_week):
            current_module = module_for_week(current_week)
            current_label = current_module.title if current_module else "your current module"
            requirements_missing.append(
                f"Complete {current_label}'s required work first."
            )

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

        lab_avg = (
            db.query(func.coalesce(func.avg(LabRun.final_score), 0))
            .join(LabTemplate, LabRun.lab_template_id == LabTemplate.id)
            .filter(LabRun.student_id == student_id, LabTemplate.lesson_id == lesson.id)
            .scalar()
            or 0
        )

        lesson_score = (float(quiz_avg) * 0.5) + (float(lab_avg) * 0.5)
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
        elif req_type == "min_service_desk_passes":
            result = _check_service_desk_requirement(student_id, config, db)
        elif req_type == "min_mastery_by_domain":
            result = _check_mastery_requirement(student_id, config, db)
        elif req_type == "practical_checkpoint":
            result = _check_practical_checkpoint(student_id, config, db)
        elif req_type == "min_completed_lessons":
            result = _check_lessons_requirement(student_id, config, db)
        elif req_type == "min_cli_labs":
            result = _check_cli_labs_requirement(student_id, config, db)
        elif req_type == "no_unresolved_flags":
            result = _check_no_flags(student_id, config, db)
        elif req_type == "required_quiz":
            result = _check_required_quiz(student_id, config, db)
        elif req_type == "required_lab_pass":
            result = _check_required_lab_pass(student_id, config, db)
        else:
            # Unknown types are ignored for forward-compatibility, and must not
            # count toward the completion denominator (previously they did,
            # silently deflating completion_percent).
            continue

        if result["met"]:
            requirements_met.append(result)
        else:
            requirements_missing.append(result)

    evaluated = len(requirements_met) + len(requirements_missing)
    completion_percent = (len(requirements_met) / evaluated * 100) if evaluated else 0
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


def _check_required_quiz(student_id: int, config: dict, db: Session) -> dict:
    from app.services.quiz_progression import is_quiz_passed, required_quizzes_for_week

    week = int((config or {}).get("week", -1))
    gate_quizzes = [quiz for quiz in required_quizzes_for_week(db, week) if quiz.quiz_purpose == "gate"]
    passed = bool(gate_quizzes) and all(is_quiz_passed(db, student_id, quiz) for quiz in gate_quizzes)
    module = module_for_week(week)
    module_label = module.title if module else "the required training module"
    return {
        "type": "required_quiz",
        "description": f"Pass the {module_label} promotion-gate quiz",
        "progress": {
            "week": week,
            "required": len(gate_quizzes),
            "passed": sum(is_quiz_passed(db, student_id, quiz) for quiz in gate_quizzes),
        },
        "met": passed,
    }


def _check_required_lab_pass(student_id: int, config: dict, db: Session) -> dict:
    """Config: {"lab_id": int, "min_score_pct": int}. Only counts a LabRun
    graded under the versioned rubric it names (structured_feedback.grading
    .rubric_version), so a weaker pre-upgrade completion of the same
    LabTemplate id can never silently satisfy a strengthened requirement —
    see Phase 4C.3's historical-completion policy."""
    cfg = config or {}
    lab_id = cfg.get("lab_id")
    min_score_pct = int(cfg.get("min_score_pct", 100))
    description = "Pass the required final assessment"
    lab = db.query(LabTemplate).filter(LabTemplate.id == lab_id).first() if lab_id else None
    if lab is not None:
        description = f"Pass {lab.title} (≥ {min_score_pct}%)"

    runs = (
        db.query(LabRun)
        .filter(LabRun.lab_template_id == lab_id, LabRun.student_id == student_id, LabRun.status == "submitted")
        .all()
    )
    best_score = 0
    met = False
    for run in runs:
        feedback = run.structured_feedback or {}
        grading = feedback.get("grading") or {}
        if not grading.get("rubric_version", "").startswith("final-shift-"):
            continue
        score = int(run.final_score or 0)
        best_score = max(best_score, score)
        if grading.get("passed") and score >= min_score_pct:
            met = True
    return {
        "type": "required_lab_pass",
        "description": description,
        "progress": {"lab_id": lab_id, "best_score": best_score, "required_score": min_score_pct},
        "met": met,
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
                TicketSubmission.status == "passed",
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


def _check_service_desk_requirement(student_id: int, config: dict, db: Session) -> dict:
    from app.services.service_desk_progression import (
        SERVICE_DESK_PACKS,
        _passed_scenario_keys,
    )

    cfg = config or {}
    pack_key = str(cfg.get("pack_key", ""))
    required = cfg.get("min_passed")
    pack = next((item for item in SERVICE_DESK_PACKS if item.key == pack_key), None)
    # A missing/zero threshold or an unrecognized pack_key is a misconfigured
    # gate, not a satisfied one — fail closed instead of auto-passing on 0 >= 0.
    if pack is None or not isinstance(required, int) or required <= 0:
        return {
            "type": "min_service_desk_passes",
            "description": f"Service Desk scenarios passed in {pack_key or '(unconfigured)'}",
            "progress": {"pack_key": pack_key, "current": 0, "required": required},
            "met": False,
        }
    passed = len(set(pack.scenario_keys) & _passed_scenario_keys(db, student_id))
    return {
        "type": "min_service_desk_passes",
        "description": f"Service Desk scenarios passed in {pack_key}",
        "progress": {
            "pack_key": pack_key,
            "current": passed,
            "required": required,
        },
        "met": passed >= required,
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


# --------------------------------------------------------------------------- 
# TB-02 gate evaluators (Gate 1 / Gate 2). Same contract as the evaluators
# above: return {"type", "description", "progress", "met"}.
# ---------------------------------------------------------------------------

def _check_practical_checkpoint(student_id: int, config: dict, db: Session) -> dict:
    """A designated ticket completed within hint/score limits.

    Config: {"ticket_title": str (substring match) OR "ticket_id": int,
             "max_hints": int (default 0), "min_score": int (default 7)}
    """
    cfg = config or {}
    max_hints = int(cfg.get("max_hints", 0))
    min_score = int(cfg.get("min_score", 7))

    query = (
        db.query(TicketSubmission)
        .join(Ticket, TicketSubmission.ticket_id == Ticket.id)
        .filter(
            TicketSubmission.student_id == student_id,
            TicketSubmission.status == "passed",
        )
    )
    if cfg.get("ticket_id"):
        query = query.filter(Ticket.id == int(cfg["ticket_id"]))
        label = f"ticket #{cfg['ticket_id']}"
    else:
        title = str(cfg.get("ticket_title", ""))
        query = query.filter(Ticket.title.ilike(f"%{title}%"))
        label = f'"{title}"'

    best = None
    for sub in query.all():
        score = sub.final_score if sub.final_score is not None else sub.ai_score
        hints = getattr(sub, "hints_used", 0) or 0  # column lands with TB-04
        if score is not None and score >= min_score and hints <= max_hints:
            best = sub
            break
        if best is None:
            best = sub

    met = bool(
        best
        and (best.final_score if best.final_score is not None else best.ai_score) is not None
        and (best.final_score if best.final_score is not None else best.ai_score) >= min_score
        and (getattr(best, "hints_used", 0) or 0) <= max_hints
    )
    achieved_score = None
    achieved_hints = None
    if best is not None:
        achieved_score = best.final_score if best.final_score is not None else best.ai_score
        achieved_hints = getattr(best, "hints_used", 0) or 0
    return {
        "type": "practical_checkpoint",
        "description": f"Practical checkpoint {label}: score ≥ {min_score} with ≤ {max_hints} hints",
        "progress": {
            "required_min_score": min_score,
            "required_max_hints": max_hints,
            "achieved_score": achieved_score,
            "achieved_hints": achieved_hints,
        },
        "met": met,
    }


def _check_lessons_requirement(student_id: int, config: dict, db: Session) -> dict:
    """Lesson completion = an explicit, server-stored completion record.

    Config: {"weeks": [1,2,3,4]} or {"module_codes": ["MOD-001", ...]}.
    Requires explicit completion for every published lesson in scope, except
    a lesson the weekly curriculum explicitly marks optional (a "lesson"
    TrainingWeekActivity with is_required=False). A lesson with no weekly
    activity row at all stays required, matching legacy/unlinked content.
    Optional content must never silently gate promotion.
    """
    from app.models.lesson_progress import StudentLessonProgress
    from app.models.training import TrainingWeekActivity

    cfg = config or {}
    lesson_query = db.query(Lesson.id).filter(Lesson.status == "published")
    scope_desc = "all published lessons"
    if cfg.get("module_codes"):
        lesson_query = lesson_query.join(Module, Lesson.module_id == Module.id).filter(
            Module.code.in_(list(cfg["module_codes"]))
        )
        scope_desc = f"modules {', '.join(cfg['module_codes'])}"

    all_ids = {row.id for row in lesson_query.all()}
    optional_ids = {
        int(row.content_ref)
        for row in db.query(TrainingWeekActivity.content_ref)
        .filter(TrainingWeekActivity.activity_type == "lesson", TrainingWeekActivity.is_required.is_(False))
        .all()
        if row.content_ref and row.content_ref.isdigit()
    }
    required_ids = all_ids - optional_ids
    done_ids = {
        row.lesson_id
        for row in db.query(StudentLessonProgress.lesson_id)
        .filter(StudentLessonProgress.student_id == student_id, StudentLessonProgress.completed_at.isnot(None))
        .all()
    }
    missing = sorted(required_ids - done_ids)
    return {
        "type": "min_completed_lessons",
        "description": f"Lessons completed for {scope_desc}",
        "progress": {
            "required": len(required_ids),
            "completed": len(required_ids) - len(missing),
            "missing_lesson_ids": missing,
        },
        "met": len(missing) == 0,
    }


def _check_cli_labs_requirement(student_id: int, config: dict, db: Session) -> dict:
    """Config: {"min_completed": int, "pack_prefix": optional str (lab id prefix)}."""
    from app.models.cli_lab import CliLab, CliLabAttempt

    cfg = config or {}
    required = int(cfg.get("min_completed", 0))
    query = (
        db.query(func.count(func.distinct(CliLabAttempt.lab_id)))
        .filter(
            CliLabAttempt.student_id == student_id,
            CliLabAttempt.completed_at.isnot(None),
        )
    )
    if cfg.get("pack_prefix"):
        query = query.join(CliLab, CliLabAttempt.lab_id == CliLab.id).filter(
            CliLab.id.like(f"{cfg['pack_prefix']}%")
        )
    completed = int(query.scalar() or 0)
    return {
        "type": "min_cli_labs",
        "description": f"CLI labs completed (≥ {required})",
        "progress": {"required": required, "completed": completed},
        "met": completed >= required,
    }


def _check_no_flags(student_id: int, config: dict, db: Session) -> dict:
    """No unresolved mentor flags: a flag is a mentor comment on a submission
    that has not been re-reviewed (admin_comment set, admin_reviewed False)."""
    open_flags = (
        db.query(func.count(TicketSubmission.id))
        .filter(
            TicketSubmission.student_id == student_id,
            TicketSubmission.admin_comment.isnot(None),
            TicketSubmission.admin_comment != "",
            TicketSubmission.admin_reviewed.is_(False),
        )
        .scalar()
        or 0
    )
    return {
        "type": "no_unresolved_flags",
        "description": "No unresolved mentor flags",
        "progress": {"open_flags": int(open_flags)},
        "met": int(open_flags) == 0,
    }
