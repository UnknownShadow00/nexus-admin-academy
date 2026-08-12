import pytest

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.xp_ledger import XPLedger
from app.routers import service_desk
from app.services.service_desk_grading import compute_grade
from app.services.service_desk_objectives import SCENARIO_OBJECTIVES
from app.services.service_desk_objectives import PROCESS_CATALOG_VERSION
from conftest import auth_headers, make_client, make_student


def _process_ticket_id(stable_key: str) -> str:
    definition = SCENARIO_OBJECTIVES[stable_key]
    return next(
        rule.payload["ticketId"]
        for category in definition.categories
        for objective in category.objectives
        for rule in objective.any_of
        if "ticketId" in rule.payload
    )


def setup_assignment(
    db,
    student,
    *,
    published=True,
    maximum_attempts=None,
    stable_key=None,
    priority="high",
    mode="simulation",
    process_profile=False,
):
    key = stable_key or f"scenario-{student.id}-{published}"
    scenario = db.query(ServiceDeskScenario).filter_by(stable_key=key).first()
    if scenario is None:
        scenario = ServiceDeskScenario(
            stable_key=key, title="VPN outage", description="desc",
            category="network", difficulty=2,
        )
        db.add(scenario)
        db.flush()
        version = ServiceDeskScenarioVersion(
            scenario_id=scenario.id,
            version_number=1,
            definition_json={
                "steps": [], "priority": priority,
                **(
                    {
                        "id": _process_ticket_id(key),
                        "objective_catalog_version": PROCESS_CATALOG_VERSION,
                    }
                    if process_profile
                    else {}
                ),
            },
            definition_hash=f"hash-{student.id}-{published}-{stable_key or priority}",
            status="published" if published else "draft",
        )
        db.add(version)
        db.flush()
    assignment = ServiceDeskAssignment(
        student_id=student.id,
        scenario_id=scenario.id,
        mode=mode,
        assigned_by="admin",
        maximum_attempts=maximum_attempts,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def start(client, student, assignment):
    return client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts",
        headers=auth_headers(student),
    )


def close(client, student, attempt_id, *, verified=True, payload=None):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/events",
        headers=auth_headers(student),
        json={
            "idempotency_key": f"close-{attempt_id}-{verified}",
            "event_type": "ticket.close",
            "tool": "ticket",
            "payload": {"verifiedResolved": verified, "resolutionNote": "resolved"}
            | (payload or {}),
            "resulting_state": {},
            "success": True,
        },
    )


def unlock_avery(client, student, attempt_id, *, key="unlock-avery", success=True):
    assign = client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={"idempotency_key": f"assign-{key}", "event_type": "ticket.assign", "tool": "ticket",
              "payload": {"ticketId": "INC2401"}},
    )
    assert assign.status_code in {200, 201}
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=auth_headers(student),
        json={
            "idempotency_key": key,
            "event_type": "directory.unlock_account",
            "tool": "directory",
            "payload": {"directoryUserId": "directory-user-avery-brooks"},
        },
    )


def _tool_for(rule):
    if rule.event_type.startswith("directory."):
        return "directory"
    if rule.event_type.startswith("asset."):
        return "asset"
    if rule.event_type.startswith("shipping."):
        return "shipping"
    if rule.event_type.startswith("ticket."):
        return "ticket"
    return "remote_desktop"


def complete_process_workflow(client, student, attempt_id, stable_key):
    """Submit one server-authorized valid route through each process category."""
    headers = auth_headers(student)
    ticket_id = _process_ticket_id(stable_key)
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    assert client.post(path, headers=headers, json={
        "idempotency_key": "assign", "event_type": "ticket.assign", "tool": "ticket",
        "payload": {"ticketId": ticket_id},
    }).status_code == 201
    definition = SCENARIO_OBJECTIVES[stable_key]
    for category_index, category in enumerate(definition.categories):
        for objective_index, objective in enumerate(category.objectives):
            rule = objective.any_of[0]
            payload = dict(rule.payload)
            if rule.event_type == "ticket.add_note" or rule.event_type == "remote_desktop.add_internal_note":
                payload["body"] = "Documented the symptom, evidence, repair, and verification."
            response = client.post(path, headers=headers, json={
                "idempotency_key": f"{category.name}-{category_index}-{objective_index}",
                "event_type": rule.event_type,
                "tool": _tool_for(rule),
                "payload": payload,
            })
            assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "stable_key",
    [f"inc{number}" for number in range(2501, 2511)],
)
def test_converted_legacy_cases_require_server_authoritative_process_evidence(
    db, stable_key
):
    """Each harvested case has a complete, trusted process path—not a text answer."""
    student = make_student(db, username=f"{stable_key}-student")
    assignment = setup_assignment(
        db, student, stable_key=stable_key, process_profile=True
    )
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    complete_process_workflow(client, student, attempt_id, stable_key)
    close(client, student, attempt_id)
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student), json={"idempotency_key": f"complete-{stable_key}"},
    )
    assert grade.status_code == 201
    assert grade.json()["passed"] is True
    assert grade.json()["overall_score"] == 100


