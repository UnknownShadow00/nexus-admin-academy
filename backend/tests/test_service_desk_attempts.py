from app.models.service_desk import ServiceDeskAssignment, ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.student import Student
from app.models.xp_ledger import XPLedger
from app.routers import service_desk
from app.services.service_desk_grading import compute_grade
from conftest import auth_headers, make_client, make_student


def setup_assignment(db, student, *, published=True, maximum_attempts=None, stable_key=None, priority="high"):
    scenario = ServiceDeskScenario(stable_key=stable_key or f"scenario-{student.id}-{published}", title="VPN outage", description="desc", category="network", difficulty=2)
    db.add(scenario); db.flush()
    version = ServiceDeskScenarioVersion(scenario_id=scenario.id, version_number=1, definition_json={"steps": [], "priority": priority}, definition_hash=f"hash-{student.id}-{published}-{stable_key or priority}", status="published" if published else "draft")
    db.add(version); db.flush()
    assignment = ServiceDeskAssignment(student_id=student.id, scenario_id=scenario.id, mode="learning", assigned_by="admin", maximum_attempts=maximum_attempts)
    db.add(assignment); db.commit(); db.refresh(assignment)
    return assignment


def start(client, student, assignment):
    return client.post(f"/api/service-desk/assignments/{assignment.id}/attempts", headers=auth_headers(student))


def close(client, student, attempt_id, *, verified=True, payload=None):
    return client.post(f"/api/service-desk/attempts/{attempt_id}/events", headers=auth_headers(student), json={
        "idempotency_key": f"close-{attempt_id}-{verified}", "event_type": "ticket.close", "tool": "ticket",
        "payload": {"verifiedResolved": verified, "resolutionNote": "resolved"} | (payload or {}),
        "resulting_state": {}, "success": True,
    })


def test_service_desk_requires_authentication():
    assert make_client(service_desk.router).get("/api/service-desk/assignments").status_code == 401


def test_assignment_listing_start_resume_and_event_idempotency(db):
    student = make_student(db); assignment = setup_assignment(db, student)
    client = make_client(service_desk.router); headers = auth_headers(student)
    listing = client.get("/api/service-desk/assignments", headers=headers)
    assert listing.status_code == 200 and listing.json()[0]["scenario"]["title"] == "VPN outage"
    first = start(client, student, assignment); assert first.status_code == 201 and first.json()["attempt_number"] == 1
    second = start(client, student, assignment); assert second.status_code == 200 and second.json()["id"] == first.json()["id"]
    event_body = {"idempotency_key": "evt-1", "event_type": "command", "tool": "shell", "payload": {"x": 1}, "resulting_state": {"x": 1}, "success": True}
    event = client.post(f"/api/service-desk/attempts/{first.json()['id']}/events", headers=headers, json=event_body)
    replay = client.post(f"/api/service-desk/attempts/{first.json()['id']}/events", headers=headers, json=event_body)
    assert event.status_code == 201 and replay.status_code == 200 and replay.json()["id"] == event.json()["id"]
    next_event = dict(event_body, idempotency_key="evt-2", resulting_state={"x": 2})
    assert client.post(f"/api/service-desk/attempts/{first.json()['id']}/events", headers=headers, json=next_event).json()["sequence_number"] == 2
    assert db.query(ServiceDeskAttempt).count() == 1


def test_no_published_version_and_attempt_cap(db):
    student = make_student(db); client = make_client(service_desk.router)
    draft_assignment = setup_assignment(db, student, published=False)
    assert start(client, student, draft_assignment).status_code == 409
    capped_student = make_student(db, username="capped")
    capped = setup_assignment(db, capped_student, maximum_attempts=1)
    response = start(client, capped_student, capped); attempt_id = response.json()["id"]
    db.query(ServiceDeskAttempt).filter_by(id=attempt_id).update({"status": "failed"}); db.commit()
    assert start(client, capped_student, capped).status_code == 403


