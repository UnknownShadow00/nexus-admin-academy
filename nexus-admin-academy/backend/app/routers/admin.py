import logging
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.resource import Resource
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.xp_ledger import XPLedger
from app.schemas.quiz import BulkTicketGenerateRequest, QuizGenerateRequest
from app.schemas.resource import ResourceCreateRequest
from app.schemas.ticket import ManualReviewRequest, OverrideRequest, TicketCreateRequest
from app.services.ai_service import AIServiceError, generate_quiz_questions
from app.services.admin_auth import verify_admin
from app.services.xp_service import award_xp

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)


def _ok(data, *, total: int | None = None, page: int | None = None, per_page: int | None = None):
    payload = {"success": True, "data": data}
    if total is not None:
        payload["total"] = total
    if page is not None:
        payload["page"] = page
    if per_page is not None:
        payload["per_page"] = per_page
    return payload


def _collab_multiplier(count_people: int) -> float:
    if count_people <= 1:
        return 1.0
    if count_people == 2:
        return 0.8
    return 0.6


@router.post("/quiz/generate")
def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db)):
    try:
        generated = generate_quiz_questions(str(payload.source_url), payload.title)
    except AIServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    quiz = Quiz(title=payload.title, source_url=str(payload.source_url), week_number=payload.week_number)
    db.add(quiz)
    db.flush()

    for item in generated:
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=item["question_text"],
                option_a=item["option_a"],
                option_b=item["option_b"],
                option_c=item["option_c"],
                option_d=item["option_d"],
                correct_answer=item["correct_answer"],
                explanation=item.get("explanation"),
            )
        )

    db.commit()
    logger.info("admin_quiz_generated quiz_id=%s week=%s title=%s", quiz.id, payload.week_number, payload.title)
    return _ok({"quiz_id": quiz.id, "questions": generated, "message": f"Quiz created: {payload.title} - 10 unique questions ready"})


@router.post("/tickets")
def create_ticket(payload: TicketCreateRequest, db: Session = Depends(get_db)):
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        difficulty=payload.difficulty,
        week_number=payload.week_number,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info("admin_ticket_created ticket_id=%s week=%s difficulty=%s", ticket.id, payload.week_number, payload.difficulty)
    return _ok({"ticket_id": ticket.id, "title": ticket.title})