@pytest.mark.parametrize(
    ("stable_key", "event_type", "payload"),
    [
        (
            "locked-user-account",
            "directory.unlock_account",
            {"directoryUserId": "directory-user-taylor-morgan"},
        ),
        (
            "password-reset",
            "directory.reset_password",
            {
                "directoryUserId": "directory-user-jordan-lee",
                "requireChangeAtNextSignIn": True,
            },
        ),
        (
            "mfa-reset",
            "directory.reset_mfa",
            {"directoryUserId": "directory-user-camille-reyes"},
        ),
    ],
)
def test_foundational_account_fix_is_rejected_before_investigation(
    db, stable_key, event_type, payload
):
    student = make_student(db, username=f"premature-{stable_key}")
    assignment = setup_assignment(
        db, student, stable_key=stable_key, process_profile=True
    )
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    headers = auth_headers(student)
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    assert client.post(
        path,
        headers=headers,
        json={
            "idempotency_key": "assign",
            "event_type": "ticket.assign",
            "tool": "ticket",
            "payload": {"ticketId": _process_ticket_id(stable_key)},
        },
    ).status_code == 201

    response = client.post(
        path,
        headers=headers,
        json={
            "idempotency_key": "guessed-fix",
            "event_type": event_type,
            "tool": "directory",
            "payload": payload,
        },
    )

    assert response.status_code == 409
    assert "server-authoritative attempt state" in response.json()["detail"]


@pytest.mark.parametrize(
    "stable_key",
    ["locked-user-account", "password-reset", "mfa-reset"],
)
def test_foundational_account_lifecycle_passes_and_replays(db, stable_key):
    student = make_student(db, username=f"lifecycle-{stable_key}")
    assignment = setup_assignment(
        db, student, stable_key=stable_key, process_profile=True
    )
    client = make_client(service_desk.router)
    first_attempt_id = start(client, student, assignment).json()["id"]
    complete_process_workflow(client, student, first_attempt_id, stable_key)
    close(client, student, first_attempt_id)
    grade = client.post(
        f"/api/service-desk/attempts/{first_attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "complete-foundational"},
    )
    replay = start(client, student, assignment)

    assert grade.status_code == 201
    assert grade.json()["passed"] is True
    assert grade.json()["overall_score"] == 100
    assert replay.status_code == 201
    assert replay.json()["attempt_number"] == 2


def test_converted_legacy_case_repair_does_not_replace_investigation_or_diagnosis(db):
    student = make_student(db, username="guessing-lockout")
    assignment = setup_assignment(db, student, stable_key="inc2507", process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    headers = auth_headers(student)
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    assert client.post(path, headers=headers, json={
        "idempotency_key": "assign", "event_type": "ticket.assign", "tool": "ticket",
        "payload": {"ticketId": "INC2507"},
    }).status_code == 201
    for index, step in enumerate(("scenario.apply-safe-remediation", "scenario.verify-original-symptom")):
        assert client.post(path, headers=headers, json={
            "idempotency_key": f"guess-{index}",
            "event_type": "remote_desktop.perform_scenario_step", "tool": "remote_desktop",
            "payload": {"ticketId": "INC2507", "assetTag": "NX-2507", "stepId": step},
        }).status_code == 201
    close(client, student, attempt_id)
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete", headers=headers,
        json={"idempotency_key": "complete-guess"},
    )
    assert grade.status_code == 201
    assert grade.json()["passed"] is False
    assert grade.json()["overall_score"] < 50


def test_service_desk_requires_authentication():
    assert (
        make_client(service_desk.router)
        .get("/api/service-desk/assignments")
        .status_code
        == 401
    )


def test_assignment_listing_start_resume_and_event_idempotency(db):
    student = make_student(db)
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    headers = auth_headers(student)
    listing = client.get("/api/service-desk/assignments", headers=headers)
    assert (
        listing.status_code == 200
        and listing.json()[0]["scenario"]["title"] == "VPN outage"
    )
    assert listing.json()[0]["latest_published_version"]["definition_json"]["priority"] == "high"
    assert "objectives" not in listing.json()[0]["latest_published_version"]["definition_json"]
    assert "explanation" not in listing.json()[0]["latest_published_version"]["definition_json"]
    first = start(client, student, assignment)
    assert first.status_code == 201 and first.json()["attempt_number"] == 1
    second = start(client, student, assignment)
    assert second.status_code == 200 and second.json()["id"] == first.json()["id"]
    event_body = {
        "idempotency_key": "evt-1",
        "event_type": "ticket.assign",
        "tool": "ticket",
        "payload": {"ticketId": "INC2401"},
        "resulting_state": {"x": 1},
        "success": True,
    }
    event = client.post(
        f"/api/service-desk/attempts/{first.json()['id']}/events",
        headers=headers,
        json=event_body,
    )
    replay = client.post(
        f"/api/service-desk/attempts/{first.json()['id']}/events",
        headers=headers,
        json=event_body,
    )
    assert (
        event.status_code == 201
        and replay.status_code == 200
        and replay.json()["id"] == event.json()["id"]
    )
    next_event = dict(event_body, idempotency_key="evt-2", resulting_state={"x": 2})
    assert (
        client.post(
            f"/api/service-desk/attempts/{first.json()['id']}/events",
            headers=headers,
            json=next_event,
        ).json()["sequence_number"]
        == 2
    )
    assert db.query(ServiceDeskAttempt).count() == 1


