"""Week 0 orientation walkthrough regression coverage."""

import json
from datetime import datetime, timezone

from conftest import auth_headers, make_client, make_student
from app.models.ai_rate_limit import AIRateLimit
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.progression import PromotionGate, Role
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.models.ticket import TicketSubmission
from app.models.xp_ledger import XPLedger
from app.routers.lesson_notes import LessonNoteRequest, router as lesson_router, save_lesson_note
from app.routers.onboarding import get_onboarding_progress
from app.routers.students import get_leaderboard, get_student_stats, get_week_plan
from app.routers.tickets import router as tickets_router
from app.routers.admin_students import student_activity
from app.services.progression_service import check_promotion_eligibility

ORIENTATION_TITLE = "Welcome to Nexus: Your First Week"

client = make_client(tickets_router, lesson_router)


def _seed_orientation(db):
    week_zero = Module(code="MOD-000", title="Troubleshooting Methodology", module_order=0)
    week_one = Module(code="MOD-001", title="The Ticket Is the Job", module_order=1)
    db.add_all([week_zero, week_one])
    db.flush()
    # Reproduce the production regression: the Phase A content seed restored
    # this retired mastery prerequisite after migration 0030 had removed it.
    week_one.prerequisite_module_id = week_zero.id
    orientation = Lesson(module_id=week_zero.id, title=ORIENTATION_TITLE, lesson_order=1, status="published")
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
    db.add_all([orientation, first_week_one_lesson, quiz])
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


def _complete_orientation(db, student, orientation):
    db.add(
        StudentLessonProgress(
            student_id=student.id,
            lesson_id=orientation.id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def _pass_quiz(db, student, quiz, question):
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
    assert progress["data"]["steps"] == {"lesson_completion": False, "quiz": False}
    assert progress["data"]["is_complete"] is False
    assert progress["data"]["week_one_unlocked"] is False

    locked = client.get(f"/api/lessons/{first_week_one_lesson.id}", headers=auth_headers(student))
    assert locked.status_code == 403
    assert locked.json()["error"] == "Complete the required lesson and quiz in Nexus Orientation first."

    note = save_lesson_note(
        orientation.id,
        LessonNoteRequest(content="I will check Home → This Week."),
        db=db,
        current_student=student,
    )
    assert note["data"]["content"] == "I will check Home → This Week."

    # Notes are optional study aids and never complete the walkthrough.
    resumed = get_onboarding_progress(db=db, current_student=student)
    assert resumed["data"]["steps"]["lesson_completion"] is False
    assert resumed["data"]["is_complete"] is False

    _complete_orientation(db, student, orientation)
    orientation_only = get_onboarding_progress(db=db, current_student=student)["data"]
    assert orientation_only["steps"] == {"lesson_completion": True, "quiz": False}
    assert orientation_only["is_complete"] is False
    locked = client.get(f"/api/lessons/{first_week_one_lesson.id}", headers=auth_headers(student))
    assert locked.status_code == 403
    assert locked.json()["error"] == "Complete the required quiz in Nexus Orientation first."

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

    # Finishing the two current requirements does not create a ticket, AI
    # rate-limit row, or promotion-relevant completion; therefore it cannot
    # distort rank.
    db.refresh(student)
    assert student.total_xp == xp_after_required_quiz
    assert db.query(AIRateLimit).filter(AIRateLimit.user_id == student.id).count() == ai_limit_count == 0
    assert db.query(TicketSubmission).filter(TicketSubmission.student_id == student.id).count() == ticket_count == 0
    assert check_promotion_eligibility(student.id, role.id, db)["requirements_missing"][0]["progress"] == ticket_gate_before["requirements_missing"][0]["progress"]
    leaderboard = get_leaderboard(db=db, current_student=student)
    assert [row["student_id"] for row in leaderboard["data"]][:2] == [leader.id, student.id]

    finished = get_onboarding_progress(db=db, current_student=student)
    assert finished["data"]["is_complete"] is True
    assert finished["data"]["week_one_unlocked"] is True
    assert finished["data"]["is_fresh"] is False
    assert finished["data"]["available_later"] is True

    # The final UI CTA resolves this from the Week Plan API, not a guessed URL.
    week_one = get_week_plan(week=1, db=db, current_student=student)
    next_action = week_one["data"]["next_action"]
    assert next_action["title"] == first_week_one_lesson.title
    assert next_action["route"] == f"/lessons/{first_week_one_lesson.id}"

    # Direct route authorization is server-authoritative and survives a fresh
    # request, regardless of the stale legacy module prerequisite reproduced
    # by this fixture.
    opened = client.get(f"/api/lessons/{first_week_one_lesson.id}", headers=auth_headers(student))
    assert opened.status_code == 200
    assert opened.json()["data"]["title"] == first_week_one_lesson.title

    other = make_student(db, username="fresh-isolated-student")
    other_locked = client.get(f"/api/lessons/{first_week_one_lesson.id}", headers=auth_headers(other))
    assert other_locked.status_code == 403
    assert get_onboarding_progress(db=db, current_student=other)["data"]["week_one_unlocked"] is False


def test_quiz_without_orientation_keeps_week_one_locked(db):
    student = make_student(db)
    _, quiz, question, first_week_one_lesson = _seed_orientation(db)

    _pass_quiz(db, student, quiz, question)

    progress = get_onboarding_progress(db=db, current_student=student)["data"]
    assert progress["steps"] == {"lesson_completion": False, "quiz": True}
    assert progress["is_complete"] is False
    assert progress["week_one_unlocked"] is False
    locked = client.get(f"/api/lessons/{first_week_one_lesson.id}", headers=auth_headers(student))
    assert locked.status_code == 403
    assert locked.json()["error"] == "Complete the required lesson in Nexus Orientation first."


def test_orientation_completion_unlocks_week_one_without_retired_methodology_lesson(db):
    student = make_student(db)
    orientation, quiz, question, first_week_one_lesson = _seed_orientation(db)

    _complete_orientation(db, student, orientation)
    _pass_quiz(db, student, quiz, question)

    progress = get_onboarding_progress(db=db, current_student=student)["data"]
    assert progress["is_complete"] is True
    assert progress["week_one_unlocked"] is True
    assert progress["week_one_remaining_lessons"] == []
    assert client.get(f"/api/lessons/{first_week_one_lesson.id}", headers=auth_headers(student)).status_code == 200

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
    assert client.post(f"/api/tickets/{ticket.id}/hint", headers=auth_headers(student)).status_code == 200


def test_admin_activity_includes_student_onboarding_progress(db):
    student = make_student(db)
    orientation, _, _, _ = _seed_orientation(db)
    db.add(StudentLessonProgress(student_id=student.id, lesson_id=orientation.id, completed_at=datetime.now(timezone.utc)))
    db.commit()

    response = student_activity(student.id, db=db)

    assert response["data"]["onboarding"]["lesson_id"] == orientation.id
    assert response["data"]["onboarding"]["steps"]["lesson_completion"] is True
