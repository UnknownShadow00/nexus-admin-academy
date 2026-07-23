"""Week 0 orientation walkthrough regression coverage."""

import json

from conftest import auth_headers, make_client, make_student
from app.models.ai_rate_limit import AIRateLimit
from app.models.learning import Lesson, Module
from app.models.onboarding import StudentOnboardingPractice
from app.models.progression import PromotionGate, Role
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.models.ticket import TicketSubmission
from app.models.xp_ledger import XPLedger
from app.routers.lesson_notes import LessonNoteRequest, save_lesson_note
from app.routers.onboarding import OrientationPracticeRequest, get_onboarding_progress, save_orientation_practice
from app.routers.students import get_leaderboard, get_student_stats, get_week_plan
from app.routers.tickets import router as tickets_router
from app.routers.admin_students import student_activity
from app.services.progression_service import check_promotion_eligibility

ORIENTATION_TITLE = "Welcome to Nexus: Your First Week"

client = make_client(tickets_router)


def _seed_orientation(db):
    week_zero = Module(code="MOD-000", title="Troubleshooting Methodology", module_order=0)
    week_one = Module(code="MOD-001", title="The Ticket Is the Job", module_order=1)
    db.add_all([week_zero, week_one])
    db.flush()
    orientation = Lesson(module_id=week_zero.id, title=ORIENTATION_TITLE, lesson_order=1, status="published")
    methodology = Lesson(module_id=week_zero.id, title="CompTIA 6-Step Process", lesson_order=2, status="published")
    first_week_one_lesson = Lesson(module_id=week_one.id, title="Anatomy of a Good Ticket", lesson_order=1, status="published")
    quiz = Quiz(
        title="Ticketing Systems Quiz",
        week_number=0,
        question_count=1,
        status=QUIZ_STATUS_PUBLISHED,
        quiz_purpose="required",
        is_required=True,
        show_in_weekly_checklist=True,
        show_in_practice_library=False,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
        is_active=True,
    )
    db.add_all([orientation, methodology, first_week_one_lesson, quiz])
    db.flush()
    question = Question(
        quiz_id=quiz.id,
        question_text="Where do you find the next task?",
        option_a="Home → This Week",
        option_b="By guessing",
        option_c="Only from a mentor",
        option_d="Nowhere",
        correct_answer="A",
        explanation="Home shows This Week and its next action.",
    )
    db.add(question)
    db.commit()
    return orientation, quiz, question, first_week_one_lesson


def test_fresh_student_can_resume_and_complete_orientation_without_ticket_grading(db):
    student = make_student(db)
    orientation, quiz, question, first_week_one_lesson = _seed_orientation(db)

    # The Home-page-equivalent server response identifies a real fresh student;
    # it is not a browser flag and does not contain returning-user copy.
    home = get_student_stats(student.id, db=db, current_student=student)
    assert home["onboarding"]["is_fresh"] is True
    assert home["onboarding"]["lesson_id"] == orientation.id
    assert "pick up where you left off" not in json.dumps(home).lower()

    progress = get_onboarding_progress(db=db, current_student=student)
    assert progress["data"]["steps"] == {
        "lesson_note": False,
        "quiz": False,
        "practice_response": False,
        "optional_evidence": False,
    }

    note = save_lesson_note(
        orientation.id,
        LessonNoteRequest(content="I will check Home → This Week."),
        db=db,
        current_student=student,
    )
    assert note["data"]["content"] == "I will check Home → This Week."

    # Simulate leaving and resuming with a new request: completion is in DB.
    resumed = get_onboarding_progress(db=db, current_student=student)
    assert resumed["data"]["steps"]["lesson_note"] is True
    assert resumed["data"]["is_complete"] is False

    # The existing quiz endpoint has its own scoring coverage. Seed its normal
    # persisted result here so this regression stays focused on onboarding
    # state rather than unrelated milestone notifications.
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={str(question.id): "A"},
            results=[],
            score=1,
            xp_awarded=100,
            best_score=1,
            first_attempt_xp=100,
        )
    )
    db.add(XPLedger(student_id=student.id, source_type="quiz", source_id=quiz.id, delta=100, description="Ticketing Systems Quiz"))
    student.total_xp = 100  # existing required quiz policy, not orientation practice XP
    db.commit()

    db.refresh(student)
    xp_after_required_quiz = student.total_xp
    ai_limit_count = db.query(AIRateLimit).filter(AIRateLimit.user_id == student.id).count()
    ticket_count = db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id).count()
    leader = make_student(db, username="leader")
    leader.total_xp = 1000
    role = Role(name="Support Technician I", rank_order=1)
    db.add(role)
    db.flush()
    db.add(
        PromotionGate(
            role_id=role.id,
            requirement_type="min_verified_tickets_by_difficulty",
            requirement_config={"thresholds": {"1": 1, "2": 1}},
        )
    )
    db.commit()
    ticket_gate_before = check_promotion_eligibility(student.id, role.id, db)

    practice = save_orientation_practice(
        OrientationPracticeRequest(response="I would open This Week and choose Next up."),
        db=db,
        current_student=student,
    )
    assert practice["data"]["onboarding"]["is_complete"] is True

    # Zero-stakes practice does not create a ticket, AI rate-limit row, XP, or
    # promotion-relevant ticket completion; therefore it cannot distort rank.
    db.refresh(student)
    assert student.total_xp == xp_after_required_quiz
    assert db.query(AIRateLimit).filter(AIRateLimit.user_id == student.id).count() == ai_limit_count == 0
    assert db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id).count() == ticket_count == 0
    assert db.query(StudentOnboardingPractice).filter(StudentOnboardingPractice.student_id == student.id).count() == 1
    assert check_promotion_eligibility(student.id, role.id, db)["requirements_missing"][0]["progress"] == ticket_gate_before["requirements_missing"][0]["progress"]
    leaderboard = get_leaderboard(db=db, current_student=student)
    assert [row["student_id"] for row in leaderboard["data"]][:2] == [leader.id, student.id]

    finished = get_onboarding_progress(db=db, current_student=student)
    assert finished["data"]["is_complete"] is True
    assert finished["data"]["is_fresh"] is False
    assert finished["data"]["available_later"] is True

    # The final UI CTA resolves this from the Week Plan API, not a guessed URL.
    week_one = get_week_plan(week=1, db=db, current_student=student)
    next_action = week_one["data"]["next_action"]
    assert next_action["title"] == first_week_one_lesson.title
    assert next_action["route"] == f"/lessons/{first_week_one_lesson.id}"


