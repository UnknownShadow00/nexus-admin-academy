from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.schemas.student import DashboardResponse, LeaderboardEntry, LeaderboardResponse, RecentActivity, StudentInfo
from app.services.xp_calculator import level_from_xp

router = APIRouter(tags=["students"])


@router.get("/api/students/{student_id}/dashboard", response_model=DashboardResponse)
def get_student_dashboard(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    level, level_name = level_from_xp(student.total_xp)

    quiz_activities = (
        db.query(QuizAttempt, Quiz)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(QuizAttempt.student_id == student_id)
        .all()
    )
    ticket_activities = (
        db.query(TicketSubmission, Ticket)
        .join(Ticket, TicketSubmission.ticket_id == Ticket.id)
        .filter(TicketSubmission.student_id == student_id)
        .all()
    )

    activity: list[RecentActivity] = []
    for attempt, quiz in quiz_activities:
        activity.append(
            RecentActivity(
                type="quiz",
                title=quiz.title,
                score=attempt.score,
                xp=attempt.xp_awarded,
                timestamp=attempt.completed_at,
            )
        )
    for sub, ticket in ticket_activities:
        activity.append(
            RecentActivity(
                type="ticket",
                title=ticket.title,
                score=sub.ai_score,
                xp=sub.xp_awarded,
                timestamp=sub.submitted_at,
            )
        )

    activity = sorted(activity, key=lambda x: x.timestamp, reverse=True)[:5]

    return DashboardResponse(
        student=StudentInfo(
            id=student.id,
            name=student.name,
            total_xp=student.total_xp,
            level=level,
            level_name=level_name,
        ),
        recent_activity=activity,
    )


@router.get("/api/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.total_xp.desc(), Student.id.asc()).all()
    entries = []
    for rank, student in enumerate(students, start=1):
        level, _ = level_from_xp(student.total_xp)
        entries.append(
            LeaderboardEntry(
                rank=rank,
                student_id=student.id,
                name=student.name,
                total_xp=student.total_xp,
                level=level,
            )
        )
    return LeaderboardResponse(leaderboard=entries)
