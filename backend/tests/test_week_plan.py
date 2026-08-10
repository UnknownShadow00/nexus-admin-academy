"""TB-03: 'This Week' dashboard endpoint tests."""
from datetime import datetime, timezone

from conftest import auth_headers, make_client, make_student
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Quiz
from app.models.ticket import Ticket, TicketSubmission
from app.routers.students import router as students_router

client = make_client(students_router)


def _seed_week1(db):
    module = Module(code="MOD-001", title="The Ticket Is the Job", module_order=1)
    db.add(module)
    db.flush()
    l1 = Lesson(module_id=module.id, title="Anatomy of a Good Ticket", lesson_order=1, status="published")
    l2 = Lesson(module_id=module.id, title="Meet the Command Line", lesson_order=2, status="published")
    draft = Lesson(module_id=module.id, title="Unpublished Draft", lesson_order=3, status="draft")
    quiz = Quiz(
        title="Ticket Writing Quiz",
        week_number=1,
        status=QUIZ_STATUS_PUBLISHED,
        quiz_purpose="required",
        is_required=True,
        show_in_weekly_checklist=True,
        answer_keys_validated=True,
        editorial_status="validated",
        is_active=True,
    )
    cli = CliLab(id="mtc-01", title="First Commands", compartment_id="meet-the-cli", vendor_id="cisco", content={}, order_index=1)
    db.add_all([l1, l2, draft, quiz, cli])
    db.commit()
    return module, l1, l2, quiz, cli


def test_week_plan_statuses_and_progress(db):
    student = make_student(db)
    module, l1, l2, quiz, cli = _seed_week1(db)
    # complete one lesson and the CLI lab
    db.add(StudentLessonNote(student_id=student.id, lesson_id=l1.id, content="notes"))
    db.add(CliLabAttempt(student_id=student.id, lab_id=cli.id, completed_at=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/api/students/me/week-plan?week=1", headers=auth_headers(student))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["week"] == 1

    lessons = {lesson["title"]: lesson["status"] for lesson in data["lessons"]}
    assert lessons["Anatomy of a Good Ticket"] == "done"
    assert lessons["Meet the Command Line"] == "available"
    assert "Unpublished Draft" not in lessons  # drafts hidden

    assert data["cli_labs"][0]["status"] == "done"
    assert data["quizzes"][0]["status"] == "available"
    assert "tickets" not in data
    # 2 done of 4 visible items; legacy Support Tickets are retired.
    assert data["progress_percent"] == 50.0
    # next action is the first incomplete item in pedagogical order (a lesson)
    assert data["next_action"]["title"] == "Meet the Command Line"
    assert data["next_action"]["route"] == f"/lessons/{l2.id}"


def test_week_plan_excludes_retired_ticket_history(db):
    student = make_student(db)
    _seed_week1(db)
    ticket = Ticket(title="Retired DNS ticket", description="d", difficulty=1, week_number=1)
    db.add(ticket)
    db.flush()
    db.add(TicketSubmission(student_id=student.id, ticket_id=ticket.id, writeup="w", status="pending", xp_awarded=0))
    db.commit()

    r = client.get("/api/students/me/week-plan?week=1", headers=auth_headers(student))
    data = r.json()["data"]
    assert "tickets" not in data
    assert data["progress_percent"] == 0.0


def test_week_plan_scoped_to_own_data(db):
    """Another student's completions must never appear in my plan."""
    s1 = make_student(db)
    s2 = make_student(db, username="student2")
    module, l1, l2, quiz, cli = _seed_week1(db)
    db.add(StudentLessonNote(student_id=s2.id, lesson_id=l1.id, content="s2 notes"))
    db.commit()
    r = client.get("/api/students/me/week-plan?week=1", headers=auth_headers(s1))
    lessons = {lesson["title"]: lesson["status"] for lesson in r.json()["data"]["lessons"]}
    assert lessons["Anatomy of a Good Ticket"] == "available"  # s2's note is not mine


def test_week_plan_requires_auth(db):
    _seed_week1(db)
    r = client.get("/api/students/me/week-plan?week=1")
    assert r.status_code in (401, 403)