def test_ownership_and_complete_awards_xp_once(db):
    owner = make_student(db); other = make_student(db, username="other")
    assignment = setup_assignment(db, owner); client = make_client(service_desk.router)
    started = start(client, owner, assignment); attempt_id = started.json()["id"]
    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(other)).status_code == 403
    close(client, owner, attempt_id)
    body = {"idempotency_key": "complete-1"}
    before_xp = owner.total_xp
    first = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(owner), json=body)
    second = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(owner), json=body)
    third = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(owner), json=dict(body, idempotency_key="complete-2", overall_score=1))
    db.refresh(owner)
    ledger_rows = db.query(XPLedger).filter_by(
        student_id=owner.id, source_type="service_desk_attempt", source_id=attempt_id,
    ).all()
    assert first.status_code == 201 and second.status_code == 200 and third.status_code == 200
    assert second.json()["id"] == first.json()["id"] == third.json()["id"]
    assert len(ledger_rows) == 1 and ledger_rows[0].delta == 100
    assert owner.total_xp == before_xp + 100


def test_failed_complete_also_awards_the_score_as_xp(db):
    student = make_student(db, username="failed-complete")
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id, verified=False)
    body = {"idempotency_key": "failed-complete"}

    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json=body)

    db.refresh(student)
    ledger_rows = db.query(XPLedger).filter_by(
        student_id=student.id, source_type="service_desk_attempt", source_id=attempt_id,
    ).all()
    assert response.status_code == 201 and response.json()["overall_score"] == 75
    assert len(ledger_rows) == 1 and ledger_rows[0].delta == 75
    assert student.total_xp == 75


def test_full_priority_verified_close_gets_exact_score(db):
    student = make_student(db, username="critical-score"); assignment = setup_assignment(db, student, priority="critical")
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id)
    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json={"idempotency_key": "grade"})
    assert response.status_code == 201 and response.json()["overall_score"] == 100
    assert response.json()["details"]["points_possible"] == 160


def test_two_hints_use_one_free_hint_and_normalize_score(db):
    student = make_student(db, username="hint-score"); assignment = setup_assignment(db, student, priority="critical")
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    for key in ("hint-1", "hint-2"):
        assert client.post(f"/api/service-desk/attempts/{attempt_id}/hints", headers=auth_headers(student), json={"idempotency_key": key, "tool": "ticket", "payload": {}}).status_code == 201
    close(client, student, attempt_id)
    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json={"idempotency_key": "grade"})
    assert response.json()["details"]["penalty_points"] == 5 and response.json()["overall_score"] == 97


def test_unresolved_close_applies_penalty_and_fails(db):
    student = make_student(db, username="unresolved"); assignment = setup_assignment(db, student, priority="critical")
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id, verified=False)
    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json={"idempotency_key": "grade"})
    assert response.json()["passed"] is False and response.json()["details"]["penalty_points"] == 40 and response.json()["overall_score"] == 75


def test_inc2401_directory_replay_reduces_then_restores_objective_points(db):
    student = make_student(db, username="avery"); assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id)
    attempt = db.query(ServiceDeskAttempt).filter_by(id=attempt_id).one()
    first = compute_grade(db, attempt)
    assert first["details"]["directory_objective_satisfied"] is False and first["overall_score"] == 50

    event = {"idempotency_key": "unlock", "event_type": "directory.unlock_account", "tool": "directory", "payload": {"directoryUserId": "directory-user-avery-brooks"}, "resulting_state": {}, "success": True}
    assert client.post(f"/api/service-desk/attempts/{attempt_id}/events", headers=auth_headers(student), json=event).status_code == 201
    second = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json={"idempotency_key": "grade"}).json()
    assert second["details"]["directory_objective_satisfied"] is True and second["overall_score"] == 100


def test_wrong_directory_user_does_not_satisfy_inc2401_objective(db):
    student = make_student(db, username="wrong-directory"); assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    event = {"idempotency_key": "wrong-unlock", "event_type": "directory.unlock_account", "tool": "directory", "payload": {"directoryUserId": "directory-user-sloane-rivera"}, "resulting_state": {}, "success": True}
    client.post(f"/api/service-desk/attempts/{attempt_id}/events", headers=auth_headers(student), json=event); close(client, student, attempt_id)
    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json={"idempotency_key": "grade"})
    assert response.json()["details"]["directory_objective_satisfied"] is False