def test_builder_definition_uses_versioned_server_objectives(db):
    student = make_student(db, username="builder-runtime")
    assignment = setup_assignment(db, student, stable_key="printer-queue-stops", priority="medium")
    version = db.query(ServiceDeskScenarioVersion).filter_by(scenario_id=assignment.scenario_id).one()
    definition = {
        "priority": "medium",
        "objectives": [{
            "required": True,
            "predicateType": "action_event_occurred",
            "predicateParams": {
                "actionType": "ticket.add_note",
                "payloadMatch": {"ticketId": "PRINTER-QUEUE-STOPS"},
            },
        }],
    }
    # The test fixture uses a placeholder hash and remains published; updating
    # it here models a definition created before the immutable publish step.
    db.execute(
        ServiceDeskScenarioVersion.__table__.update().where(
            ServiceDeskScenarioVersion.id == version.id
        ).values(definition_json=definition)
    )
    db.commit()
    client = make_client(service_desk.router)
    headers = auth_headers(student)
    attempt_id = start(client, student, assignment).json()["id"]
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/actions",
        headers=headers,
        json={
            "idempotency_key": "diagnosis-note",
            "event_type": "ticket.add_note",
            "tool": "ticket",
            "payload": {
                "ticketId": "PRINTER-QUEUE-STOPS",
                "body": "Confirmed the local queue failed and verified printing after repair.",
            },
        },
    )
    assert response.status_code == 201
    close(client, student, attempt_id)
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=headers,
        json={"idempotency_key": "complete-builder"},
    )
    assert grade.status_code == 201 and grade.json()["passed"] is True


def test_no_published_version_and_attempt_cap(db):
    student = make_student(db)
    client = make_client(service_desk.router)
    draft_assignment = setup_assignment(db, student, published=False)
    assert start(client, student, draft_assignment).status_code == 409
    capped_student = make_student(db, username="capped")
    capped = setup_assignment(db, capped_student, maximum_attempts=1)
    response = start(client, capped_student, capped)
    attempt_id = response.json()["id"]
    db.query(ServiceDeskAttempt).filter_by(id=attempt_id).update({"status": "failed"})
    db.commit()
    assert start(client, capped_student, capped).status_code == 403


def test_publishing_vnext_does_not_orphan_an_in_progress_old_version_attempt(db):
    student = make_student(db, username="version-resume")
    assignment = setup_assignment(db, student, stable_key="inc2401")
    client = make_client(service_desk.router)
    first = start(client, student, assignment).json()
    first_version_id = first["scenario_version_id"]
    scenario = db.get(ServiceDeskScenario, assignment.scenario_id)
    v2 = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=2,
        definition_json={"priority": "high", "revision": 2},
        definition_hash="published-v2-hash",
        status="published",
    )
    db.add(v2)
    db.commit()
    db.refresh(v2)

    listing = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()[0]
    assert listing["latest_published_version"]["id"] == v2.id
    assert listing["most_recent_attempt"]["id"] == first["id"]
    resumed = start(client, student, assignment)
    assert resumed.status_code == 200
    assert resumed.json()["id"] == first["id"]
    assert resumed.json()["scenario_version_id"] == first_version_id

    db.query(ServiceDeskAttempt).filter_by(id=first["id"]).update({"status": "failed"})
    db.commit()
    second = start(client, student, assignment)
    assert second.status_code == 201
    assert second.json()["scenario_version_id"] == v2.id


def test_ownership_and_verified_complete_awards_xp_once(db):
    owner = make_student(db)
    other = make_student(db, username="other")
    assignment = setup_assignment(db, owner, stable_key="inc2401")
    client = make_client(service_desk.router)
    started = start(client, owner, assignment)
    attempt_id = started.json()["id"]
    assert (
        client.get(
            f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(other)
        ).status_code
        == 403
    )
    unlock_avery(client, owner, attempt_id)
    close(client, owner, attempt_id)
    body = {"idempotency_key": "complete-1"}
    before_xp = owner.total_xp
    first = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(owner),
        json=body,
    )
    second = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(owner),
        json=body,
    )
    third = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(owner),
        json=dict(body, idempotency_key="complete-2", overall_score=1),
    )
    db.refresh(owner)
    ledger_rows = (
        db.query(XPLedger)
        .filter_by(
            student_id=owner.id,
            source_type="service_desk_attempt",
            source_id=attempt_id,
        )
        .all()
    )
    assert (
        first.status_code == 201
        and second.status_code == 200
        and third.status_code == 200
    )
    assert second.json()["id"] == first.json()["id"] == third.json()["id"]
    assert len(ledger_rows) == 1 and ledger_rows[0].delta == 100
    assert owner.total_xp == before_xp + 100


