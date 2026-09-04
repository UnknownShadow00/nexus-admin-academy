"""Retry after a failed attempt, and pre-decision escalation privacy.

Covers the corrective-sprint P0 (a failed attempt must not lock a student out
while attempts remain) plus the guarantee that neither the assignment listing
nor an in-progress attempt reveals whether escalation is expected or which team
is correct.
"""

import json

from app.routers import service_desk
from conftest import auth_headers, make_student
from test_service_desk_attempts import (
    close,
    make_client,
    setup_assignment,
    start,
)


def _client():
    return make_client(service_desk.router)


def _complete(client, student, attempt_id):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/complete",
        headers=auth_headers(student),
        json={"idempotency_key": f"complete-{attempt_id}"},
    )


def _hint(client, student, attempt_id):
    return client.post(
        f"/api/service-desk/attempts/{attempt_id}/hints",
        headers=auth_headers(student),
        json={
            "idempotency_key": f"hint-{attempt_id}",
            "tool": "ticket",
            "payload": {"ticketId": "INC2506", "step": 1},
        },
    )


def _fail_attempt(client, student, attempt_id):
    """Close with no trusted evidence at all - a guaranteed failing attempt."""
    close(client, student, attempt_id)
    response = _complete(client, student, attempt_id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["passed"] is False
    return body


# --------------------------------------------------------------------------- #
# P0 - retry
# --------------------------------------------------------------------------- #


def test_failed_attempt_can_be_retried_until_the_server_ceiling(db):
    student = make_student(db, username="retry-ceiling")
    assignment = setup_assignment(
        db,
        student,
        stable_key="inc2506",
        priority="high",
        process_profile=True,
        maximum_attempts=3,
        # Guided experience: hints are available, so attempt-scoped hint usage
        # can be asserted against the next attempt.
        mode="learning",
    )
    client = _client()

    first = start(client, student, assignment)
    assert first.status_code == 201
    first_id = first.json()["id"]
    assert first.json()["attempt_number"] == 1
    assert _hint(client, student, first_id).status_code == 201

    grade_one = _fail_attempt(client, student, first_id)
    debrief_one = grade_one["debrief"]
    assert debrief_one["result"]["attempts_remaining"] == 2
    # Failed with retries left: limited coaching only.
    assert debrief_one["coaching_tier"] == "limited"
    assert debrief_one["stronger_path"] == []
    assert debrief_one["escalation_feedback"] is None
    assert grade_one["details"]["hints_used"] == 1

    # The retry action starts the next SERVER attempt - the client never
    # invents the number.
    second = start(client, student, assignment)
    assert second.status_code == 201
    second_id = second.json()["id"]
    assert second_id != first_id
    assert second.json()["attempt_number"] == 2

    # Attempt 2 carries none of attempt 1's evidence or hint usage.
    attempt_two = client.get(
        f"/api/service-desk/attempts/{second_id}", headers=auth_headers(student)
    ).json()
    assert attempt_two["grade"] is None
    assert attempt_two["workspace_view"]["evidence"] == []
    assert attempt_two["status"] == "in_progress"

    # Attempt 1 remains historical and still carries its own grade.
    attempt_one = client.get(
        f"/api/service-desk/attempts/{first_id}", headers=auth_headers(student)
    ).json()
    assert attempt_one["status"] == "failed"
    assert attempt_one["grade"]["passed"] is False

    # Reloading resumes attempt 2 rather than burning another attempt.
    resumed = start(client, student, assignment)
    assert resumed.status_code == 200
    assert resumed.json()["id"] == second_id

    grade_two = _fail_attempt(client, student, second_id)
    assert grade_two["debrief"]["result"]["attempts_remaining"] == 1
    assert grade_two["details"]["hints_used"] == 0

    third = start(client, student, assignment)
    assert third.status_code == 201
    assert third.json()["attempt_number"] == 3
    grade_three = _fail_attempt(client, student, third.json()["id"])
    # Final graded attempt: the full walkthrough is released.
    assert grade_three["debrief"]["result"]["attempts_remaining"] == 0
    assert grade_three["debrief"]["coaching_tier"] == "full"
    assert grade_three["debrief"]["stronger_path"]

    # No fourth attempt once the ceiling is reached.
    fourth = start(client, student, assignment)
    assert fourth.status_code == 403


def test_single_attempt_assignment_offers_no_retry_and_full_coaching(db):
    """Failed with zero attempts remaining: no retry, but the full debrief."""
    student = make_student(db, username="retry-single-attempt")
    assignment = setup_assignment(
        db,
        student,
        stable_key="inc2506",
        priority="high",
        process_profile=True,
        maximum_attempts=1,
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    grade = _fail_attempt(client, student, attempt_id)
    debrief = grade["debrief"]
    assert debrief["result"]["attempts_remaining"] == 0
    assert debrief["coaching_tier"] == "full"
    assert debrief["stronger_path"]
    assert debrief["escalation_feedback"] is not None
    assert start(client, student, assignment).status_code == 403


# --------------------------------------------------------------------------- #
# Escalation privacy before the student decides
# --------------------------------------------------------------------------- #

_ROUTE_LEAKS = (
    "Identity & Access",
    "Information Security",
    "escalation_expected",
    "escalation_correct",
    "no_escalation_rationale",
)


def test_assignment_listing_does_not_reveal_escalation_expectation(db):
    student = make_student(db, username="leak-assignments")
    for key in ("inc2506", "inc2401"):
        setup_assignment(
            db, student, stable_key=key, priority="high", process_profile=True
        )
    client = _client()
    listing = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    )
    assert listing.status_code == 200
    for leak in _ROUTE_LEAKS:
        assert leak not in listing.text

    views = [
        row["workspace_view"]
        for row in listing.json()
        if row.get("workspace_view") is not None
    ]
    assert views
    # Identical, route-free affordance for escalation and ordinary tickets.
    assert {json.dumps(view["escalation"], sort_keys=True) for view in views} == {
        json.dumps({"available": True}, sort_keys=True)
    }


def test_active_attempt_does_not_reveal_the_correct_route(db):
    student = make_student(db, username="leak-attempt")
    assignment = setup_assignment(
        db, student, stable_key="inc2506", priority="high", process_profile=True
    )
    client = _client()
    attempt_id = start(client, student, assignment).json()["id"]
    live = client.get(
        f"/api/service-desk/attempts/{attempt_id}", headers=auth_headers(student)
    )
    assert live.status_code == 200
    for leak in _ROUTE_LEAKS:
        assert leak not in live.text
    assert live.json()["workspace_view"]["escalation"] == {"available": True}
    assert "resolve_blockers" not in live.json()["workspace_view"]
