import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.models.evidence import EvidenceArtifact
from app.models.login_streak import LoginStreak
from app.models.mastery import StudentDomainMastery
from app.models.progression import MethodologyFramework, Role, StudentMethodologyProgress
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
from app.models.weekly_lead import WeeklyDomainLead
from app.routers.admin_students import router as admin_students_router
from app.services.admin_auth import verify_admin
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
    db.add_all([role, *frameworks])
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
    artifact = db.query(EvidenceArtifact).filter_by(storage_key="disposable.png").one()
    assert artifact.student_id is None
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