def test_mentor_review_access_cannot_mutate_student_attempt(db):
    owner = make_student(db, username="attempt-owner")
    mentor = make_student(db, username="read-only-mentor")
    mentor.is_mentor = True
    db.commit()
    assignment = setup_assignment(db, owner, stable_key="inc2401")
    client = make_client(service_desk.router)
    attempt_id = start(client, owner, assignment).json()["id"]
    headers = auth_headers(mentor)

    assert client.get(f"/api/service-desk/attempts/{attempt_id}", headers=headers).status_code == 200
    writes = [
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/events",
            headers=headers,
            json={"idempotency_key": "mentor-event", "event_type": "ticket.close", "tool": "ticket",
                  "payload": {"verifiedResolved": True}, "resulting_state": {}, "success": True},
        ),
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/snapshot",
            headers=headers,
            json={"idempotency_key": "mentor-snapshot", "snapshot": {
                "schema_version": 1, "nexus_service_desk_attempt": {}}},
        ),
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/actions",
            headers=headers,
            json={"idempotency_key": "mentor-action", "event_type": "ticket.assign", "tool": "ticket",
                  "payload": {"ticketId": "INC2401"}, "resulting_state": {}},
        ),
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/hints",
            headers=headers,
            json={"idempotency_key": "mentor-hint", "tool": "ticket", "payload": {}},
        ),
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/complete",
            headers=headers,
            json={"idempotency_key": "mentor-complete"},
        ),
    ]

    assert [response.status_code for response in writes] == [403, 403, 403, 403, 403]
    assert db.query(ServiceDeskAttemptEvent).filter_by(attempt_id=attempt_id).count() == 0
    assert db.query(XPLedger).filter_by(student_id=owner.id).count() == 0


def test_failed_complete_awards_zero_xp(db):
    student = make_student(db, username="failed-complete")
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id, verified=False)
    body = {"idempotency_key": "failed-complete"}

    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json=body,
    )

    db.refresh(student)
    ledger_rows = (
        db.query(XPLedger)
        .filter_by(
            student_id=student.id,
            source_type="service_desk_attempt",
            source_id=attempt_id,
        )
        .all()
    )
    assert response.status_code == 201 and response.json()["overall_score"] == 0
    assert ledger_rows == [] and student.total_xp == 0


def test_full_priority_verified_close_gets_exact_score(db):
    student = make_student(db, username="critical-score")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="critical")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    unlock_avery(client, student, attempt_id)
    close(client, student, attempt_id)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    assert response.status_code == 201 and response.json()["overall_score"] == 100
    assert response.json()["details"]["points_possible"] == 160


def test_two_hints_use_one_free_hint_and_normalize_score(db):
    student = make_student(db, username="hint-score")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="critical")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    for key in ("hint-1", "hint-2"):
        assert (
            client.post(
                f"/api/service-desk/attempts/{attempt_id}/hints",
                headers=auth_headers(student),
                json={"idempotency_key": key, "tool": "ticket", "payload": {}},
            ).status_code
            == 201
        )
    unlock_avery(client, student, attempt_id)
    close(client, student, attempt_id)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    assert (
        response.json()["details"]["penalty_points"] == 5
        and response.json()["overall_score"] == 97
    )


def test_unresolved_close_applies_penalty_and_fails(db):
    student = make_student(db, username="unresolved")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="critical")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id, verified=False)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    assert (
        response.json()["passed"] is False
        and response.json()["details"]["penalty_points"] == 40
        and response.json()["overall_score"] == 0
    )


def test_learning_mode_waives_hint_penalty(db):
    student = make_student(db, username="learning-hint-score")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="critical", mode="learning")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    for key in ("hint-1", "hint-2", "hint-3"):
        assert (
            client.post(
                f"/api/service-desk/attempts/{attempt_id}/hints",
                headers=auth_headers(student),
                json={"idempotency_key": key, "tool": "ticket", "payload": {}},
            ).status_code
            == 201
        )
    unlock_avery(client, student, attempt_id)
    close(client, student, attempt_id)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    body = response.json()
    assert body["details"]["penalty_points"] == 0 and body["overall_score"] == 100
    assert (
        body["details"]["hints_used"] == 3
        and body["details"]["is_learning_mode"] is True
    )
    assert "Learning Mode" in body["feedback_summary"]


def test_learning_mode_waives_unresolved_close_penalty(db):
    student = make_student(db, username="learning-unresolved")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="critical", mode="learning")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id, verified=False)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    body = response.json()
    # Learning Mode waives the score penalty for an unresolved close, but
    # does not pretend the ticket was actually resolved.
    assert (
        body["passed"] is False
        and body["details"]["penalty_points"] == 0
        and body["overall_score"] == 0
    )
    assert "Learning Mode" in body["feedback_summary"]


def test_inc2401_directory_evidence_is_required_then_passes(db):
    student = make_student(db, username="avery")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    close(client, student, attempt_id)
    attempt = db.query(ServiceDeskAttempt).filter_by(id=attempt_id).one()
    first = compute_grade(db, attempt)
    assert (
        first["passed"] is False
        and first["overall_score"] == 0
    )

    assert unlock_avery(client, student, attempt_id, key="unlock").status_code == 201
    second = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    ).json()
    assert (
        second["details"]["objective_checks"]["approved_corrective_action"] is True
        and second["overall_score"] == 100
    )


def test_wrong_directory_user_does_not_satisfy_inc2401_objective(db):
    student = make_student(db, username="wrong-directory")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    event = {
        "idempotency_key": "wrong-unlock",
        "event_type": "directory.unlock_account",
        "tool": "directory",
        "payload": {"directoryUserId": "directory-user-sloane-rivera"},
        "resulting_state": {},
        "success": True,
    }
    client.post(
        f"/api/service-desk/attempts/{attempt_id}/events",
        headers=auth_headers(student),
        json=event,
    )
    close(client, student, attempt_id)
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    assert response.json()["passed"] is False


