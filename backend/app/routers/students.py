from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.comptia import ComptiaObjective, StudentObjectiveProgress
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.login_streak import LoginStreak
from app.models.progression import MethodologyFramework, StudentMethodologyProgress
from app.models.quiz import (
    QUIZ_PURPOSE_CERTIFICATION,
    QUIZ_PURPOSE_CUMULATIVE,
    QUIZ_PURPOSE_GATE,
    QUIZ_PURPOSE_PRACTICE,
    QUIZ_PURPOSE_REMEDIATION,
    Quiz,
    QuizAttempt,
)
from app.models.student import Student
from app.models.service_desk import ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.squad_activity import SquadActivity
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.activity_service import mark_student_active
from app.services.auth_service import ensure_student_access, ensure_student_ownership, get_current_student
from app.services.mastery_service import list_student_mastery
from app.services.methodology_enforcer import can_access_tickets
from app.services.onboarding_service import get_orientation_state
from app.services.progression_service import (
    CLI_PACK_WEEKS,
    MODULE_WEEKS,
    check_module_unlock,
    derive_current_week,
    get_module_mastery,
    get_promotion_status,
)
from app.services.quiz_progression import (
    assigned_remediation_ids,
    is_quiz_passed,
    required_quizzes_for_week,
    triggered_remediation_ids,
)
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.squad_service import get_weekly_domain_leads
from app.services.xp_calculator import level_from_xp
from app.utils.responses import ok

router = APIRouter(tags=["students"])


def update_login_streak(db: Session, student_id: int) -> LoginStreak:
    today = date.today()
    streak = db.query(LoginStreak).filter(LoginStreak.student_id == student_id).first()

    if streak is None:
        streak = LoginStreak(student_id=student_id, current_streak=1, longest_streak=1, last_login=today)
        db.add(streak)
        try:
            db.commit()
        except IntegrityError:
            # Two Home requests can arrive together (for example React strict
            # mode or two tabs). The unique student row may be created by the
            # other request after our initial read; recover by loading it.
            db.rollback()
            concurrent = db.query(LoginStreak).filter(LoginStreak.student_id == student_id).first()
            if concurrent is None:
                raise
            return concurrent
        db.refresh(streak)
        return streak

    if streak.last_login == today:
        return streak

    if streak.last_login == today - timedelta(days=1):
        streak.current_streak += 1
        streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    else:
        streak.current_streak = 1

    streak.last_login = today
    db.commit()
    db.refresh(streak)
    return streak


def _build_cert_readiness(student_id: int, db: Session) -> dict:
    total_objectives = db.query(func.count(ComptiaObjective.id)).scalar() or 0

    mastery_rows = (
        db.query(
            ComptiaObjective.domain.label("domain"),
            func.coalesce(func.avg(StudentObjectiveProgress.mastery_level), 0).label("avg_mastery"),
        )
        .outerjoin(
            StudentObjectiveProgress,
            (ComptiaObjective.id == StudentObjectiveProgress.objective_id)
            & (StudentObjectiveProgress.student_id == student_id),
        )
        .group_by(ComptiaObjective.domain)
        .order_by(ComptiaObjective.domain)
        .all()
    )

    overall = (
        db.query(func.coalesce(func.avg(StudentObjectiveProgress.mastery_level), 0))
        .filter(StudentObjectiveProgress.student_id == student_id)
        .scalar()
        or 0
    )

    return {
        "overall_readiness": round(float(overall), 1),
        "by_domain": [{"domain": row.domain, "readiness": round(float(row.avg_mastery), 1)} for row in mastery_rows],
        "total_objectives": int(total_objectives),
    }


