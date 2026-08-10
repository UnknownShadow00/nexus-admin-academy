"""Regression coverage for curriculum-week prerequisite enforcement."""

from datetime import datetime, timezone

from conftest import auth_headers, make_client, make_student

from app.models.capstone import CapstoneTemplate
from app.models.cli_lab import CliLab
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabTemplate
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.progression import Role, StudentRole
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Quiz, QuizAttempt
from app.models.ticket import Ticket
from app.models.video_watch import VideoWatch
from app.routers.capstones import has_unlocked_capstones, router as capstones_router
from app.routers.cli_labs import router as cli_labs_router
from app.routers.labs import router as labs_router
from app.routers.students import router as students_router
from app.routers.tickets import router as tickets_router
from seed import seed_capstones
from seed_phase_g import seed_phase_g


client = make_client(tickets_router, labs_router, cli_labs_router, capstones_router, students_router)


def _ticket_payload(student_id):
    return {
        "student_id": student_id,
        "symptom": "The workstation cannot connect.",
        "root_cause": "The cable is disconnected.",
        "resolution": "Reconnect the cable.",
        "verification": "Confirmed successful connectivity.",
    }


def _seed_week_zero_gate(db):
    week_zero_quiz = Quiz(
        title="Week 0 required quiz",
        week_number=0,
        question_count=1,
        status=QUIZ_STATUS_PUBLISHED,
        quiz_purpose="required",
        is_required=True,
        show_in_weekly_checklist=True,
        answer_keys_validated=True,
        editorial_status="validated",
        is_active=True,
    )
    week_one_module = Module(code="MOD-001", title="Week 1", module_order=1)
    db.add_all([week_zero_quiz, week_one_module])
    db.flush()
    db.add(Lesson(module_id=week_one_module.id, title="Week 1 lesson", lesson_order=1, status="published"))
    db.commit()
    return week_zero_quiz


def _pass_week_zero(db, student_id, quiz):
    db.add(QuizAttempt(student_id=student_id, quiz_id=quiz.id, answers={}, score=1, xp_awarded=0))
    db.commit()


def _seed_hands_on_week_one(db):
    ticket = Ticket(title="Week 1 ticket", description="Troubleshoot.", difficulty=1, week_number=1)
    lab = LabTemplate(
        title="Week 1 lab",
        description="Practice.",
        lab_type="guided",
        difficulty=1,
        week_number=1,
        environment_requirements={},
        success_criteria={},
        required_evidence={},
        hints={},
        is_published=True,
    )
    cli_lab = CliLab(
        id="meet-cli-week-one",
        compartment_id="meet-the-cli",
        vendor_id="cisco-ios",
        title="Meet the CLI",
        content={},
    )
    capstone = CapstoneTemplate(
        title="Week 1 capstone",
        week_number=1,
        is_published=True,
        requirements={},
        deliverables={},
        rubric={},
    )
    db.add_all([ticket, lab, cli_lab, capstone])
    db.commit()
    return ticket, lab, cli_lab, capstone


def test_fresh_student_ticket_lock_has_exact_prerequisite_contract(db):
    student = make_student(db)
    _seed_week_zero_gate(db)
    ticket, *_ = _seed_hands_on_week_one(db)

    response = client.post(f"/api/tickets/{ticket.id}/submit", json=_ticket_payload(student.id), headers=auth_headers(student))

    assert response.status_code == 403
    assert response.json() == {
        "success": False,
        "code": "PREREQUISITE_NOT_MET",
        "error": "Complete Week 0's required quiz first.",
        "data": {
            "required_week": 1,
            "current_week": 0,
            "next_action_route": "/quizzes/1",
        },
    }