def test_headset_ticket_requires_asset_replacement_shipping_and_notes(db):
    student = make_student(db, username="headset-workflow")
    assignment = setup_assignment(db, student, stable_key="inc2404", priority="medium")
    client = make_client(service_desk.router)
    headers = auth_headers(student)
    attempt_id = start(client, student, assignment).json()["id"]
    path = f"/api/service-desk/attempts/{attempt_id}/actions"

    assert client.post(path, headers=headers, json={
        "idempotency_key": "asset-damaged",
        "event_type": "asset.change_status",
        "tool": "asset",
        "payload": {"assetTag": "NX-9052", "status": "damaged"},
    }).status_code == 201
    assert client.post(path, headers=headers, json={
        "idempotency_key": "ship-headset",
        "event_type": "shipping.create",
        "tool": "shipping",
        "payload": {
            "recipientDirectoryUserId": "directory-user-elliot-ward",
            "recipientName": "Elliot Ward",
            "street": "120 Cedar Street",
            "city": "Seattle",
            "state": "WA",
            "postalCode": "98101",
            "senderDepartment": "IT Department",
            "equipment": [{"name": "Headset", "quantity": 1}],
            "computerAssetTag": None,
            "speed": "express",
            "includeReturnLabel": True,
        },
    }).status_code == 201
    assert client.post(path, headers=headers, json={
        "idempotency_key": "short-note",
        "event_type": "ticket.add_note",
        "tool": "ticket",
        "payload": {"ticketId": "INC2404", "body": "Replaced."},
    }).status_code == 422
    assert client.post(path, headers=headers, json={
        "idempotency_key": "complete-note",
        "event_type": "ticket.add_note",
        "tool": "ticket",
        "payload": {
            "ticketId": "INC2404",
            "body": "Confirmed static followed the headset; replacement shipped and user will test it.",
        },
    }).status_code == 201
    close(client, student, attempt_id)
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=headers,
        json={"idempotency_key": "grade-headset"},
    )
    assert grade.status_code == 201
    assert grade.json()["passed"] is True


def test_non_ticket_tool_events_do_not_overwrite_resumable_ticket_state(db):
    student = make_student(db, username="state-shape")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router)
    headers = auth_headers(student)
    attempt_id = start(client, student, assignment).json()["id"]

    ticket_event = {
        "idempotency_key": "ticket-1",
        "event_type": "ticket.assign",
        "tool": "ticket",
        "payload": {"ticketId": "INC2401"},
        "resulting_state": {"notes": ["assigned"]},
        "success": True,
    }
    assert (
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/events",
            headers=headers,
            json=ticket_event,
        ).status_code
        == 201
    )
    assert client.get(
        f"/api/service-desk/attempts/{attempt_id}", headers=headers
    ).json()["current_state"] == {"notes": ["assigned"]}

    # A directory-tool event's resulting_state describes that directory user's
    # overlay, not the ticket - it must not clobber the ticket snapshot a
    # resumed session hydrates from (see service_desk.py's _record_event).
    directory_event = {
        "idempotency_key": "unlock",
        "event_type": "directory.unlock_account",
        "tool": "directory",
        "payload": {"directoryUserId": "directory-user-avery-brooks"},
        "resulting_state": {"locked": False, "mfaEnrolled": True},
        "success": True,
    }
    assert (
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/events",
            headers=headers,
            json=directory_event,
        ).status_code
        == 201
    )
    resumed = client.get(
        f"/api/service-desk/attempts/{attempt_id}", headers=headers
    ).json()
    assert resumed["current_state"] == {"notes": ["assigned"]}
    assert resumed["state_version"] == 2


def test_client_grade_fields_are_ignored_and_repeat_is_identical(db):
    student = make_student(db, username="untrusted-fields")
    assignment = setup_assignment(db, student, stable_key="inc2401", priority="high")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    unlock_avery(client, student, attempt_id)
    close(client, student, attempt_id)
    body = {
        "idempotency_key": "grade",
        "technical_complete": False,
        "critical_failure": True,
        "overall_score": 1,
        "passed": False,
        "feedback_summary": "fake",
        "details": {"fake": True},
        "rubric_version": "fake",
    }
    first = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json=body,
    )
    second = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json=body,
    )
    assert (
        first.status_code == 201
        and second.status_code == 200
        and second.json() == first.json()
    )
    assert (
        first.json()["overall_score"] == 100
        and first.json()["passed"] is True
        and first.json()["rubric_version"] == "server-process-v3"
    )


def test_versioned_full_snapshot_restores_all_tool_state(db):
    student = make_student(db, username="snapshot-resume")
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    snapshot = {
        "schema_version": 1,
        "nexus_service_desk_attempt": {
            "directoryOverlays": {"directory-user-avery-brooks": {"locked": False}},
            "remoteDesktopOverlays": {"NX-2047": {"terminal": ["ipconfig"]}},
            "assetOverlays": {"NX-2047": {"status": "active"}},
            "deploymentRuns": {"run-1": {"hostname": "NX-2047"}},
            "ticketOverlays": {"INC2401": {"notes": ["restored"]}},
        },
    }
    event = {
        "idempotency_key": "snapshot-1",
        "event_type": "directory.unlock_account",
        "tool": "directory",
        "payload": {"directoryUserId": "directory-user-avery-brooks"},
        "resulting_state": snapshot,
        "success": True,
    }
    assert (
        client.post(
            f"/api/service-desk/attempts/{attempt_id}/events",
            headers=auth_headers(student),
            json=event,
        ).status_code
        == 201
    )
    resumed = client.get(
        f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(student)
    ).json()
    assert resumed["current_state"] == snapshot