@router.post("/api/students/{student_id}/check-in")
def student_check_in(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_ownership(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    mark_student_active(db, student_id)
    streak = update_login_streak(db, student_id)
    return {"success": True, "streak": streak.current_streak, "longest_streak": streak.longest_streak}


@router.get("/api/students/{student_id}/dashboard")
def get_student_dashboard(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    level, level_name = level_from_xp(student.total_xp)

    recent_entries = (
        db.query(XPLedger)
        .filter(XPLedger.student_id == student_id)
        .order_by(XPLedger.created_at.desc())
        .limit(5)
        .all()
    )

    quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).all()
    service_desk_completed = (
        db.query(func.count(ServiceDeskAttempt.id))
        .filter(ServiceDeskAttempt.student_id == student_id, ServiceDeskAttempt.passed.is_(True))
        .scalar()
        or 0
    )

    data = {
        "student": {
            "id": student.id,
            "name": student.name,
            "total_xp": student.total_xp,
            "level": level,
            "level_name": level_name,
            "quiz_best_scores": [{"quiz_id": q.quiz_id, "best_score": q.best_score, "first_attempt_xp": q.first_attempt_xp} for q in quiz_attempts],
            "service_desk_completed": int(service_desk_completed),
        },
        "recent_activity": [
            {
                "type": entry.source_type,
                "delta": entry.delta,
                "description": entry.description,
                "timestamp": entry.created_at,
            }
            for entry in recent_entries
        ],
    }

    return ok(data)


@router.get("/api/students/{student_id}/stats")
def get_student_stats(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # This is a read endpoint and is also used by mentor review. Presence and
    # streak mutations belong to the owner-only check-in endpoint above.
    streak = db.query(LoginStreak).filter(LoginStreak.student_id == student_id).first()
    level, level_name = level_from_xp(student.total_xp)

    required_quizzes = [quiz for week in range(25) for quiz in required_quizzes_for_week(db, week)]
    completed_required = [quiz for quiz in required_quizzes if is_quiz_passed(db, student_id, quiz)]
    required_scores = [
        max((attempt.score or 0) for attempt in quiz.attempts if attempt.student_id == student_id)
        for quiz in completed_required
    ]
    quiz_stats = type("QuizStats", (), {
        "completed": len(completed_required),
        "avg_score": (sum(required_scores) / len(required_scores)) if required_scores else 0,
    })()
    total_quizzes = len(required_quizzes)

    service_desk_stats = (
        db.query(
            func.count(ServiceDeskAttempt.id).label("completed"),
            func.coalesce(func.avg(ServiceDeskAttempt.score), 0).label("avg_score"),
        )
        .filter(ServiceDeskAttempt.student_id == student_id, ServiceDeskAttempt.passed.is_(True))
        .first()
    )
    total_service_desk = db.query(func.count(ServiceDeskScenario.id)).filter(ServiceDeskScenario.status == "active").scalar() or 0

    week_number = derive_current_week(student_id, db)
    week_required_quizzes = required_quizzes_for_week(db, week_number)
    week_quizzes = len(week_required_quizzes)
    week_service_desk = 0
    week_completed_q = sum(is_quiz_passed(db, student_id, quiz) for quiz in week_required_quizzes)
    week_total = week_quizzes + week_service_desk
    week_done = week_completed_q
    week_completion = round((week_done / week_total) * 100, 1) if week_total else 0

    quiz_activity = (
        db.query(
            QuizAttempt.completed_at.label("timestamp"),
            Quiz.title.label("title"),
            QuizAttempt.score.label("score"),
            QuizAttempt.xp_awarded.label("xp"),
        )
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .filter(QuizAttempt.student_id == student_id)
        .all()
    )
    service_desk_activity = (
        db.query(
            ServiceDeskAttempt.completed_at.label("timestamp"),
            ServiceDeskScenario.title.label("title"),
            ServiceDeskAttempt.score.label("score"),
        )
        .join(ServiceDeskScenarioVersion, ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id)
        .join(ServiceDeskScenario, ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id)
        .filter(ServiceDeskAttempt.student_id == student_id, ServiceDeskAttempt.passed.is_(True))
        .all()
    )

    recent_activity = [
        {"type": "quiz", "title": row.title, "score": row.score, "xp": row.xp, "timestamp": row.timestamp}
        for row in quiz_activity
    ] + [
        {"type": "service_desk", "title": row.title, "score": row.score, "xp": None, "timestamp": row.timestamp}
        for row in service_desk_activity
    ]
    recent_activity.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
    recent_activity = recent_activity[:5]

    weak_rows = []

    cohort = (
        db.query(Student.id, Student.total_xp)
        .filter(Student.id != student_id)
        .all()
    )
    cohort_xp_values = [row.total_xp for row in cohort]
    avg_xp = round(sum(cohort_xp_values) / len(cohort_xp_values), 0) if cohort_xp_values else 0
    percentile = round(((student.total_xp - avg_xp) / avg_xp) * 100, 1) if avg_xp else 0

    cohort_quiz_avg = (
        db.query(func.coalesce(func.avg(QuizAttempt.score), 0))
        .join(Student, Student.id == QuizAttempt.student_id)
        .filter(Student.id != student_id)
        .scalar()
        or 0
    )

    cert = _build_cert_readiness(student_id, db)

    return {
        "success": True,
        "name": student.name,
        "total_xp": student.total_xp,
        "level": level,
        "level_name": level_name,
        "quizzes_completed": int(quiz_stats.completed or 0),
        "total_quizzes": int(total_quizzes),
        "avg_quiz_score": round(float(quiz_stats.avg_score or 0), 1),
        "service_desk_completed": int(service_desk_stats.completed or 0),
        "total_service_desk": int(total_service_desk),
        "avg_service_desk_score": round(float(service_desk_stats.avg_score or 0), 1),
        "current_week": week_number,
        "week_completion": week_completion,
        "recent_activity": recent_activity,
        "weak_areas": [
            {"topic": row.category or "general", "avg_score": round(float(row.avg_score or 0), 1), "attempts": int(row.attempts or 0)}
            for row in weak_rows
        ],
        "streak": streak.current_streak if streak else 0,
        "longest_streak": streak.longest_streak if streak else 0,
        "cohort_comparison": {
            "your_xp": student.total_xp,
            "avg_xp": avg_xp,
            "percentile": percentile,
            "your_quiz_avg": round(float(quiz_stats.avg_score or 0), 1),
            "cohort_quiz_avg": round(float(cohort_quiz_avg), 1),
        },
        "cert_readiness": cert,
        "onboarding": get_orientation_state(db, student),
    }


@router.get("/api/students/{student_id}/certification-readiness")
def get_cert_readiness(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"success": True, "data": _build_cert_readiness(student_id, db)}


@router.get("/api/leaderboard")
def get_leaderboard(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    students = db.query(Student).order_by(Student.total_xp.desc(), Student.id.asc()).all()
    entries = []
    for rank, student in enumerate(students, start=1):
        level, _ = level_from_xp(student.total_xp)
        entries.append(
            {
                "rank": rank,
                "student_id": student.id,
                "name": student.name,
                "total_xp": student.total_xp,
                "level": level,
            }
        )
    return ok(entries, total=len(entries), page=1, per_page=len(entries) or 1)


@router.get("/api/students")
def get_students(db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    # Student-facing roster (e.g. the ticket collaborator picker) — no email or
    # other private profile data. Admins use /api/admin/students/overview for that.
    rows = db.query(Student).order_by(Student.name.asc()).all()
    data = [{"id": row.id, "name": row.name} for row in rows]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/api/students/{student_id}/mastery")
def get_student_mastery(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return ok(list_student_mastery(db, student_id))


@router.get("/api/squad/dashboard")
def squad_dashboard(student_id: int | None = None, limit: int = 30, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    if student_id is not None:
        ensure_student_access(current_student, student_id)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    members = (
        db.query(Student)
        .filter(Student.is_mentor.is_(False))
        .order_by(Student.total_xp.desc(), Student.name.asc())
        .all()
    )
    member_rows = []
    for member in members:
        last_active = member.last_active_at
        if last_active and last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        active = bool(last_active and last_active >= cutoff)
        member_rows.append(
            {
                "student_id": member.id,
                "name": member.name,
                "total_xp": member.total_xp,
                "last_active_at": member.last_active_at,
                "status": "Active" if active else "Idle",
            }
        )

    activities = (
        db.query(SquadActivity)
        .join(Student, Student.id == SquadActivity.student_id)
        .filter(Student.is_mentor.is_(False))
        .order_by(SquadActivity.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    feed = []
    for row in activities:
        student = db.query(Student).filter(Student.id == row.student_id).first()
        feed.append(
            {
                "id": row.id,
                "student_id": row.student_id,
                "student_name": student.name if student else f"Student {row.student_id}",
                "activity_type": row.activity_type,
                "title": row.title,
                "detail": row.detail,
                "created_at": row.created_at,
            }
        )

    response = {
        "members": member_rows,
        "activity_feed": feed,
        "weekly_domain_leads": get_weekly_domain_leads(db),
    }

    if student_id is not None:
        response["selected_student_mastery"] = list_student_mastery(db, student_id)

    return ok(response)


@router.get("/api/students/{student_id}/learning-path")
def get_learning_path(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    modules = db.query(Module).order_by(Module.module_order.asc().nullslast(), Module.id.asc()).all()
    result = []
    for module in modules:
        mastery = get_module_mastery(student_id, module.id, db)
        unlock_check = check_module_unlock(student_id, module.id, db)
        lessons = db.query(Lesson).filter(Lesson.module_id == module.id).order_by(Lesson.lesson_order.asc()).all()

        lesson_items = []
        for lesson in lessons:
            quiz_count = db.query(func.count(Quiz.id)).filter(Quiz.lesson_id == lesson.id).scalar() or 0
            ticket_count = db.query(func.count(Ticket.id)).filter(Ticket.lesson_id == lesson.id).scalar() or 0
            completed_quiz = (
                db.query(func.count(QuizAttempt.id))
                .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
                .filter(QuizAttempt.student_id == student_id, Quiz.lesson_id == lesson.id)
                .scalar()
                or 0
            )
            completed_ticket = (
                db.query(func.count(TicketSubmission.id))
                .join(Ticket, TicketSubmission.ticket_id == Ticket.id)
                .filter(TicketSubmission.student_id == student_id, Ticket.lesson_id == lesson.id, TicketSubmission.status == "passed")
                .scalar()
                or 0
            )
            total_parts = int(quiz_count + ticket_count)
            done_parts = int(completed_quiz + completed_ticket)
            lesson_note_exists = bool(
                db.query(StudentLessonNote.id)
                .filter(StudentLessonNote.student_id == student_id, StudentLessonNote.lesson_id == lesson.id)
                .first()
            )
            completion_percent = round((done_parts / total_parts) * 100, 1) if total_parts else (100 if lesson_note_exists else 0)

            lesson_items.append(
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "video_url": lesson.video_url,
                    "summary": lesson.summary,
                    "lesson_order": lesson.lesson_order,
                    "completion_percent": completion_percent,
                    "is_orientation": module.code == "MOD-000" and lesson.title == "Welcome to Nexus: Your First Week",
                }
            )

        result.append(
            {
                "id": module.id,
                "code": module.code,
                "title": module.title,
                "description": module.description,
                "mastery_percent": mastery,
                "unlocked": unlock_check["unlocked"],
                "unlock_requirements": unlock_check.get("requirements_missing", []),
                "lessons": lesson_items,
            }
        )

    return {"success": True, "modules": result}


@router.get("/api/students/{student_id}/promotion-status")
def promotion_status(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    status = get_promotion_status(student_id, db)
    return {"success": True, **status}


@router.get("/api/students/{student_id}/methodology-status")
def methodology_status(student_id: int, db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)):
    ensure_student_access(current_student, student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    access = can_access_tickets(student_id, db)
    frameworks = db.query(MethodologyFramework).order_by(MethodologyFramework.id.asc()).all()
    progress = (
        db.query(StudentMethodologyProgress)
        .filter(StudentMethodologyProgress.student_id == student_id)
        .all()
    )
    by_framework = {p.framework_id: p for p in progress}
    data = []
    for fw in frameworks:
        p = by_framework.get(fw.id)
        data.append(
            {
                "framework_id": fw.id,
                "name": fw.name,
                "completed": bool(p.completed) if p else False,
                "practice_passed": bool(p.practice_passed) if p else False,
                "quiz_score": p.quiz_score if p else None,
            }
        )
    return {"success": True, "allowed": access["allowed"], "missing_frameworks": access["missing_frameworks"], "frameworks": data}


# ---------------------------------------------------------------- TB-03: week plan

@router.get("/api/students/me/week-plan")
def get_week_plan(
    week: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """The student's ordered plan for a week: lessons, quizzes, CLI labs, labs,
    Service Desk scenarios — each with done/available status. Scope: own data only (TB-03)."""
    from app.models.cli_lab import CliLab, CliLabAttempt
    from app.models.lab import LabRun, LabTemplate
    from app.models.learning import Lesson, Module
    from app.models.lesson_notes import StudentLessonNote
    from app.models.quiz import Quiz
    from app.models.training import TrainingWeek, TrainingWeekActivity
    from app.services.progression_service import get_promotion_status

    student_id = current_student.id
    current_week = week or derive_current_week(student_id, db)

    # Lessons for this week's modules
    week_module_codes = [c for c, w in MODULE_WEEKS.items() if w == current_week]
    lessons_out = []
    if week_module_codes:
        modules = (
            db.query(Module)
            .filter(Module.code.in_(week_module_codes))
            .order_by(Module.module_order)
            .all()
        )
        done_lessons = {
            row.lesson_id
            for row in db.query(StudentLessonNote.lesson_id).filter(
                StudentLessonNote.student_id == student_id
            )
        }
        for module in modules:
            for lesson in (
                db.query(Lesson)
                .filter(Lesson.module_id == module.id, Lesson.status == "published")
                .order_by(Lesson.lesson_order)
                .all()
            ):
                lessons_out.append(
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "module": module.code,
                        "status": "done" if lesson.id in done_lessons else "available",
                        "route": f"/lessons/{lesson.id}",
                    }
                )

    visible_quizzes = (
        db.query(Quiz)
        .filter(
            Quiz.week_number == current_week,
            *student_visible_quiz_filters(),
        )
        .order_by(Quiz.id)
        .all()
    )
    remediation_ids = assigned_remediation_ids(db, student_id) | triggered_remediation_ids(db, student_id)

    def quiz_item(quiz):
        passed = is_quiz_passed(db, student_id, quiz)
        attempted = any(attempt.student_id == student_id for attempt in quiz.attempts)
        return {
            "id": quiz.id,
            "title": quiz.title,
            "status": "done" if passed else ("in_progress" if attempted else "available"),
            "route": f"/quizzes/{quiz.id}",
            "quiz_purpose": quiz.quiz_purpose,
            "is_required": quiz.is_required,
            "label": {
                QUIZ_PURPOSE_REMEDIATION: "Remediation",
                QUIZ_PURPOSE_CERTIFICATION: "Certification Practice",
                QUIZ_PURPOSE_CUMULATIVE: "Cumulative Review",
                QUIZ_PURPOSE_GATE: "Promotion Gate",
            }.get(quiz.quiz_purpose, "Required" if quiz.is_required else "Optional"),
        }

    quizzes_out = [
        quiz_item(q) for q in visible_quizzes
        if q.is_required and q.show_in_weekly_checklist and q.quiz_purpose not in {QUIZ_PURPOSE_CUMULATIVE, QUIZ_PURPOSE_GATE}
    ]
    practice_out = [quiz_item(q) for q in visible_quizzes if q.quiz_purpose == QUIZ_PURPOSE_PRACTICE and q.show_in_practice_library]
    remediation_out = [quiz_item(q) for q in visible_quizzes if q.quiz_purpose == QUIZ_PURPOSE_REMEDIATION and q.id in remediation_ids]
    cumulative_gate_out = [quiz_item(q) for q in visible_quizzes if q.quiz_purpose in {QUIZ_PURPOSE_CUMULATIVE, QUIZ_PURPOSE_GATE}]

    # CLI labs by pack mapping
    week_packs = [p for p, w in CLI_PACK_WEEKS.items() if w == current_week]
    cli_out = []
    if week_packs:
        completed_cli = {
            row.lab_id
            for row in db.query(CliLabAttempt.lab_id).filter(
                CliLabAttempt.student_id == student_id,
                CliLabAttempt.completed_at.isnot(None),
            )
        }
        for lab in (
            db.query(CliLab)
            .filter(CliLab.compartment_id.in_(week_packs))
            .order_by(CliLab.order_index)
            .all()
        ):
            cli_out.append(
                {
                    "id": lab.id,
                    "title": lab.title,
                    "status": "done" if lab.id in completed_cli else "available",
                    "route": f"/cli-labs/{lab.id}",
                }
            )

    # VM/local labs by week_number; done = verified or submitted run
    lab_runs = {
        run.lab_template_id: run.status
        for run in db.query(LabRun).filter(LabRun.student_id == student_id).all()
    }
    labs_out = [
        {
            "id": lt.id,
            "title": lt.title,
            "status": "done" if lab_runs.get(lt.id) in ("submitted", "verified") else "available",
            "route": f"/labs/{lt.id}",
        }
        for lt in db.query(LabTemplate)
        .filter(LabTemplate.week_number == current_week, LabTemplate.is_published.is_(True))
        .order_by(LabTemplate.id)
        .all()
    ]

    scenario_keys = [
        row.content_ref
        for row in db.query(TrainingWeekActivity)
        .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
        .filter(
            TrainingWeek.week_number == current_week,
            TrainingWeekActivity.activity_type == "service_desk_scenario",
        )
        .all()
    ]
    passed_scenarios = {
        stable_key
        for stable_key, in db.query(ServiceDeskScenario.stable_key)
        .join(ServiceDeskScenarioVersion, ServiceDeskScenarioVersion.scenario_id == ServiceDeskScenario.id)
        .join(ServiceDeskAttempt, ServiceDeskAttempt.scenario_version_id == ServiceDeskScenarioVersion.id)
        .filter(ServiceDeskAttempt.student_id == student_id, ServiceDeskAttempt.passed.is_(True))
        .all()
    }
    service_desk_out = [
        {
            "id": scenario.stable_key,
            "title": scenario.title,
            "difficulty": scenario.difficulty,
            "status": "done" if scenario.stable_key in passed_scenarios else "available",
            "route": "/service-desk",
        }
        for scenario in db.query(ServiceDeskScenario)
        .filter(ServiceDeskScenario.stable_key.in_(scenario_keys), ServiceDeskScenario.status == "active")
        .order_by(ServiceDeskScenario.difficulty, ServiceDeskScenario.id)
        .all()
    ]

    all_items = lessons_out + quizzes_out + cumulative_gate_out + cli_out + labs_out + service_desk_out
    done_count = sum(1 for item in all_items if item["status"] == "done")

    # Recommended next action: first non-done item in pedagogical order
    next_action = next((i for i in all_items if i["status"] != "done"), None)

    promotion = get_promotion_status(student_id, db)

    return ok(
        {
            "week": current_week,
            "role": (promotion.get("current_role") or {}).get("name"),
            "gate": promotion.get("eligibility"),
            "progress_percent": round(done_count / len(all_items) * 100, 1) if all_items else 0,
            "next_action": next_action,
            "lessons": lessons_out,
            "quizzes": quizzes_out,
            "practice_quizzes": practice_out,
            "remediation_quizzes": remediation_out,
            "cumulative_gate_quizzes": cumulative_gate_out,
            "cli_labs": cli_out,
            "labs": labs_out,
            "service_desk": service_desk_out,
            "onboarding": get_orientation_state(db, current_student),
        }
    )
