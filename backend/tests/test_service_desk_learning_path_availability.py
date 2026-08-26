"""Regression coverage for the Learning Path / Service Desk availability
mismatch: the Learning Path page must never show an actionable Start CTA
for a Service Desk case the Service Desk backend will reject.

Root cause: training_service.py's service_desk_scenario resolution computed
its Start CTA purely from "does a ServiceDeskScenario record exist," never
consulting the same authoritative unlock answer
(app.services.service_desk_progression.scenario_access) that Service Desk's
own endpoints (list_assignments, require_scenario_unlocked) use. The two
answers happened to agree for students provisioned through the admin
student-create endpoint or seed.py's bulk sync, but conftest.make_student
(used by ~340 other tests, and structurally identical to
scripts/seed_users.py's direct Student(...) insert) creates a student with
zero ServiceDeskAssignment rows -- exactly the gap that produced "Case
unavailable" for a curriculum-required, definitionally-unlocked case.

Fix: training_service.py now calls the same scenario_access() function
Service Desk uses, and service_desk_progression.ensure_assigned_scenarios
lazily/idempotently backfills the one missing precondition (the assignment
row itself) from both the Learning Path and Service Desk's own endpoints.
"""

from app.models.service_desk import ServiceDeskAssignment, ServiceDeskScenario
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.routers.service_desk import router
from app.services.training_service import build_training_overview
from conftest import auth_headers, make_client, make_student
from test_service_desk_progression import _map_required_case, _seed_pack_assignments

client = make_client(router)


def _week1_activity(overview: dict) -> dict:
    return next(
        item
        for item in overview["current_week_activities"]
        if item["activity_type"] == "service_desk_scenario"
    )


def test_missing_assignment_row_is_self_healed_and_learning_path_matches_service_desk(
    monkeypatch, db
):
    """Reproduces the exact reported bug: a student created the same way
    conftest.make_student (and scripts/seed_users.py) does, with no
    pre-provisioned Service Desk assignment inventory, reaching the week of
    a required case ("locked-user-account"-equivalent) before completing an
    earlier same-week item. Before the fix, Learning Path showed Start while
    Service Desk's queue had nothing to return for it."""
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 1,
    )
    student = make_student(db, "healed-assignment-student")
    _seed_pack_assignments(db)  # scenarios + versions only, no assignment rows
    _map_required_case(db, 1, "locked-user-account")

    assert (
        db.query(ServiceDeskAssignment).filter_by(student_id=student.id).count() == 0
    )

    overview = build_training_overview(db, student)
    activity = _week1_activity(overview)
    assert activity["content_ref"] == "locked-user-account"
    assert activity["permission_locked"] is False
    assert activity["status"] != "locked"
    assert activity["destination_route"] is not None

    # Visiting the Learning Path healed the gap: Service Desk's own queue
    # now agrees, backed by a real assignment row -- ensure_assigned_scenarios
    # tops off the whole starter-support pack (not just this one case), so
    # assert presence rather than an exact count.
    healed_keys = {
        stable_key
        for (stable_key,) in db.query(ServiceDeskScenario.stable_key)
        .join(
            ServiceDeskAssignment,
            ServiceDeskAssignment.scenario_id == ServiceDeskScenario.id,
        )
        .filter(ServiceDeskAssignment.student_id == student.id)
        .all()
    }
    assert "locked-user-account" in healed_keys
    row = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    assigned = next(r for r in row if r["scenario"]["stable_key"] == "locked-user-account")
    assert assigned["unlocked"] is True

    # And starting it for real succeeds -- no "Case unavailable" gap.
    assert (
        client.post(
            f"/api/service-desk/assignments/{assigned['id']}/attempts",
            headers=auth_headers(student),
        ).status_code
        == 201
    )


