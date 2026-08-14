import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models.ai_rate_limit import AIRateLimit
from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.evidence import EvidenceArtifact
from app.models.flashcard import FlashcardReview
from app.models.incident import Incident, IncidentParticipant, RCASubmission
from app.models.lab import LabRun, LabTemplate
from app.models.lesson_notes import StudentLessonNote
from app.models.lesson_progress import StudentLessonProgress
from app.models.login_streak import LoginStreak
from app.models.learning import Lesson, Module
from app.models.mastery import StudentDomainMastery
from app.models.onboarding import StudentOnboardingPractice
from app.models.progression import MethodologyFramework, Role, StudentMethodologyProgress, StudentRole
from app.models.quiz import Question, Quiz, QuizAssignment, QuizAttempt
from app.models.comptia import ComptiaObjective, StudentObjectiveProgress
from app.models.squad_activity import SquadActivity
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskAttemptGrade,
    ServiceDeskBetaEnrollment,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.video_watch import VideoWatch
from app.models.vm_assignment import VmAssignment
from app.models.weekly_lead import WeeklyDomainLead
from app.models.xp_ledger import XPLedger
from app.routers.admin_students import router as admin_students_router
from app.services.admin_auth import verify_admin
from app.services.student_deletion import (
    global_student_ownership_orphans,
    remaining_student_owned_rows,
    student_owned_row_counts,
)
from scripts.repair_orphaned_student_data import find_orphans, repair_orphans


def _admin_client(db):
    app = FastAPI()
    app.include_router(admin_students_router)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[verify_admin] = lambda: True
    return TestClient(app)


def _student_payload(suffix: str) -> dict:
    return {
        "name": "Disposable Student",
        "email": f"disposable-{suffix}@test.local",
        "username": f"disposable-{suffix}",
        "password": "safe-test-password",
    }


def test_sqlite_connections_enable_foreign_keys(db):
    assert db.connection().exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


def test_admin_create_delete_and_id_reuse_leave_no_orphans(db):
    role = Role(name="Trainee", rank_order=1)
    frameworks = [
        MethodologyFramework(name="Troubleshooting", steps={}),
        MethodologyFramework(name="Documentation", steps={}),
    ]
    module = Module(code="DEL-MIN", title="Deletion minimal shared curriculum")
    db.add_all([role, *frameworks, module])
    db.flush()
    lesson = Lesson(module_id=module.id, title="Deletion minimal lesson", lesson_order=1, outcomes=[])
    db.add(lesson)
    db.commit()
    client = _admin_client(db)

    created = client.post("/api/admin/students", json=_student_payload("one"))
    assert created.status_code == 200
    student_id = created.json()["data"]["student_id"]
    assert (
        db.query(StudentMethodologyProgress)
        .filter(StudentMethodologyProgress.student_id == student_id)
        .count()
        == 2
    )

    db.add_all(
        [
            LoginStreak(student_id=student_id),
            SquadActivity(
                student_id=student_id,
                activity_type="test",
                title="Disposable activity",
            ),
            StudentDomainMastery(student_id=student_id, domain_id="1.0"),
            WeeklyDomainLead(
                week_key="2026-W01",
                domain_id="1.0",
                student_id=student_id,
                badge_name="Disposable",
            ),
            EvidenceArtifact(
                student_id=student_id,
                submission_type="lab",
                submission_id=999,
                artifact_type="screenshot",
                storage_key="disposable.png",
            ),
            StudentLessonProgress(student_id=student_id, lesson_id=lesson.id),
            StudentLessonNote(student_id=student_id, lesson_id=lesson.id, content="Optional note"),
        ]
    )
    scenario = ServiceDeskScenario(
        stable_key="disposable-cleanup",
        title="Disposable cleanup scenario",
        category="service_desk",
        difficulty=1,
    )
    db.add(scenario)
    db.flush()
    version = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=1,
        definition_json={},
        definition_hash="d" * 64,
        validation_status="valid",
        status="published",
    )
    db.add(version)
    db.flush()
    assignment = ServiceDeskAssignment(
        student_id=student_id,
        scenario_id=scenario.id,
        mode="simulation",
        assigned_by="admin",
    )
    attempt = ServiceDeskAttempt(
        student_id=student_id,
        scenario_version_id=version.id,
        mode="simulation",
        status="completed",
        current_state={},
        current_state_hash="a" * 64,
        state_version=1,
        attempt_number=1,
        score=100,
        passed=True,
    )
    enrollment = ServiceDeskBetaEnrollment(
        student_id=student_id,
        enabled=True,
        enrolled_by="admin",
    )
    db.add_all([assignment, attempt, enrollment])
    db.flush()
    attempt_id = attempt.id
    event = ServiceDeskAttemptEvent(
        attempt_id=attempt.id,
        sequence_number=1,
        idempotency_key="disposable-cleanup-event",
        event_type="ticket.close",
        tool="ticket",
        payload_json={},
        previous_state_hash="0" * 64,
        resulting_state_hash="a" * 64,
        success=True,
        trusted=True,
    )
    grade = ServiceDeskAttemptGrade(
        attempt_id=attempt.id,
        scenario_version_id=version.id,
        rubric_version="test-v1",
        technical_complete=True,
        critical_failure=False,
        overall_score=100,
        passed=True,
        feedback_summary="Passed",
        details_json={},
    )
    db.add_all([event, grade])
    db.commit()
    attempt_id = attempt.id

    deleted = client.delete(f"/api/admin/students/{student_id}")
    assert deleted.status_code == 200
    db.expire_all()
    assert db.query(Student).filter(Student.id == student_id).count() == 0
    assert db.query(StudentMethodologyProgress).filter_by(student_id=student_id).count() == 0
    assert db.query(LoginStreak).filter_by(student_id=student_id).count() == 0
    assert db.query(SquadActivity).filter_by(student_id=student_id).count() == 0
    assert db.query(StudentDomainMastery).filter_by(student_id=student_id).count() == 0
    assert db.query(WeeklyDomainLead).filter_by(student_id=student_id).count() == 0
    assert db.query(ServiceDeskAssignment).filter_by(student_id=student_id).count() == 0
    assert db.query(ServiceDeskAttempt).filter_by(student_id=student_id).count() == 0
    assert db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt_id).count() == 0
    assert db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt_id).count() == 0
    assert db.query(ServiceDeskBetaEnrollment).filter_by(student_id=student_id).count() == 0
    assert db.query(EvidenceArtifact).filter_by(storage_key="disposable.png").count() == 0
    assert db.connection().exec_driver_sql("PRAGMA foreign_key_check").all() == []

    recreated = client.post("/api/admin/students", json=_student_payload("two"))
    assert recreated.status_code == 200
    reused_id = recreated.json()["data"]["student_id"]
    assert reused_id == student_id
    assert (
        db.query(StudentMethodologyProgress)
        .filter(StudentMethodologyProgress.student_id == reused_id)
        .count()
        == 2
    )


