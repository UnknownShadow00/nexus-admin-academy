"""Per-student V2 pilot targeting.

V2 is piloted with a named handful of students, not the whole cohort. Access
is the conjunction of a master kill switch and an explicit allowlist, and it
fails closed in every direction: flag off, not enrolled, unauthenticated, or a
malformed allowlist all deny.
"""

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.routers.v2_curriculum import router as curriculum_router
from app.routers.v2_progress import router as progress_router
from app.services.v2_access import (
    pilot_student_count,
    pilot_student_ids,
    student_has_v2_access,
    v2_access_state,
    v2_master_enabled,
)
from app.services.v2_content_loader import load_module

MODULE = "module.aplus.core1.network_services_troubleshooting"


def _client():
    return make_client(curriculum_router, progress_router)


def _loaded(db):
    load_module(db, commit=True)


# --------------------------------------------------------------------------- #
# Allowlist parsing
# --------------------------------------------------------------------------- #

def test_unset_allowlist_enrols_nobody(monkeypatch):
    monkeypatch.delenv("V2_PILOT_STUDENT_IDS", raising=False)
    assert pilot_student_ids() == frozenset()
    assert pilot_student_count() == 0


def test_empty_allowlist_enrols_nobody(monkeypatch):
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "   ")
    assert pilot_student_ids() == frozenset()


def test_malformed_entries_are_ignored_without_raising(monkeypatch):
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "3,abc,,-1,7.5,0,7,,x")
    assert pilot_student_ids() == frozenset({3, 7})


def test_whitespace_is_tolerated(monkeypatch):
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "  3 ,\t7 \n")
    assert pilot_student_ids() == frozenset({3, 7})


def test_duplicate_ids_are_harmless(monkeypatch):
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "3,3,7,3")
    assert pilot_student_ids() == frozenset({3, 7})
    assert pilot_student_count() == 2


def test_semicolon_and_newline_separators_are_accepted(monkeypatch):
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", "3;7\n11")
    assert pilot_student_ids() == frozenset({3, 7, 11})


def test_master_flag_is_off_by_default(monkeypatch):
    monkeypatch.delenv("V2_CURRICULUM_ENABLED", raising=False)
    assert v2_master_enabled() is False


# --------------------------------------------------------------------------- #
# The access matrix
# --------------------------------------------------------------------------- #

def test_master_off_with_enrolled_student_is_denied(db, monkeypatch):
    _loaded(db)
    student = make_student(db, username="pilot_master_off")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "false")
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", str(student.id))

    assert student_has_v2_access(student) is False
    response = _client().get("/api/v2/curriculum", headers=auth_headers(student))
    assert response.status_code == 404
    assert response.json()["detail"] == "This learning experience is not available."


def test_master_on_but_not_enrolled_is_denied(db, monkeypatch):
    _loaded(db)
    student = make_student(db, username="pilot_not_enrolled")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", str(student.id + 1000))

    assert student_has_v2_access(student) is False
    assert _client().get("/api/v2/curriculum", headers=auth_headers(student)).status_code == 404


def test_master_on_and_enrolled_is_allowed(db, monkeypatch):
    _loaded(db)
    student = make_student(db, username="pilot_enrolled")
    enroll_v2(monkeypatch, student)

    assert student_has_v2_access(student) is True
    assert _client().get("/api/v2/curriculum", headers=auth_headers(student)).status_code == 200


def test_mentor_reaches_v2_without_being_enrolled(db, monkeypatch):
    _loaded(db)
    student = make_student(db, username="pilot_mentor")
    student.is_mentor = True
    db.commit()
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    monkeypatch.delenv("V2_PILOT_STUDENT_IDS", raising=False)

    assert student_has_v2_access(student) is True
    assert v2_access_state(student)["mode"] == "mentor"
    assert _client().get("/api/v2/curriculum", headers=auth_headers(student)).status_code == 200


def test_mentor_is_still_blocked_by_the_master_switch(db, monkeypatch):
    student = make_student(db, username="pilot_mentor_off")
    student.is_mentor = True
    db.commit()
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "false")
    assert student_has_v2_access(student) is False


def test_admin_mentor_surface_ignores_the_student_allowlist(db, monkeypatch):
    """Admin V2 routes authorize through verify_admin and the master switch.

    The allowlist is a *student* enrolment list; narrowing admin surfaces with
    it would lock mentors out of their own cohort view.
    """
    from app.routers.admin_v2_mentor import router as mentor_router

    _loaded(db)
    monkeypatch.setenv("ADMIN_API_KEY", "pilot-mentor-key")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    monkeypatch.delenv("V2_PILOT_STUDENT_IDS", raising=False)
    client = make_client(mentor_router)

    assert client.get(
        f"/api/admin/v2/mentor/cohort/{MODULE}", headers={"X-Admin-Key": "pilot-mentor-key"}
    ).status_code == 200

    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "false")
    assert client.get(
        f"/api/admin/v2/mentor/cohort/{MODULE}", headers={"X-Admin-Key": "pilot-mentor-key"}
    ).status_code == 404