def test_snapshot_endpoint_persists_untrusted_resume_state_idempotently(db):
    student = make_student(db, username="snapshot-only")
    assignment = setup_assignment(db, student, stable_key="inc2401")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    snapshot = {
        "schema_version": 1,
        "nexus_service_desk_attempt": {
            "chatThreads": {"avery": {"messages": [{"body": "hello"}]}},
            "assetOverlays": {"NX-4831": {"status": "retired"}},
            "pcShelfOverlays": {"SD9099": {"present": False}},
            "serverRoomOverlays": {"dc01": {"status": "online"}},
            "deploymentRuns": {"run-1": {"hostname": "SD9999"}},
            "shipments": {"shipment-1": {"recipientName": "Avery Brooks"}},
        },
    }
    body = {"idempotency_key": "resume-1", "snapshot": snapshot}
    first = client.post(
        f"/api/service-desk/attempts/{attempt_id}/snapshot",
        headers=auth_headers(student), json=body,
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/service-desk/attempts/{attempt_id}/snapshot",
        headers=auth_headers(student), json=body,
    )
    assert second.status_code == 200
    resumed = client.get(
        f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(student)
    ).json()
    assert resumed["current_state"] == snapshot
    assert resumed["state_version"] == 1
    # Snapshot-only writes are auditable but can never become trusted evidence.
    event = db.query(ServiceDeskAttemptEvent).filter_by(
        attempt_id=attempt_id, idempotency_key="resume-1"
    ).one()
    assert event.trusted is False
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student), json={"idempotency_key": "snapshot-grade"},
    )
    assert grade.status_code == 409


def test_snapshot_endpoint_rejects_invalid_or_completed_attempts(db):
    student = make_student(db, username="invalid-snapshot")
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    invalid = client.post(
        f"/api/service-desk/attempts/{attempt_id}/snapshot",
        headers=auth_headers(student),
        json={"idempotency_key": "bad", "snapshot": {"schema_version": 2}},
    )
    assert invalid.status_code == 422


def test_complete_before_close_returns_409(db):
    student = make_student(db, username="not-closed")
    assignment = setup_assignment(db, student)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    response = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": "grade"},
    )
    assert (
        response.status_code == 409
        and response.json()["detail"] == "Attempt has not been closed yet"
    )


@pytest.mark.parametrize("stable_key", [f"inc240{number}" for number in range(1, 9)])
def test_direct_api_forged_close_never_passes_or_awards_xp(db, stable_key):
    """Regression for the P0: a close request is never completion evidence."""
    student = make_student(db, username=f"forged-{stable_key}")
    assignment = setup_assignment(db, student, stable_key=stable_key)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]

    # This is the actual malicious API shape: no simulation work beforehand.
    response = close(client, student, attempt_id, verified=True)
    assert response.status_code == 201
    grade = client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student), json={"idempotency_key": "forge-grade"},
    )
    db.refresh(student)
    assert grade.status_code == 201
    assert grade.json()["passed"] is False
    assert grade.json()["technical_complete"] is False
    assert student.total_xp == 0


def test_forged_snapshot_unknown_event_and_failed_evidence_do_not_complete(db):
    student = make_student(db, username="forged-evidence")
    assignment = setup_assignment(db, student, stable_key="inc2401")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    headers = auth_headers(student)
    unknown = client.post(
        f"/api/service-desk/attempts/{attempt_id}/events", headers=headers,
        json={"idempotency_key": "unknown", "event_type": "totally.arbitrary", "tool": "ticket",
              "payload": {}, "success": True, "resulting_state": {"solved": True}},
    )
    assert unknown.status_code == 422
    forged_events = [
        ("wrong-target", "directory.unlock_account", {"directoryUserId": "directory-user-sloane-rivera"}, True),
        ("failed", "directory.unlock_account", {"directoryUserId": "directory-user-avery-brooks"}, False),
    ]
    for key, event_type, payload, success in forged_events:
        assert client.post(
            f"/api/service-desk/attempts/{attempt_id}/events", headers=headers,
                json={"idempotency_key": key, "event_type": event_type, "tool": "directory",
                  "payload": payload, "success": success,
                  "resulting_state": {"solved": True, "verifiedResolved": True}},
        ).status_code == 201
    close(client, student, attempt_id, verified=True, payload={"resolved": True})
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=headers,
                        json={"idempotency_key": "complete"})
    assert grade.json()["passed"] is False
    assert grade.json()["details"]["objective_checks"]["approved_corrective_action"] is False


def test_inc2405_correct_target_evidence_passes(db):
    student = make_student(db, username="sloane-pass")
    assignment = setup_assignment(db, student, stable_key="inc2405", priority="low", process_profile=True)
    client = make_client(service_desk.router)
    attempt_id = start(client, student, assignment).json()["id"]
    complete_process_workflow(client, student, attempt_id, "inc2405")
    close(client, student, attempt_id)
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student),
                        json={"idempotency_key": "complete"})
    assert grade.json()["passed"] is True and grade.json()["overall_score"] == 100