def test_direct_ticket_submit_api_cannot_bypass_week_prerequisite(db):
    """The submit endpoint itself enforces the rule; no UI state is involved."""
    student = make_student(db, username="direct-api")
    _seed_week_zero_gate(db)
    ticket, *_ = _seed_hands_on_week_one(db)

    response = client.post(f"/api/tickets/{ticket.id}/submit", json=_ticket_payload(student.id), headers=auth_headers(student))

    assert response.status_code == 403
    assert response.json()["code"] == "PREREQUISITE_NOT_MET"
    assert response.json()["data"]["required_week"] == 1
    assert response.json()["data"]["current_week"] == 0


def test_passing_week_zero_allows_direct_week_one_ticket_submission(monkeypatch, db):
    student = make_student(db)
    week_zero_quiz = _seed_week_zero_gate(db)
    _pass_week_zero(db, student.id, week_zero_quiz)
    ticket, *_ = _seed_hands_on_week_one(db)

    async def fake_grade(**_kwargs):
        return {
            "final_score": 8,
            "structure_score": 8,
            "technical_score": 8,
            "communication_score": 8,
            "strengths": [],
            "weaknesses": [],
            "feedback": "Good work",
            "anchors": [],
            "checkpoints_met": [],
            "checkpoints_missed": [],
        }

    monkeypatch.setattr("app.routers.tickets.grade_ticket_submission", fake_grade)
    response = client.post(f"/api/tickets/{ticket.id}/submit", json=_ticket_payload(student.id), headers=auth_headers(student))

    assert response.status_code == 200


def test_later_week_ticket_remains_locked_by_general_week_rule(db):
    student = make_student(db)
    week_zero_quiz = _seed_week_zero_gate(db)
    _pass_week_zero(db, student.id, week_zero_quiz)
    ticket = Ticket(title="Week 3 ticket", description="Troubleshoot.", difficulty=1, week_number=3)
    db.add(ticket)
    db.commit()

    response = client.post(f"/api/tickets/{ticket.id}/submit", json=_ticket_payload(student.id), headers=auth_headers(student))

    assert response.status_code == 403
    assert response.json()["code"] == "PREREQUISITE_NOT_MET"
    assert response.json()["data"] == {
        "required_week": 3,
        "current_week": 1,
        "next_action_route": "/training",
    }
    assert response.json()["error"] == "You'll unlock this once you reach Week 3."


def test_a_plus_video_progress_never_changes_hands_on_week_access(db):
    student = make_student(db)
    _seed_week_zero_gate(db)
    ticket, lab, cli_lab, capstone = _seed_hands_on_week_one(db)
    videos = [
        CurriculumVideo(
            video_key=f"a-plus-{index}",
            section="A+",
            section_order=1,
            title=f"A+ {index}",
            exam_code="220-1201",
            video_order=index,
            active=True,
        )
        for index in range(3)
    ]
    db.add_all(videos)
    db.commit()
    headers = auth_headers(student)

    def action_statuses():
        return [
            client.post(f"/api/tickets/{ticket.id}/submit", json=_ticket_payload(student.id), headers=headers),
            client.post(f"/api/labs/{lab.id}/start", headers=headers),
            client.post(f"/api/cli-labs/{cli_lab.id}/complete", json={"commandLog": [], "durationMs": 1}, headers=headers),
            client.post(f"/api/capstones/{capstone.id}/start", headers=headers),
        ]

    zero_watched = action_statuses()
    db.add_all(VideoWatch(student_id=student.id, video_key=video.video_key) for video in videos)
    db.commit()
    all_watched = action_statuses()

    assert [response.status_code for response in zero_watched] == [403, 403, 403, 403]
    assert [response.status_code for response in all_watched] == [403, 403, 403, 403]
    assert all(response.json()["code"] == "PREREQUISITE_NOT_MET" for response in zero_watched + all_watched)


