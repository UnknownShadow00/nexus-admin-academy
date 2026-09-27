"""Direct lab URLs obey the V2 beginner catalog and trusted-run policy."""

import pytest

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import CertificationModule, ModuleAssessment
from app.models.lab import LabTemplate
from app.models.vm_assignment import VmAssignment
from app.routers.labs import router as labs_router
from app.services.v2_beginner_path import STAGE_KEYS
from app.services.v2_content_loader import load_module

OLD_MODULE = "module.aplus.core1.network_services_troubleshooting"


def _seed_practical(db, module_key):
    module = db.query(CertificationModule).filter_by(module_key=module_key).one()
    lab = LabTemplate(
        title=f"Disposable {module_key} practical", lab_type="guided",
        difficulty=1, week_number=24, is_published=True,
        success_criteria={"tasks": ["Describe the result"]},
    )
    db.add(lab)
    db.flush()
    assessment = ModuleAssessment(
        assessment_key=f"test.practical.{module_key}",
        certification_module_id=module.id, assessment_role="practical",
        lab_template_id=lab.id, title="Disposable practical", active=True,
    )
    db.add(assessment)
    db.commit()
    return lab, assessment


def _params(module_key, assessment):
    return {"v2_module_key": module_key, "v2_assessment_key": assessment.assessment_key}


def test_direct_get_and_start_share_beginner_version_and_prerequisite_policy(db, monkeypatch):
    load_module(db, commit=True)
    student = make_student(db, username="lab_path_policy")
    enroll_v2(monkeypatch, student)
    client = make_client(labs_router)
    headers = auth_headers(student)
    old_module = db.query(CertificationModule).filter_by(module_key=OLD_MODULE).one()
    old = db.query(ModuleAssessment).filter_by(
        certification_module_id=old_module.id, assessment_role="practical"
    ).one()
    old_url = f"/api/labs/{old.lab_template_id}"
    old_params = _params(OLD_MODULE, old)
    first_lab, first = _seed_practical(db, STAGE_KEYS[0])
    second_lab, second = _seed_practical(db, STAGE_KEYS[1])

    # The switch-off path preserves the old practical, while beginner stages
    # remain unavailable by either direct GET or start.
    for method in (client.get, client.post):
        route = old_url if method == client.get else old_url + "/start"
        assert method(route, params=old_params, headers=headers).status_code == 200
        beginner_route = f"/api/labs/{first_lab.id}"
        if method == client.post:
            beginner_route += "/start"
        assert method(beginner_route, params=_params(STAGE_KEYS[0], first), headers=headers).status_code == 404

    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    # The already-owned old run may be inspected, but cannot be started again.
    assert client.post(old_url + "/start", params=old_params, headers=headers).status_code == 404
    assert client.get(old_url, params=old_params, headers=headers).status_code == 200

    for method in (client.get, client.post):
        suffix = "" if method == client.get else "/start"
        first_response = method(f"/api/labs/{first_lab.id}{suffix}", params=_params(STAGE_KEYS[0], first), headers=headers)
        assert first_response.status_code == 200, first_response.text
        locked = method(f"/api/labs/{second_lab.id}{suffix}", params=_params(STAGE_KEYS[1], second), headers=headers)
        assert locked.status_code == 403
        assert "Finish Stage 1" in locked.json()["detail"]
        assert method(f"/api/labs/{second_lab.id}{suffix}", headers=headers).status_code == 404

    forged = _params(STAGE_KEYS[0], second)
    for method in (client.get, client.post):
        suffix = "" if method == client.get else "/start"
        assert method(f"/api/labs/{first_lab.id}{suffix}", params=forged, headers=headers).status_code == 404


def test_cached_old_url_without_owned_run_is_hidden_and_existing_run_can_finish(db, monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.routers.labs._destroy_vm_task", lambda _assignment_id: None)
    load_module(db, commit=True)
    owner = make_student(db, username="lab_switch_owner")
    other = make_student(db, username="lab_switch_other")
    enroll_v2(monkeypatch, owner, other)
    client = make_client(labs_router)
    old_module = db.query(CertificationModule).filter_by(module_key=OLD_MODULE).one()
    old = db.query(ModuleAssessment).filter_by(
        certification_module_id=old_module.id, assessment_role="practical"
    ).one()
    url = f"/api/labs/{old.lab_template_id}"
    params = _params(OLD_MODULE, old)
    started = client.post(url + "/start", params=params, headers=auth_headers(owner))
    assert started.status_code == 200
    run_id = started.json()["data"]["run_id"]
    db.add(VmAssignment(student_id=owner.id, lab_run_id=run_id, status="provisioning"))
    db.commit()

    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    assert client.get(url, params=params, headers=auth_headers(other)).status_code == 404
    assert client.post(url + "/start", params=params, headers=auth_headers(other)).status_code == 404
    assert client.get(url, headers=auth_headers(other)).status_code == 404
    assert client.get(url, params=params, headers=auth_headers(owner)).status_code == 200
    assert client.get(url, headers=auth_headers(owner)).status_code == 200
    forged = {"v2_module_key": STAGE_KEYS[0], "v2_assessment_key": old.assessment_key}
    assert client.get(url, params=forged, headers=auth_headers(owner)).status_code == 404
    assert client.get(url + "/vm-status", headers=auth_headers(owner)).status_code == 200
    assert client.post(url + "/vm-access", headers=auth_headers(owner)).status_code == 409
    evidence = client.post(
        f"/api/labs/{run_id}/evidence", headers=auth_headers(owner),
        files={"file": ("proof.png", b"image", "image/png")},
    )
    assert evidence.status_code == 200, evidence.text
    # Authorization succeeds; this guided lab simply has no verification workbench.
    assert client.post(url + "/verify", json={"answers": {}, "inspected_panel_ids": []}, headers=auth_headers(owner)).status_code == 400
    assert client.post(url + "/verify", params=forged, json={"answers": {}, "inspected_panel_ids": []}, headers=auth_headers(owner)).status_code == 404
    assert client.post(url + "/submit", params=forged, json={"notes": "Evidence"}, headers=auth_headers(owner)).status_code == 404
    submitted = client.post(url + "/submit", params=params, json={"notes": "Evidence checked"}, headers=auth_headers(owner))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["status"] == "submitted"
    assert client.post(url + "/start", params=params, headers=auth_headers(owner)).status_code == 404


@pytest.mark.parametrize("beginner_enabled", [False, True])
def test_legacy_non_v2_lab_still_uses_ordinary_route(db, monkeypatch, beginner_enabled):
    student = make_student(db, username="legacy_lab_path")
    lab = LabTemplate(title="Legacy practice", lab_type="guided", difficulty=1, week_number=1, is_published=True)
    db.add(lab)
    db.commit()
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", str(beginner_enabled).lower())
    client = make_client(labs_router)
    headers = auth_headers(student)
    assert client.get(f"/api/labs/{lab.id}", headers=headers).status_code == 200
    assert client.post(f"/api/labs/{lab.id}/start", headers=headers).status_code == 200