@pytest.mark.parametrize("event_type", ["directory.unlock_account", "directory.reset_mfa"])
def test_inc2401_old_account_actions_cannot_solve_process_version(db, event_type):
    student = make_student(db, username=f"inc2401-old-{event_type.rsplit('.', 1)[1]}")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(
        db, student, stable_key="inc2401", process_profile=True
    )).json()["id"]
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    headers = auth_headers(student)
    assert client.post(path, headers=headers, json={
        "idempotency_key": "assign", "event_type": "ticket.assign", "tool": "ticket",
        "payload": {"ticketId": "INC2401"},
    }).status_code == 201
    assert client.post(path, headers=headers, json={
        "idempotency_key": "old-fix", "event_type": event_type, "tool": "directory",
        "payload": {"directoryUserId": "directory-user-avery-brooks"},
    }).status_code == 201
    close(client, student, attempt_id)
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=headers,
                        json={"idempotency_key": "complete"})
    assert grade.json()["passed"] is False
    assert grade.json()["overall_score"] == 0


def test_inc2401_profile_evidence_repair_and_verification_earn_full_credit(db):
    student = make_student(db, username="inc2401-profile-pass")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(
        db, student, stable_key="inc2401", process_profile=True
    )).json()["id"]
    complete_process_workflow(client, student, attempt_id, "inc2401")
    close(client, student, attempt_id)
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student),
                        json={"idempotency_key": "complete"}).json()
    assert grade["passed"] is True and grade["overall_score"] == 100
    assert grade["details"]["objective_checks"] == {
        "server_verifiable": True, "investigation": True, "diagnosis": True,
        "remediation": True, "verification": True, "documentation": True,
        "technical_complete": True,
    }


def test_inc2405_group_change_cannot_solve_mapping_version(db):
    student = make_student(db, username="inc2405-group-guess")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(
        db, student, stable_key="inc2405", priority="low", process_profile=True
    )).json()["id"]
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    headers = auth_headers(student)
    assert client.post(path, headers=headers, json={
        "idempotency_key": "assign", "event_type": "ticket.assign", "tool": "ticket",
        "payload": {"ticketId": "INC2405"},
    }).status_code == 201
    assert client.post(path, headers=headers, json={
        "idempotency_key": "group", "event_type": "directory.update_groups", "tool": "directory",
        "payload": {"directoryUserId": "directory-user-sloane-rivera", "add": ["Facilities Calendar"]},
    }).status_code == 201
    close(client, student, attempt_id)
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=headers,
                        json={"idempotency_key": "complete"}).json()
    assert grade["passed"] is False and grade["overall_score"] == 0


def _submit_actions(client, student, attempt_id, ticket_id, actions):
    headers = auth_headers(student)
    path = f"/api/service-desk/attempts/{attempt_id}/actions"
    assert client.post(path, headers=headers, json={
        "idempotency_key": "assign", "event_type": "ticket.assign", "tool": "ticket",
        "payload": {"ticketId": ticket_id},
    }).status_code == 201
    for index, (event_type, tool, payload) in enumerate(actions):
        response = client.post(path, headers=headers, json={
            "idempotency_key": f"action-{index}", "event_type": event_type,
            "tool": tool, "payload": payload,
        })
        assert response.status_code == 201, response.text


def test_inc2404_isolation_path_scores_higher_than_immediate_replacement(db):
    def grade_for(username, actions):
        student = make_student(db, username=username)
        client = make_client(service_desk.router)
        attempt_id = start(client, student, setup_assignment(
            db, student, stable_key="inc2404", priority="medium", process_profile=True
        )).json()["id"]
        _submit_actions(client, student, attempt_id, "INC2404", actions)
        close(client, student, attempt_id)
        return client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student),
                           json={"idempotency_key": "complete"}).json()

    replacement = [
        ("asset.change_status", "asset", {"assetTag": "NX-9052", "status": "damaged"}),
        ("shipping.create", "shipping", {"recipientDirectoryUserId": "directory-user-elliot-ward", "equipment": [{"name": "Headset", "quantity": 1}]}),
        ("asset.record_isolation", "asset", {"assetTag": "NX-9052", "test": "replacement-clean-audio"}),
        ("ticket.add_note", "ticket", {"ticketId": "INC2404", "body": "Replacement shipped and clean audio confirmed after the repair."}),
    ]
    immediate = grade_for("inc2404-immediate", replacement)
    assert immediate["passed"] is True and immediate["overall_score"] == 60

    student = make_student(db, username="inc2404-isolated")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(
        db, student, stable_key="inc2404", priority="medium", process_profile=True
    )).json()["id"]
    complete_process_workflow(client, student, attempt_id, "inc2404")
    close(client, student, attempt_id)
    isolated = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student),
                           json={"idempotency_key": "complete"}).json()
    assert isolated["overall_score"] == 100 > immediate["overall_score"]