def test_mod_001_learning_path_uses_current_week_zero_requirements(db):
    student = make_student(db)
    week_zero = Module(code="MOD-000", title="Week 0", module_order=0)
    week_one = Module(code="MOD-001", title="The Ticket Is the Job", module_order=1, prerequisite_module_id=None)
    db.add_all([week_zero, week_one])
    db.flush()
    orientation = Lesson(module_id=week_zero.id, title="Week 0 lesson", lesson_order=1, status="published")
    checkpoint = Quiz(
        title="Ticketing Systems Quiz",
        week_number=0,
        question_count=1,
        status=QUIZ_STATUS_PUBLISHED,
        quiz_purpose="required",
        is_required=True,
        show_in_weekly_checklist=True,
        answer_keys_validated=True,
        editorial_status="validated",
        is_active=True,
    )
    db.add_all([
        orientation,
        Lesson(module_id=week_one.id, title="Anatomy of a Good Ticket", lesson_order=1, status="published"),
        Lesson(module_id=week_one.id, title="Meet the Command Line", lesson_order=2, status="published"),
        checkpoint,
    ])
    db.commit()

    def week_one_state():
        response = client.get(f"/api/students/{student.id}/learning-path", headers=auth_headers(student))
        assert response.status_code == 200
        return next(module for module in response.json()["modules"] if module["code"] == "MOD-001")

    fresh = week_one_state()
    assert fresh["unlocked"] is False
    assert fresh["unlock_requirements"] == ["Complete Week 0's required work first."]

    db.add(
        StudentLessonProgress(
            student_id=student.id,
            lesson_id=orientation.id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    orientation_only = week_one_state()
    assert orientation_only["unlocked"] is False

    db.add(QuizAttempt(student_id=student.id, quiz_id=checkpoint.id, answers={}, score=1, xp_awarded=0))
    db.commit()

    complete = week_one_state()
    assert complete["unlocked"] is True
    assert complete["unlock_requirements"] == []


def test_capstone_role_levels_block_fresh_trainee_and_allow_required_rank(db):
    trainee = make_student(db, username="trainee")
    qualified = make_student(db, username="qualified")
    roles = [
        Role(name="Support Technician I", rank_order=2),
        Role(name="Support Technician II", rank_order=3),
        Role(name="Junior Systems Technician", rank_order=5),
    ]
    db.add_all(roles)
    db.flush()
    capstones = [
        CapstoneTemplate(id=1, title="CompTIA A+ Module 1 Capstone: Hardware & Troubleshooting", week_number=4, role_level=roles[0].id, is_published=True),
        CapstoneTemplate(id=2, title="CompTIA A+ Module 2 Capstone: Networking & OS", week_number=8, role_level=roles[1].id, is_published=True),
        CapstoneTemplate(id=3, title="Take Over Maple & Finch Co.", week_number=24, role_level=roles[2].id, is_published=True),
    ]
    db.add_all(capstones)
    db.add(StudentRole(student_id=qualified.id, role_id=roles[2].id))
    db.commit()

    trainee_response = client.get("/api/capstones", headers=auth_headers(trainee))
    qualified_response = client.get("/api/capstones", headers=auth_headers(qualified))

    assert trainee_response.status_code == 200
    assert trainee_response.json()["data"] == []
    assert has_unlocked_capstones(db, trainee) is False
    assert qualified_response.status_code == 200
    assert {row["id"] for row in qualified_response.json()["data"]} == {1, 2, 3}
    assert has_unlocked_capstones(db, qualified) is True


def test_fresh_database_seeds_assign_all_capstone_role_levels(db):
    roles = [
        Role(name="Support Technician I", rank_order=2),
        Role(name="Support Technician II", rank_order=3),
        Role(name="Junior Systems Technician", rank_order=5),
    ]
    db.add_all(roles)
    db.flush()

    seed_capstones(db)
    seed_phase_g(db)
    db.commit()

    role_by_title = {
        capstone.title: db.get(Role, capstone.role_level).rank_order
        for capstone in db.query(CapstoneTemplate).all()
    }
    assert role_by_title == {
        "CompTIA A+ Module 1 Capstone: Hardware & Troubleshooting": 2,
        "CompTIA A+ Module 2 Capstone: Networking & OS": 3,
        "Take Over Maple & Finch Co.": 5,
    }