def test_orientation_completion_reports_the_remaining_week_zero_lesson_until_week_one_unlocks(db):
    student = make_student(db)
    orientation, quiz, question, _ = _seed_orientation(db)

    save_lesson_note(
        orientation.id,
        LessonNoteRequest(content="I will start from Home → This Week."),
        db=db,
        current_student=student,
    )
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={str(question.id): "A"},
            results=[],
            score=1,
            xp_awarded=0,
            best_score=1,
            first_attempt_xp=0,
        )
    )
    db.commit()
    save_orientation_practice(
        OrientationPracticeRequest(response="I would select the next item from This Week."),
        db=db,
        current_student=student,
    )

    methodology = db.query(Lesson).filter(Lesson.title == "CompTIA 6-Step Process").one()
    progress = get_onboarding_progress(db=db, current_student=student)["data"]
    assert progress["is_complete"] is True
    assert progress["week_one_unlocked"] is False
    assert progress["week_one_remaining_lessons"] == [
        {
            "id": methodology.id,
            "title": methodology.title,
            "route": f"/lessons/{methodology.id}",
        }
    ]

    from app.models.ticket import Ticket

    ticket = Ticket(
        title="Week 1 ticket",
        description="Troubleshoot the issue.",
        difficulty=1,
        week_number=1,
        hints=["Check the cable connection."],
    )
    db.add(ticket)
    db.commit()
    blocked = client.post(f"/api/tickets/{ticket.id}/hint", headers=auth_headers(student))
    assert blocked.status_code == 403
    assert blocked.json() == {
        "success": False,
        "code": "PREREQUISITE_NOT_MET",
        "error": "Complete Week 0's required lesson first.",
        "data": {
            "required_week": 1,
            "current_week": 0,
            "next_action_route": "/training",
        },
    }

    save_lesson_note(
        methodology.id,
        LessonNoteRequest(content="I will follow the six-step process before changing anything."),
        db=db,
        current_student=student,
    )
    unlocked = get_onboarding_progress(db=db, current_student=student)["data"]
    assert unlocked["week_one_unlocked"] is True
    assert unlocked["week_one_remaining_lessons"] == []
    assert client.post(f"/api/tickets/{ticket.id}/hint", headers=auth_headers(student)).status_code == 200


def test_admin_activity_includes_student_onboarding_progress(db):
    student = make_student(db)
    orientation, _, _, _ = _seed_orientation(db)
    save_lesson_note(
        orientation.id,
        LessonNoteRequest(content="I will use Home → This Week."),
        db=db,
        current_student=student,
    )

    response = student_activity(student.id, db=db)

    assert response["data"]["onboarding"]["lesson_id"] == orientation.id
    assert response["data"]["onboarding"]["steps"]["lesson_note"] is True