@pytest.mark.parametrize(
    ("stable_key", "ticket_id", "repair_actions", "expected_score"),
    [
        ("inc2407", "INC2407", [
            ("remote_desktop.settings_update_dns", "remote_desktop", {"assetTag": "NX-8892", "primaryDns": "10.20.0.10", "secondaryDns": "10.20.0.11"}),
            ("remote_desktop.run_terminal_command", "remote_desktop", {"assetTag": "NX-8892", "command": "nslookup intranet.nexus.internal"}),
            ("remote_desktop.add_internal_note", "remote_desktop", {"assetTag": "NX-8892", "ticketId": "INC2407", "body": "DNS changed and the original internal hostname now resolves."}),
        ], 60),
        ("inc2408", "INC2408", [
            ("remote_desktop.start_service", "remote_desktop", {"assetTag": "NX-4419", "serviceName": "Print Spooler"}),
            ("remote_desktop.perform_scenario_step", "remote_desktop", {"assetTag": "NX-4419", "ticketId": "INC2408", "stepId": "printer.test-page"}),
            ("remote_desktop.add_internal_note", "remote_desktop", {"assetTag": "NX-4419", "ticketId": "INC2408", "body": "Spooler started and the original print test now completes."}),
        ], 60),
    ],
)
def test_evidence_led_dns_and_print_paths_outscore_blind_repairs(db, stable_key, ticket_id, repair_actions, expected_score):
    student = make_student(db, username=f"{stable_key}-blind")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(
        db, student, stable_key=stable_key, process_profile=True
    )).json()["id"]
    _submit_actions(client, student, attempt_id, ticket_id, repair_actions)
    close(client, student, attempt_id)
    blind = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student),
                        json={"idempotency_key": "complete"}).json()
    assert blind["passed"] is True and blind["overall_score"] == expected_score

    evidence_student = make_student(db, username=f"{stable_key}-evidence")
    evidence_client = make_client(service_desk.router)
    evidence_attempt = start(evidence_client, evidence_student, setup_assignment(
        db, evidence_student, stable_key=stable_key, process_profile=True
    )).json()["id"]
    complete_process_workflow(evidence_client, evidence_student, evidence_attempt, stable_key)
    close(evidence_client, evidence_student, evidence_attempt)
    evidence = evidence_client.post(f"/api/service-desk/attempts/{evidence_attempt}/complete", headers=auth_headers(evidence_student),
                                    json={"idempotency_key": "complete"}).json()
    assert evidence["overall_score"] == 100 > blind["overall_score"]


@pytest.mark.parametrize("stable_key, evidence", [
    ("inc2401", [("directory.unlock_account", "directory", {"directoryUserId": "directory-user-avery-brooks"})]),
    ("inc2406", [("remote_desktop.vpn_complete_connection", "remote_desktop", {"assetTag": "NX-2047"}),
                 ("remote_desktop.explorer_reconnect_drive", "remote_desktop", {"assetTag": "NX-2047", "driveLetter": "Z:"}),
                 ("remote_desktop.add_internal_note", "remote_desktop", {"assetTag": "NX-2047", "ticketId": "INC2406"})]),
    ("inc2407", [("remote_desktop.settings_update_dns", "remote_desktop", {"assetTag": "NX-8892"}),
                 ("remote_desktop.run_terminal_command", "remote_desktop", {"assetTag": "NX-8892", "command": "nslookup intranet.nexus.internal"}),
                 ("remote_desktop.add_internal_note", "remote_desktop", {"assetTag": "NX-8892", "ticketId": "INC2407"})]),
    ("inc2408", [("remote_desktop.restart_service", "remote_desktop", {"assetTag": "NX-4419", "serviceName": "Print Spooler"}),
                 ("remote_desktop.perform_scenario_step", "remote_desktop", {"assetTag": "NX-4419", "ticketId": "INC2408", "stepId": "printer.test-page"}),
                 ("remote_desktop.add_internal_note", "remote_desktop", {"assetTag": "NX-4419", "ticketId": "INC2408"})]),
])
def test_raw_api_fabricated_full_evidence_sequence_is_not_trusted(db, stable_key, evidence):
    student = make_student(db, username=f"raw-sequence-{stable_key}")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(db, student, stable_key=stable_key)).json()["id"]
    headers = auth_headers(student)
    for index, (event_type, tool, payload) in enumerate(evidence):
        assert client.post(f"/api/service-desk/attempts/{attempt_id}/events", headers=headers, json={
            "idempotency_key": f"raw-{index}", "event_type": event_type, "tool": tool,
            "payload": payload, "resulting_state": {"forged": True}, "success": True,
        }).status_code == 201
    close(client, student, attempt_id)
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=headers,
                        json={"idempotency_key": "complete"})
    assert grade.json()["passed"] is False


@pytest.mark.parametrize("stable_key", sorted(SCENARIO_OBJECTIVES))
def test_server_authorized_workflow_passes_every_auto_gradable_scenario(db, stable_key):
    student = make_student(db, username=f"authorized-{stable_key}")
    client = make_client(service_desk.router)
    attempt_id = start(client, student, setup_assignment(
        db, student, stable_key=stable_key, process_profile=True
    )).json()["id"]
    complete_process_workflow(client, student, attempt_id, stable_key)
    close(client, student, attempt_id)
    grade = client.post(f"/api/service-desk/attempts/{attempt_id}/complete", headers=auth_headers(student),
                        json={"idempotency_key": "complete"})
    assert grade.json()["passed"] is True and grade.json()["overall_score"] == 100


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
