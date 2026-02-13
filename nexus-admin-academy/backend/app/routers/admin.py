import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import Question, Quiz
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.schemas.quiz import QuizGenerateRequest, QuizGenerateResponse, QuizQuestionOut
from app.schemas.ticket import (
    OverrideRequest,
    OverrideResponse,
    SubmissionDetailResponse,
    SubmissionListItem,
    SubmissionListResponse,
    TicketCreateRequest,
    TicketCreateResponse,
)
from app.services.ai_service import generate_quiz_questions

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.post("/quiz/generate", response_model=QuizGenerateResponse)
def generate_quiz(payload: QuizGenerateRequest, db: Session = Depends(get_db)):
    generated = generate_quiz_questions(str(payload.source_url), payload.title)

    quiz = Quiz(title=payload.title, source_url=str(payload.source_url), week_number=payload.week_number)
    db.add(quiz)
    db.flush()

    questions = []
    for item in generated[:10]:
        question = Question(
            quiz_id=quiz.id,
            question_text=item["question_text"],
            option_a=item["option_a"],
            option_b=item["option_b"],
            option_c=item["option_c"],
            option_d=item["option_d"],
            correct_answer=item["correct_answer"],
            explanation=item.get("explanation"),
        )
        db.add(question)
        questions.append(question)

    db.commit()
    db.refresh(quiz)

    return QuizGenerateResponse(
        quiz_id=quiz.id,
        questions=[
            QuizQuestionOut(
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
            )
            for q in questions
        ],
    )


@router.post("/tickets", response_model=TicketCreateResponse)
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
    return TicketCreateResponse(ticket_id=ticket.id, title=ticket.title)


@router.get("/submissions", response_model=SubmissionListResponse)
def list_submissions(
    student_id: int | None = None,
    ticket_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(TicketSubmission)
        .options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
    )
    if student_id is not None:
        query = query.filter(TicketSubmission.student_id == student_id)
    if ticket_id is not None:
        query = query.filter(TicketSubmission.ticket_id == ticket_id)

    submissions = query.order_by(TicketSubmission.submitted_at.desc()).all()
    return SubmissionListResponse(
        submissions=[
            SubmissionListItem(
                id=s.id,
                student_name=s.student.name,
                ticket_title=s.ticket.title,
                ai_score=s.override_score if s.overridden and s.override_score is not None else s.ai_score,
                submitted_at=s.submitted_at,
            )
            for s in submissions
        ]
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionDetailResponse)
def submission_details(submission_id: int, db: Session = Depends(get_db)):
    submission = (
        db.query(TicketSubmission)
        .options(selectinload(TicketSubmission.student), selectinload(TicketSubmission.ticket))
        .filter(TicketSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    score = submission.override_score if submission.overridden and submission.override_score is not None else submission.ai_score
    return SubmissionDetailResponse(
        id=submission.id,
        student_name=submission.student.name,
        ticket_title=submission.ticket.title,
        writeup=submission.writeup,
        ai_score=score,
        ai_feedback=submission.ai_feedback,
        xp_awarded=submission.xp_awarded,
    )


@router.put("/submissions/{submission_id}/override", response_model=OverrideResponse)
def override_grade(submission_id: int, payload: OverrideRequest, db: Session = Depends(get_db)):
    submission = db.query(TicketSubmission).filter(TicketSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    student = db.query(Student).filter(Student.id == submission.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    old_score = submission.override_score if submission.overridden and submission.override_score is not None else submission.ai_score
    old_xp = old_score * 10
    new_xp = payload.new_score * 10
    diff = new_xp - old_xp

    submission.overridden = True
    submission.override_score = payload.new_score
    submission.xp_awarded += diff
    student.total_xp += diff

    db.commit()
    logger.info(
        "grade_override submission_id=%s old_score=%s new_score=%s xp_diff=%s student_id=%s",
        submission.id,
        old_score,
        payload.new_score,
        diff,
        student.id,
    )

    return OverrideResponse(
        submission_id=submission.id,
        old_score=old_score,
        new_score=payload.new_score,
        xp_difference=diff,
        student_new_total_xp=student.total_xp,
    )