def test_service_desk_endpoints_also_self_heal_without_visiting_learning_path(
    monkeypatch, db
):
    """Order-independent: a student who opens Service Desk directly (without
    ever loading the Learning Path first) must see the same healed state."""
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 1,
    )
    student = make_student(db, "sd-first-visit-student")
    _seed_pack_assignments(db)
    _map_required_case(db, 1, "locked-user-account")

    rows = client.get(
        "/api/service-desk/assignments", headers=auth_headers(student)
    ).json()
    assigned = next(r for r in rows if r["scenario"]["stable_key"] == "locked-user-account")
    assert assigned["unlocked"] is True
    assert (
        client.post(
            f"/api/service-desk/assignments/{assigned['id']}/attempts",
            headers=auth_headers(student),
        ).status_code
        == 201
    )


def test_pack_gated_optional_case_shows_locked_not_start_in_learning_path(
    monkeypatch, db
):
    """An optional (non-curriculum-required) scenario whose pack the student
    hasn't unlocked yet must render as Locked in the Learning Path -- not an
    actionable Start -- even though the week/module containing it is itself
    unlocked."""
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 1,
    )
    student = make_student(db, "pack-gated-student")
    _seed_pack_assignments(db, student)
    # inc2505 belongs to the accounts-access pack (required_week=6), which is
    # not unlocked at current_week=1 -- but curriculum-map it as an OPTIONAL
    # week-1 activity to reproduce "shown early, not actually startable."
    week = TrainingWeek(week_number=1, display_order=1, title="Week 1", learning_goals=[])
    db.add(week)
    db.flush()
    db.add(
        TrainingWeekActivity(
            # Required but unresolvable content_ref: keeps this week genuinely
            # incomplete (not trivially "complete" from having zero required
            # items) without needing a full lesson/quiz fixture, so
            # current_week_activities actually selects this week.
            stable_id="week-1-lesson-placeholder",
            training_week_id=week.id,
            activity_type="lesson",
            content_ref="does-not-exist",
            display_order=1,
            is_required=True,
            prerequisite_mode="soft",
            metadata_json={},
        )
    )
    db.add(
        TrainingWeekActivity(
            stable_id="week-1-service-desk-inc2505-optional",
            training_week_id=week.id,
            activity_type="service_desk_scenario",
            content_ref="inc2505",
            display_order=2,
            is_required=False,
            prerequisite_mode="soft",
            metadata_json={},
        )
    )
    db.commit()

    overview = build_training_overview(db, student)
    activity = next(
        item
        for item in overview["current_week_activities"]
        if item["activity_type"] == "service_desk_scenario" and item["content_ref"] == "inc2505"
    )
    assert activity["permission_locked"] is True
    assert activity["status"] == "locked"
    assert activity["destination_route"] is None
    assert activity["permission_reason"]


def test_direct_start_of_a_not_yet_reached_weeks_case_is_still_rejected_server_side(
    monkeypatch, db
):
    """Frontend lock state is UX only. Even for a curriculum-required case,
    a student who has not reached its week must still be rejected by
    Service Desk's own authoritative check -- the Learning Path fix must
    never become the only thing standing between a student and a locked
    case."""
    monkeypatch.setattr(
        "app.services.service_desk_progression.derive_current_week",
        lambda _student_id, _db: 0,
    )
    student = make_student(db, "not-reached-student")
    _seed_pack_assignments(db, student)
    _map_required_case(db, 1, "locked-user-account")

    overview = build_training_overview(db, student)
    # Week 1 itself isn't locked here (this isolated DB has no week 0 to
    # fail the week-level "prior_required_complete" gate) -- the point of
    # this test is the per-activity gate this fix added: at current_week=0,
    # scenario_access must say "locked-user-account" (week 1) is not yet
    # curriculum-unlocked, so the Learning Path must never show Start for it.
    activity = _week1_activity(overview)
    assert activity["permission_locked"] is True
    assert activity["status"] == "locked"
    assert activity["destination_route"] is None

    assignment = (
        db.query(ServiceDeskAssignment)
        .join(ServiceDeskScenario, ServiceDeskAssignment.scenario_id == ServiceDeskScenario.id)
        .filter(
            ServiceDeskAssignment.student_id == student.id,
            ServiceDeskScenario.stable_key == "locked-user-account",
        )
        .first()
    )
    assert (
        client.post(
            f"/api/service-desk/assignments/{assignment.id}/attempts",
            headers=auth_headers(student),
        ).status_code
        == 403
    )