def test_non_ticket_tool_events_do_not_overwrite_resumable_ticket_state(db):
    student = make_student(db, username="state-shape"); assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router); headers = auth_headers(student)
    attempt_id = start(client, student, assignment).json()["id"]

    ticket_event = {"idempotency_key": "ticket-1", "event_type": "ticket.assign", "tool": "ticket",
                    "payload": {"ticketId": "INC2401"}, "resulting_state": {"notes": ["assigned"]}, "success": True}
    assert client.post(f"/api/service-desk/attempts/{attempt_id}/events", headers=headers, json=ticket_event).status_code == 201
    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=headers).json()["current_state"] == {"notes": ["assigned"]}

    # A directory-tool event's resulting_state describes that directory user's
    # overlay, not the ticket - it must not clobber the ticket snapshot a
    # resumed session hydrates from (see service_desk.py's _record_event).
    directory_event = {"idempotency_key": "unlock", "event_type": "directory.unlock_account", "tool": "directory",
                        "payload": {"directoryUserId": "directory-user-avery-brooks"},
                        "resulting_state": {"locked": False, "mfaEnrolled": True}, "success": True}
    assert client.post(f"/api/service-desk/attempts/{attempt_id}/events", headers=headers, json=directory_event).status_code == 201
    resumed = client.get(f"/api/service-desk/attempts/{attempt_id}", headers=headers).json()
    assert resumed["current_state"] == {"notes": ["assigned"]}
    assert resumed["state_version"] == 2


def test_client_grade_fields_are_ignored_and_repeat_is_identical(db):
    student = make_student(db, username="untrusted-fields"); assignment = setup_assignment(db, student, priority="high")
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id)
    body = {"idempotency_key": "grade", "technical_complete": False, "critical_failure": True, "overall_score": 1, "passed": False, "feedback_summary": "fake", "details": {"fake": True}, "rubric_version": "fake"}
    first = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json=body)
    second = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json=body)
    assert first.status_code == 201 and second.status_code == 200 and second.json() == first.json()
    assert first.json()["overall_score"] == 100 and first.json()["passed"] is True and first.json()["rubric_version"] == "sim-engine-v1"


def test_complete_before_close_returns_409(db):
    student = make_student(db, username="not-closed"); assignment = setup_assignment(db, student)
    client = make_client(service_desk.router); attempt_id = start(client, student, assignment).json()["id"]
    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json={"idempotency_key": "grade"})
    assert response.status_code == 409 and response.json()["detail"] == "Attempt has not been closed yet"

# NOTE on true concurrency testing: a real multi-threaded race test was
# attempted here and removed. This fixture's SQLite engine uses StaticPool,
# which hands every SQLAlchemy session the literal same underlying DBAPI
# connection object (verified directly: `e.connect().connection.dbapi_connection
# is e.connect().connection.dbapi_connection` is True) — concurrent commits
# against it corrupt cursor state ("no more rows available") regardless of
# application code correctness, and even a single-threaded manually-interleaved
# two-session test would not model independent transactions, since there is
# only one real transaction underneath both sessions. Exercising the actual
# IntegrityError race path in complete_attempt would require a real
# file-backed SQLite DB (or Postgres) with a proper connection pool in the
# test fixture, which is a test-infrastructure change out of scope here.
# The sequential idempotency tests above (same idempotency_key replayed,
# and a second /complete call with a different idempotency_key after the
# attempt is already terminal) cover every scenario this phase's spec
# actually lists as required (double-click, refresh, retry, two tabs,
# resuming a completed attempt) — those are all sequential-request patterns
# from a single client's perspective, not sub-millisecond simultaneous
# writes. The transactional correctness itself (award_xp called before
# commit so a failed commit rolls back both the grade and the XP mutation
# together, IntegrityError caught and re-fetched rather than raised) was
# verified by reading service_desk.py directly, not just by these tests.