# --------------------------------------------------------------------------- #
# Enforcement is server-side, on every V2 student surface
# --------------------------------------------------------------------------- #

def test_unauthenticated_requests_are_denied(db, monkeypatch):
    _loaded(db)
    student = make_student(db, username="pilot_anon_peer")
    enroll_v2(monkeypatch, student)
    assert _client().get("/api/v2/curriculum").status_code in {401, 403}
    assert _client().get(f"/api/v2/progress/module/{MODULE}").status_code in {401, 403}


def test_manual_api_calls_by_a_non_enrolled_student_are_denied(db, monkeypatch):
    """Hiding the navigation is not the boundary — the server is.

    A non-enrolled student who types a V2 URL or calls the API directly must
    be refused on every V2 student route, including the progress roll-up.
    """
    _loaded(db)
    enrolled = make_student(db, username="pilot_typed_url_ok")
    outsider = make_student(db, username="pilot_typed_url_denied")
    enroll_v2(monkeypatch, enrolled)
    client = _client()
    headers = auth_headers(outsider)

    for method, path in (
        ("get", "/api/v2/curriculum"),
        ("get", f"/api/v2/curriculum/modules/{MODULE}"),
        ("get", f"/api/v2/progress/module/{MODULE}"),
    ):
        assert getattr(client, method)(path, headers=headers).status_code == 404, path


def test_v2_progress_rollup_is_gated(db, monkeypatch):
    """Regression: this route shipped with no feature gate of any kind."""
    _loaded(db)
    student = make_student(db, username="pilot_progress_gate")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    monkeypatch.delenv("V2_PILOT_STUDENT_IDS", raising=False)
    assert _client().get(
        f"/api/v2/progress/module/{MODULE}", headers=auth_headers(student)
    ).status_code == 404

    enroll_v2(monkeypatch, student)
    assert _client().get(
        f"/api/v2/progress/module/{MODULE}", headers=auth_headers(student)
    ).status_code == 200


def test_no_cross_student_data_exposure_between_enrolled_students(db, monkeypatch):
    _loaded(db)
    student_a = make_student(db, username="pilot_cross_a")
    student_b = make_student(db, username="pilot_cross_b")
    enroll_v2(monkeypatch, student_a, student_b)
    client = _client()

    client.post(
        f"/api/v2/curriculum/modules/{MODULE}/lessons/"
        f"{client.get(f'/api/v2/curriculum/modules/{MODULE}', headers=auth_headers(student_a)).json()['data']['lessons'][0]['key']}/complete",
        headers=auth_headers(student_a),
    )
    b_view = client.get(
        f"/api/v2/progress/module/{MODULE}", headers=auth_headers(student_b)
    ).json()["data"]
    assert b_view["lessons"]["completed"] == 0


# --------------------------------------------------------------------------- #
# The access-status contract
# --------------------------------------------------------------------------- #

def _access(client, student):
    response = client.get("/api/v2/curriculum/access", headers=auth_headers(student))
    assert response.status_code == 200
    return response.json()["data"]


def test_access_status_answers_while_v2_is_off(db, monkeypatch):
    student = make_student(db, username="access_off")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "false")
    monkeypatch.setenv("V2_PILOT_STUDENT_IDS", str(student.id))
    assert _access(_client(), student) == {
        "master_enabled": False, "student_enabled": False, "mode": "disabled",
    }


def test_access_status_reports_not_enrolled(db, monkeypatch):
    student = make_student(db, username="access_not_enrolled")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    monkeypatch.delenv("V2_PILOT_STUDENT_IDS", raising=False)
    assert _access(_client(), student) == {
        "master_enabled": True, "student_enabled": False, "mode": "not_enrolled",
    }


def test_access_status_reports_pilot_enrolment(db, monkeypatch):
    student = make_student(db, username="access_enrolled")
    enroll_v2(monkeypatch, student)
    assert _access(_client(), student) == {
        "master_enabled": True, "student_enabled": True, "mode": "pilot",
    }


def test_access_status_never_leaks_the_allowlist(db, monkeypatch):
    student = make_student(db, username="access_leak_check")
    other = make_student(db, username="access_leak_other")
    enroll_v2(monkeypatch, student, other)
    body = _client().get(
        "/api/v2/curriculum/access", headers=auth_headers(student)
    ).text

    assert set(_access(_client(), student)) == {"master_enabled", "student_enabled", "mode"}
    assert str(other.id) not in body
    assert "V2_PILOT_STUDENT_IDS" not in body
    for leaked in ("allowlist", "pilot_student_ids", "count"):
        assert leaked not in body.lower()


def test_access_status_requires_authentication(db):
    assert _client().get("/api/v2/curriculum/access").status_code in {401, 403}
