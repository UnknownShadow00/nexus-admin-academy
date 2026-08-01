from app.models.service_desk import ServiceDeskAssignment, ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.student import Student
from app.models.xp_ledger import XPLedger
from app.routers import service_desk
from conftest import auth_headers, make_client, make_student


def setup_assignment(db, student, *, published=True, maximum_attempts=None):
    scenario = ServiceDeskScenario(stable_key=f"scenario-{student.id}-{published}", title="VPN outage", description="desc", category="network", difficulty=2)
    db.add(scenario); db.flush()
    version = ServiceDeskScenarioVersion(scenario_id=scenario.id, version_number=1, definition_json={"steps": []}, definition_hash=f"hash-{student.id}-{published}", status="published" if published else "draft")
    db.add(version); db.flush()
    assignment = ServiceDeskAssignment(student_id=student.id, scenario_id=scenario.id, mode="learning", assigned_by="admin", maximum_attempts=maximum_attempts)
    db.add(assignment); db.commit(); db.refresh(assignment)
    return assignment


def start(client, student, assignment):
    return client.post(f"/api/service-desk/assignments/{assignment.id}/attempts", headers=auth_headers(student))


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
    body = {"idempotency_key": "complete-1", "technical_complete": True, "critical_failure": False, "overall_score": 90, "passed": True, "feedback_summary": "Good", "rubric_version": "v1"}
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
    assert len(ledger_rows) == 1 and ledger_rows[0].delta == body["overall_score"]
    assert owner.total_xp == before_xp + body["overall_score"]


def test_failed_complete_also_awards_the_score_as_xp(db):
    student = make_student(db, username="failed-complete")
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    body = {"idempotency_key": "failed-complete", "technical_complete": False, "critical_failure": True,
            "overall_score": 17, "passed": False, "feedback_summary": "Needs work", "rubric_version": "v1"}

    response = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student), json=body)

    db.refresh(student)
    ledger_rows = db.query(XPLedger).filter_by(
        student_id=student.id, source_type="service_desk_attempt", source_id=attempt_id,
    ).all()
    assert response.status_code == 201
    assert len(ledger_rows) == 1 and ledger_rows[0].delta == 17
    assert student.total_xp == 17

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