def test_orphan_repair_is_dry_run_transactional_and_idempotent():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE students (id INTEGER PRIMARY KEY);
        CREATE TABLE child_rows (
            id INTEGER PRIMARY KEY,
            student_id INTEGER NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        CREATE TABLE evidence_artifacts (
            id INTEGER PRIMARY KEY,
            student_id INTEGER NULL
        );
        INSERT INTO students(id) VALUES (1);
        INSERT INTO child_rows(id, student_id) VALUES (1, 1), (2, 99);
        INSERT INTO evidence_artifacts(id, student_id) VALUES (1, 98);
        """
    )

    found = find_orphans(connection)
    assert [(item.table, item.count, item.action) for item in found] == [
        ("child_rows", 1, "delete"),
        ("evidence_artifacts", 1, "set_null"),
    ]
    assert repair_orphans(connection, confirm=False) == found
    assert connection.execute("SELECT COUNT(*) FROM child_rows WHERE student_id=99").fetchone()[0] == 1

    repaired = repair_orphans(connection, confirm=True)
    assert sum(item.count for item in repaired) == 2
    assert connection.execute("SELECT COUNT(*) FROM child_rows WHERE student_id=99").fetchone()[0] == 0
    assert connection.execute("SELECT student_id FROM evidence_artifacts").fetchone()[0] is None
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert repair_orphans(connection, confirm=True) == []
    connection.close()


def test_populated_student_delete_removes_complete_owned_graph_and_preserves_shared_data(db):
    """The supported endpoint removes every mapped ownership type for one student."""
    client = _admin_client(db)
    role = Role(name="Trainee", rank_order=1)
    framework = MethodologyFramework(name="Troubleshooting", steps={})
    module = Module(code="DEL-001", title="Deletion shared curriculum")
    db.add_all([role, framework, module])
    db.flush()
    lesson = Lesson(module_id=module.id, title="Shared lesson", lesson_order=1, outcomes=[])
    quiz = Quiz(title="Shared quiz", question_count=1, week_number=1, domain_id="1.0")
    lab = LabTemplate(title="Shared lab")
    capstone = CapstoneTemplate(title="Shared capstone")
    cli_lab = CliLab(id="deletion-cli", compartment_id="core", vendor_id="nexus", title="Shared CLI lab")
    incident = Incident(title="Shared incident")
    ticket = Ticket(title="Shared ticket", description="Shared", difficulty=1, week_number=1)
    objective = ComptiaObjective(domain="1.0", objective_number="1.1", objective_text="Shared objective")
    scenario = ServiceDeskScenario(stable_key="deletion-shared", title="Shared scenario", category="service_desk", difficulty=1)
    db.add_all([lesson, quiz, lab, capstone, cli_lab, incident, ticket, objective, scenario])
    db.flush()
    question = Question(quiz_id=quiz.id, question_text="Question?", option_a="A", option_b="B", correct_answer="A", explanation="Because")
    version = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=1,
        definition_json={},
        definition_hash="p" * 64,
        validation_status="valid",
        status="published",
    )
    db.add_all([question, version])
    db.commit()

    first = client.post("/api/admin/students", json=_student_payload("populated"))
    second = client.post("/api/admin/students", json=_student_payload("control"))
    assert first.status_code == second.status_code == 200
    student_id = first.json()["data"]["student_id"]
    other_id = second.json()["data"]["student_id"]

    db.add_all(
        [
            CapstoneRun(capstone_template_id=capstone.id, student_id=student_id, status="submitted"),
            CliLabAttempt(id="deletion-cli-attempt", student_id=student_id, lab_id=cli_lab.id, xp_awarded=10, command_log=[]),
            EvidenceArtifact(student_id=student_id, submission_type="lab", submission_id=1, artifact_type="screenshot", storage_key="delete-me.png"),
            FlashcardReview(student_id=student_id, question_id=question.id),
            IncidentParticipant(incident_id=incident.id, student_id=student_id, role="responder"),
            RCASubmission(incident_id=incident.id, student_id=student_id, timeline={}),
            LabRun(lab_template_id=lab.id, student_id=student_id, status="submitted"),
            LoginStreak(student_id=student_id),
            QuizAssignment(student_id=student_id, quiz_id=quiz.id),
            QuizAttempt(student_id=student_id, quiz_id=quiz.id, answers={}, score=100, xp_awarded=10, best_score=100, first_attempt_xp=10),
            SquadActivity(student_id=student_id, activity_type="test", title="Owned activity"),
            StudentDomainMastery(student_id=student_id, domain_id="1.0"),
            StudentLessonNote(student_id=student_id, lesson_id=lesson.id, content="Owned note"),
            StudentLessonProgress(student_id=student_id, lesson_id=lesson.id, completed_at=None),
            StudentObjectiveProgress(student_id=student_id, objective_id=objective.id, mastery_level=2),
            StudentRole(student_id=student_id, role_id=role.id),
            TicketSubmission(student_id=student_id, ticket_id=ticket.id, writeup="Owned legacy history", xp_awarded=10),
            VideoWatch(student_id=student_id, video_key="owned-video"),
            WeeklyDomainLead(week_key="2026-W01", domain_id="1.0", student_id=student_id, badge_name="Owned"),
            XPLedger(student_id=student_id, source_type="test", source_id=1, delta=10),
            AIRateLimit(user_id=student_id, endpoint="delete-test"),
            StudentOnboardingPractice(student_id=student_id, response="Owned orientation"),
        ]
    )
    db.flush()
    run = db.query(LabRun).filter_by(student_id=student_id).one()
    db.add(VmAssignment(student_id=student_id, lab_run_id=run.id, status="running"))
    assignment = ServiceDeskAssignment(student_id=student_id, scenario_id=scenario.id, mode="simulation", assigned_by="test")
    attempt = ServiceDeskAttempt(student_id=student_id, scenario_version_id=version.id, mode="simulation", status="completed", current_state={}, current_state_hash="s" * 64, state_version=1, attempt_number=1, score=100, passed=True)
    enrollment = ServiceDeskBetaEnrollment(student_id=student_id, enabled=True, enrolled_by="test")
    db.add_all([assignment, attempt, enrollment])
    db.flush()
    attempt_id = attempt.id
    db.add_all([
        ServiceDeskAttemptEvent(attempt_id=attempt.id, sequence_number=1, idempotency_key="deletion-populated-event", event_type="ticket.close", tool="ticket", payload_json={}, previous_state_hash="0" * 64, resulting_state_hash="s" * 64, success=True, trusted=True),
        ServiceDeskAttemptGrade(attempt_id=attempt.id, scenario_version_id=version.id, rubric_version="test", technical_complete=True, critical_failure=False, overall_score=100, passed=True, feedback_summary="Owned mentor feedback", details_json={}, mentor_feedback="Owned feedback"),
        # The control student proves isolation for each user-facing history class.
        StudentLessonProgress(student_id=other_id, lesson_id=lesson.id),
        StudentLessonNote(student_id=other_id, lesson_id=lesson.id, content="Control note"),
        QuizAttempt(student_id=other_id, quiz_id=quiz.id, answers={}, score=80, xp_awarded=0, best_score=80, first_attempt_xp=0),
        XPLedger(student_id=other_id, source_type="test", source_id=2, delta=5),
        ServiceDeskAssignment(student_id=other_id, scenario_id=scenario.id, mode="simulation", assigned_by="test"),
    ])
    db.commit()

    # Explicit cleanup must remain complete even if a legacy SQLite client
    # opened this connection without cascade enforcement.
    connection = db.connection()
    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 0
    before = student_owned_row_counts(db, student_id)
    assert all(count > 0 for table, count in before.items() if table not in {"students", "service_desk_attempt_events", "service_desk_attempt_grades"})
    assert before["service_desk_attempt_events"] == before["service_desk_attempt_grades"] == 1
    shared_before = {table: db.query(model).count() for table, model in {
        "lessons": Lesson, "quizzes": Quiz, "questions": Question, "lab_templates": LabTemplate,
        "service_desk_scenarios": ServiceDeskScenario, "service_desk_scenario_versions": ServiceDeskScenarioVersion,
    }.items()}

    deleted = client.delete(f"/api/admin/students/{student_id}")
    assert deleted.status_code == 200
    db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    db.expire_all()
    assert remaining_student_owned_rows(db, student_id) == {}
    assert db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt_id).count() == 0
    assert db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt_id).count() == 0
    assert global_student_ownership_orphans(db) == {"service_desk_attempt_events": 0, "service_desk_attempt_grades": 0}
    assert db.connection().exec_driver_sql("PRAGMA foreign_key_check").all() == []
    assert {table: db.query(model).count() for table, model in {
        "lessons": Lesson, "quizzes": Quiz, "questions": Question, "lab_templates": LabTemplate,
        "service_desk_scenarios": ServiceDeskScenario, "service_desk_scenario_versions": ServiceDeskScenarioVersion,
    }.items()} == shared_before
    assert db.query(Student).filter_by(id=other_id).count() == 1
    assert db.query(StudentLessonProgress).filter_by(student_id=other_id).count() == 1
    assert db.query(StudentLessonNote).filter_by(student_id=other_id).count() == 1
    assert db.query(QuizAttempt).filter_by(student_id=other_id).count() == 1
    assert db.query(XPLedger).filter_by(student_id=other_id).count() == 1
    assert db.query(ServiceDeskAssignment).filter_by(student_id=other_id).count() == 1


def test_student_delete_rolls_back_everything_when_cleanup_fails(db, monkeypatch):
    client = _admin_client(db)
    module = Module(code="DEL-ROLLBACK", title="Deletion rollback shared curriculum")
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="Deletion rollback lesson", lesson_order=1, outcomes=[])
    db.add(lesson)
    db.commit()
    created = client.post("/api/admin/students", json=_student_payload("rollback"))
    student_id = created.json()["data"]["student_id"]
    db.add_all([
        StudentLessonProgress(student_id=student_id, lesson_id=lesson.id),
        StudentLessonNote(student_id=student_id, lesson_id=lesson.id, content="must survive rollback"),
        XPLedger(student_id=student_id, source_type="test", source_id=1, delta=1),
    ])
    db.commit()

    from app.routers import admin_students
    original = admin_students.delete_student_owned_data

    def fail_after_cleanup(session, target_id):
        original(session, target_id)
        raise RuntimeError("forced cleanup failure")

    monkeypatch.setattr(admin_students, "delete_student_owned_data", fail_after_cleanup)
    client = TestClient(client.app, raise_server_exceptions=False)
    failed = client.delete(f"/api/admin/students/{student_id}")
    assert failed.status_code == 500
    db.expire_all()
    assert db.query(Student).filter_by(id=student_id).count() == 1
    assert db.query(StudentLessonProgress).filter_by(student_id=student_id).count() == 1
    assert db.query(StudentLessonNote).filter_by(student_id=student_id).count() == 1
    assert db.query(XPLedger).filter_by(student_id=student_id).count() == 1