@router.post("/resources")
def create_resource(payload: ResourceCreateRequest, db: Session = Depends(get_db)):
    resource = Resource(
        title=payload.title,
        url=str(payload.url),
        resource_type=payload.resource_type,
        week_number=payload.week_number,
        category=payload.category,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    logger.info("resource_created resource_id=%s week=%s type=%s", resource.id, resource.week_number, resource.resource_type)
    return _ok({"resource_id": resource.id})


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(resource)
    db.commit()
    logger.info("resource_deleted resource_id=%s", resource_id)
    return _ok({"deleted": True})


@router.get("/submissions")
def list_submissions(
    student_id: int | None = None,
    ticket_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(TicketSubmission).options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
    if student_id is not None:
        query = query.filter(TicketSubmission.student_id == student_id)
    if ticket_id is not None:
        query = query.filter(TicketSubmission.ticket_id == ticket_id)

    submissions = query.order_by(TicketSubmission.submitted_at.desc()).all()
    data = [
        {
            "id": s.id,
            "student_name": s.student.name,
            "ticket_title": s.ticket.title,
            "ai_score": s.ai_score,
            "submitted_at": s.submitted_at,
            "admin_reviewed": s.admin_reviewed,
            "collaborator_ids": s.collaborator_ids,
        }
        for s in submissions
    ]
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/submissions/{submission_id}")
def submission_details(submission_id: int, db: Session = Depends(get_db)):
    submission = (
        db.query(TicketSubmission)
        .options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
        .filter(TicketSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    data = {
        "id": submission.id,
        "student_name": submission.student.name,
        "ticket_title": submission.ticket.title,
        "writeup": submission.writeup,
        "ai_score": submission.ai_score,
        "ai_feedback": submission.ai_feedback,
        "xp_awarded": submission.xp_awarded,
        "screenshots": submission.screenshots,
        "collaborator_ids": submission.collaborator_ids,
        "admin_reviewed": submission.admin_reviewed,
        "admin_comment": submission.admin_comment,
    }
    return _ok(data)


@router.put("/submissions/{submission_id}/override")
def override_grade(submission_id: int, payload: OverrideRequest, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).filter(TicketSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.ai_score is None:
        raise HTTPException(status_code=400, detail="Cannot override an ungraded submission")

    participants = [submission.student_id] + [int(x) for x in (submission.collaborator_ids or [])]
    participant_count = len(participants)
    multiplier = _collab_multiplier(participant_count)

    old_score = submission.ai_score
    old_xp_each = submission.xp_awarded
    new_xp_each = int(payload.new_score * 10 * multiplier)
    delta = new_xp_each - old_xp_each

    submission.ai_score = payload.new_score
    submission.override_score = payload.new_score
    submission.overridden = True
    submission.admin_reviewed = True
    submission.admin_comment = payload.comment
    submission.xp_awarded = new_xp_each

    for target_student_id in participants:
        award_xp(
            db,
            student_id=target_student_id,
            delta=delta,
            source_type="admin_override",
            source_id=submission.id,
            description=f"Manual review adjustment for ticket {submission.ticket_id}",
        )

    db.commit()
    logger.info(
        "grade_override submission_id=%s old_score=%s new_score=%s xp_delta_each=%s participants=%s",
        submission.id,
        old_score,
        payload.new_score,
        delta,
        participant_count,
    )

    return _ok(
        {
            "submission_id": submission.id,
            "old_score": old_score,
            "new_score": payload.new_score,
            "xp_difference_per_student": delta,
            "participants_updated": participant_count,
        }
    )


@router.get("/review")
def review_queue(db: Session = Depends(get_db)):
    rows = (
        db.query(TicketSubmission)
        .options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
        .filter(TicketSubmission.graded_at.isnot(None))
        .order_by(TicketSubmission.submitted_at.desc())
        .all()
    )

    data = [
        {
            "submission_id": row.id,
            "student_name": row.student.name,
            "ticket_title": row.ticket.title,
            "ai_score": row.ai_score,
            "admin_reviewed": row.admin_reviewed,
            "submitted_at": row.submitted_at,
        }
        for row in rows
    ]
    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.put("/review/{submission_id}")
def manual_review(submission_id: int, payload: ManualReviewRequest, db: Session = Depends(get_db)):
    return override_grade(submission_id, OverrideRequest(new_score=payload.new_score, comment=payload.comment), db)


@router.get("/students/overview")
def student_overview(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.total_xp.desc(), Student.id.asc()).all()
    total_quizzes = db.query(Quiz).count()
    total_tickets = db.query(Ticket).count()

    data = []
    for rank, student in enumerate(students, start=1):
        quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student.id).all()
        ticket_subs = db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id, TicketSubmission.ai_score.isnot(None)).all()

        last_activity = None
        timestamps = [q.completed_at for q in quiz_attempts] + [t.submitted_at for t in ticket_subs]
        if timestamps:
            last_activity = max(ts for ts in timestamps if ts is not None)

        data.append(
            {
                "rank": rank,
                "student_id": student.id,
                "name": student.name,
                "xp": student.total_xp,
                "quiz_done": len(quiz_attempts),
                "quiz_total": total_quizzes,
                "avg_quiz": round(mean([q.score for q in quiz_attempts]), 2) if quiz_attempts else 0,
                "ticket_done": len(ticket_subs),
                "ticket_total": total_tickets,
                "avg_ticket": round(mean([t.ai_score for t in ticket_subs if t.ai_score is not None]), 2) if ticket_subs else 0,
                "last_active": last_activity,
            }
        )

    return _ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/students/{student_id}/activity")
def student_activity(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    entries = (
        db.query(XPLedger)
        .filter(XPLedger.student_id == student_id)
        .order_by(XPLedger.created_at.desc())
        .limit(50)
        .all()
    )

    data = {
        "student": {"id": student.id, "name": student.name, "total_xp": student.total_xp},
        "activity": [
            {
                "id": e.id,
                "source_type": e.source_type,
                "source_id": e.source_id,
                "delta": e.delta,
                "description": e.description,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    }
    return _ok(data)


@router.post("/tickets/bulk-generate")
def bulk_generate_tickets(payload: BulkTicketGenerateRequest):
    generated = []
    for raw in payload.titles:
        title = raw.strip()
        if not title:
            continue
        generated.append(
            {
                "title": title,
                "description": f"Scenario: {title}. Diagnose the issue, document troubleshooting steps, include verification evidence, and summarize root cause.",
                "difficulty": payload.difficulty,
                "week_number": payload.week_number,
            }
        )
    return _ok(generated)


@router.post("/tickets/bulk-publish")
def bulk_publish_tickets(payload: list[TicketCreateRequest], db: Session = Depends(get_db)):
    created = []
    for item in payload:
        ticket = Ticket(
            title=item.title,
            description=item.description,
            difficulty=item.difficulty,
            week_number=item.week_number,
        )
        db.add(ticket)
        db.flush()
        created.append({"ticket_id": ticket.id, "title": ticket.title})

    db.commit()
    logger.info("bulk_tickets_published count=%s", len(created))
    return _ok(created, total=len(created), page=1, per_page=len(created) or 1)
