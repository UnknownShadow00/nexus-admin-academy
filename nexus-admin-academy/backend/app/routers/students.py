from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.comptia import ComptiaObjective, StudentObjectiveProgress
from app.models.learning import Lesson, Module
from app.models.login_streak import LoginStreak
from app.models.progression import MethodologyFramework, StudentMethodologyProgress
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.models.squad_activity import SquadActivity
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.services.activity_service import mark_student_active
from app.services.mastery_service import list_student_mastery
from app.services.methodology_enforcer import can_access_tickets
from app.services.progression_service import check_module_unlock, get_module_mastery, get_promotion_status
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
        db.commit()
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


@router.post("/api/students/{student_id}/check-in")
def student_check_in(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    mark_student_active(db, student_id)
    streak = update_login_streak(db, student_id)
    return {"success": True, "streak": streak.current_streak, "longest_streak": streak.longest_streak}


@router.get("/api/students/{student_id}/dashboard")
def get_student_dashboard(student_id: int, db: Session = Depends(get_db)):
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
    ticket_subs = db.query(TicketSubmission).filter(TicketSubmission.student_id == student_id).all()

    data = {
        "student": {
            "id": student.id,
            "name": student.name,
            "total_xp": student.total_xp,
            "level": level,
            "level_name": level_name,
            "quiz_best_scores": [{"quiz_id": q.quiz_id, "best_score": q.best_score, "first_attempt_xp": q.first_attempt_xp} for q in quiz_attempts],
            "tickets_completed": sum(1 for t in ticket_subs if t.status == "passed"),
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
def get_student_stats(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    streak = update_login_streak(db, student_id)
    level, level_name = level_from_xp(student.total_xp)

    quiz_stats = (
        db.query(func.count(QuizAttempt.id).label("completed"), func.coalesce(func.avg(QuizAttempt.score), 0).label("avg_score"))
        .filter(QuizAttempt.student_id == student_id)
        .first()
    )
    total_quizzes = db.query(func.count(Quiz.id)).scalar() or 0

    ticket_stats = (
        db.query(func.count(TicketSubmission.id).label("completed"), func.coalesce(func.avg(TicketSubmission.ai_score), 0).label("avg_score"))
        .filter(TicketSubmission.student_id == student_id, TicketSubmission.status == "passed")
        .first()
    )
    total_tickets = db.query(func.count(Ticket.id)).scalar() or 0

    week_number = 1
    week_quizzes = db.query(func.count(Quiz.id)).filter(Quiz.week_number == week_number).scalar() or 0
    week_tickets = db.query(func.count(Ticket.id)).filter(Ticket.week_number == week_number).scalar() or 0
    week_completed_q = db.query(func.count(QuizAttempt.id)).join(Quiz, QuizAttempt.quiz_id == Quiz.id).filter(QuizAttempt.student_id == student_id, Quiz.week_number == week_number).scalar() or 0
    week_completed_t = (
        db.query(func.count(TicketSubmission.id))
        .join(Ticket, TicketSubmission.ticket_id == Ticket.id)
        .filter(TicketSubmission.student_id == student_id, Ticket.week_number == week_number, TicketSubmission.status == "passed")
        .scalar()
        or 0
    )
    week_total = week_quizzes + week_tickets
    week_done = week_completed_q + week_completed_t
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
    ticket_activity = (
        db.query(
            TicketSubmission.submitted_at.label("timestamp"),
            Ticket.title.label("title"),
            TicketSubmission.ai_score.label("score"),
            TicketSubmission.xp_awarded.label("xp"),
        )
        .join(Ticket, Ticket.id == TicketSubmission.ticket_id)
        .filter(TicketSubmission.student_id == student_id, TicketSubmission.status == "passed")
        .all()
    )

    recent_activity = [
        {"type": "quiz", "title": row.title, "score": row.score, "xp": row.xp, "timestamp": row.timestamp}
        for row in quiz_activity
    ] + [
        {"type": "ticket", "title": row.title, "score": row.score, "xp": row.xp, "timestamp": row.timestamp}
        for row in ticket_activity
    ]
    recent_activity.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
    recent_activity = recent_activity[:5]

    weak_rows = (
        db.query(
            Ticket.category.label("category"),
            func.count(TicketSubmission.id).label("attempts"),
            func.coalesce(func.avg(TicketSubmission.ai_score), 0).label("avg_score"),
        )
        .join(Ticket, Ticket.id == TicketSubmission.ticket_id)
        .filter(TicketSubmission.student_id == student_id, TicketSubmission.status == "passed")
        .group_by(Ticket.category)
        .having(func.avg(TicketSubmission.ai_score) < 6)
        .order_by(func.avg(TicketSubmission.ai_score).asc())
        .all()
    )

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

    cert = get_cert_readiness(student_id, db)

    return {
        "success": True,
        "name": student.name,
        "total_xp": student.total_xp,
        "level": level,
        "level_name": level_name,
        "quizzes_completed": int(quiz_stats.completed or 0),
        "total_quizzes": int(total_quizzes),
        "avg_quiz_score": round(float(quiz_stats.avg_score or 0), 1),
        "tickets_completed": int(ticket_stats.completed or 0),
        "total_tickets": int(total_tickets),
        "avg_ticket_score": round(float(ticket_stats.avg_score or 0), 1),
        "current_week": week_number,
        "week_completion": week_completion,
        "recent_activity": recent_activity,
        "weak_areas": [
            {"topic": row.category or "general", "avg_score": round(float(row.avg_score or 0), 1), "attempts": int(row.attempts or 0)}
            for row in weak_rows
        ],
        "streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "cohort_comparison": {
            "your_xp": student.total_xp,
            "avg_xp": avg_xp,
            "percentile": percentile,
            "your_quiz_avg": round(float(quiz_stats.avg_score or 0), 1),
            "cohort_quiz_avg": round(float(cohort_quiz_avg), 1),
        },
        "cert_readiness": cert["data"],
    }


@router.get("/api/students/{student_id}/certification-readiness")
def get_cert_readiness(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

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

    data = {
        "overall_readiness": round(float(overall), 1),
        "by_domain": [{"domain": row.domain, "readiness": round(float(row.avg_mastery), 1)} for row in mastery_rows],
        "total_objectives": int(total_objectives),
    }
    return {"success": True, "data": data}


@router.get("/api/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
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
def get_students(db: Session = Depends(get_db)):
    rows = db.query(Student).order_by(Student.name.asc()).all()
    data = [{"id": row.id, "name": row.name, "email": row.email, "last_active_at": row.last_active_at} for row in rows]
    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/api/students/{student_id}/mastery")
def get_student_mastery(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return ok(list_student_mastery(db, student_id))


@router.get("/api/squad/dashboard")
def squad_dashboard(student_id: int | None = None, limit: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=48)

    members = db.query(Student).order_by(Student.total_xp.desc(), Student.name.asc()).all()
    member_rows = []
    for member in members:
        active = member.last_active_at and member.last_active_at >= cutoff
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
def get_learning_path(student_id: int, db: Session = Depends(get_db)):
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
            completion_percent = round((done_parts / total_parts) * 100, 1) if total_parts else 0

            lesson_items.append(
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "video_url": lesson.video_url,
                    "summary": lesson.summary,
                    "lesson_order": lesson.lesson_order,
                    "completion_percent": completion_percent,
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
def promotion_status(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    status = get_promotion_status(student_id, db)
    return {"success": True, **status}


@router.get("/api/students/{student_id}/methodology-status")
def methodology_status(student_id: int, db: Session = Depends(get_db)):
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
