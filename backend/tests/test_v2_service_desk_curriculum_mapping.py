"""Section 3 regression guard for V2 Service Desk curriculum bindings."""

from __future__ import annotations

import pytest

import seed_v2_foundation
from app.models.certification import CertificationModule, ModuleAssessment
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.services.service_desk_objectives import objective_definition
from app.services.service_desk_scenario_validation import (
    scenario_has_supported_grading_profile,
)
from app.services.v2_content_loader import AUTO_DEACTIVATED_REASON_KEY
from app.services.v2_curriculum_service import (
    assessment_is_available,
    launch_service_desk,
    service_desk_scenario_is_playable,
)
from conftest import enroll_v2, make_student


AVAILABLE = {
    "module.aplus.core1.ip_configuration": (
        "assess.aplus.ipcfg.service_desk",
        "inc2503",
    ),
    "module.aplus.core1.printers_mfds": (
        "assess.aplus-core1-printers-mfds.service_desk",
        "inc2504",
    ),
    "module.aplus.core2.windows_troubleshooting": (
        "assess.aplus.wintriage.service_desk",
        "inc2403",
    ),
    "module.aplus.core2.windows_admin_cli_networking": (
        "assess.aplus-core2-windows-admin-cli-networking.service_desk",
        "inc2505",
    ),
    "module.aplus.core2.threat_malware_response": (
        "assess.aplus-core2-threat-malware-response.service_desk",
        "inc2508",
    ),
    "module.aplus.core2.service_desk_workflow": (
        "assess.aplus-core2-service-desk-workflow.service_desk",
        "inc2506",
    ),
}

UNAVAILABLE = {
    "module.aplus.core1.network_services_troubleshooting": (
        "assess.aplus-core1-network-services-troubleshooting.service_desk",
        "service_desk.aplus.network.loading_dock_wifi",
    ),
    "module.aplus.core1.hardware_fault_isolation": (
        "assess.aplus-core1-hardware-fault-isolation.service_desk",
        "service_desk.aplus.hardware.render_shutdown",
    ),
    "module.aplus.core1.mobile_device_support": (
        "assess.aplus-core1-mobile-device-support.service_desk",
        "service_desk.aplus.mobile.intermittent_charge_mail_sync",
    ),
    "module.aplus.core2.identity_endpoint_hardening": (
        "assess.aplus-core2-identity-endpoint-hardening.service_desk",
        "sd.aplus.security.approved_app_standard_user",
    ),
    "module.aplus.core2.connected_endpoint_mobile_security": (
        "assess.aplus-core2-connected-endpoint-mobile-security.service_desk",
        "sd.aplus.security.mobile_secure_wifi_profile",
    ),
    "module.aplus.core2.cross_platform_app_cloud_support": (
        "assess.aplus-core2-cross-platform-app-cloud-support.service_desk",
        "sd.aplus.cross_platform.unlicensed_suite_mac",
    ),
}

ALL_PROCESS_CATEGORIES = {
    "investigation",
    "diagnosis",
    "remediation",
    "verification",
    "documentation",
}


@pytest.fixture()
def loaded_mapping(db):
    seed_v2_foundation.run(db)
    return db


def _assessment(db, module_key: str, assessment_key: str) -> ModuleAssessment:
    module = db.query(CertificationModule).filter_by(module_key=module_key).one()
    return db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id,
        assessment_key=assessment_key,
        assessment_role="service_desk",
    ).one()


@pytest.mark.parametrize(
    ("module_key", "assessment_key", "stable_key"),
    [
        (module_key, assessment_key, stable_key)
        for module_key, (assessment_key, stable_key) in AVAILABLE.items()
    ],
)
def test_available_service_desk_mapping_has_published_supported_scenario(
    loaded_mapping, monkeypatch, module_key, assessment_key, stable_key
):
    assessment = _assessment(loaded_mapping, module_key, assessment_key)
    scenario = loaded_mapping.get(
        ServiceDeskScenario, assessment.service_desk_scenario_id
    )
    assert scenario.stable_key == stable_key
    version = (
        loaded_mapping.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id, status="published")
        .order_by(
            ServiceDeskScenarioVersion.version_number.desc(),
            ServiceDeskScenarioVersion.id.desc(),
        )
        .first()
    )
    assert version is not None

    definition = version.definition_json or {}
    objective = objective_definition(stable_key, definition)
    assert scenario_has_supported_grading_profile(stable_key, definition) is True
    assert objective is not None
    assert {category.name for category in objective.categories} == ALL_PROCESS_CATEGORIES

    assert assessment.active is True
    assert AUTO_DEACTIVATED_REASON_KEY not in (assessment.config or {})
    assert service_desk_scenario_is_playable(loaded_mapping, assessment) is True
    assert assessment_is_available(loaded_mapping, assessment) is True

    student = make_student(loaded_mapping, username=f"mapping-{stable_key}")
    enroll_v2(monkeypatch, student)
    launch = launch_service_desk(
        loaded_mapping, student.id, module_key, assessment_key
    )
    assert launch["launch_url"] == (
        f"/service-desk/tickets/{stable_key.upper()}"
        f"?returnTo=/learning-v2/modules/{module_key}"
        f"&v2ModuleKey={module_key}&v2AssessmentKey={assessment_key}"
    )
    assert launch["mode"] == "learning"
    assert launch["experience_mode"] == "guided"


@pytest.mark.parametrize(
    ("module_key", "assessment_key", "stable_key"),
    [
        (module_key, assessment_key, stable_key)
        for module_key, (assessment_key, stable_key) in UNAVAILABLE.items()
    ],
)
def test_unmatched_service_desk_mapping_remains_unavailable(
    loaded_mapping, module_key, assessment_key, stable_key
):
    assessment = _assessment(loaded_mapping, module_key, assessment_key)
    scenario = loaded_mapping.get(
        ServiceDeskScenario, assessment.service_desk_scenario_id
    )
    assert scenario.stable_key == stable_key
    assert assessment.active is False
    assert (assessment.config or {})[AUTO_DEACTIVATED_REASON_KEY] == (
        "no_grading_profile"
    )
    assert service_desk_scenario_is_playable(loaded_mapping, assessment) is False
    assert assessment_is_available(loaded_mapping, assessment) is False


def test_mapping_partitions_all_service_desk_assessments(loaded_mapping):
    rows = loaded_mapping.query(ModuleAssessment).filter_by(
        assessment_role="service_desk"
    ).all()
    assert len(AVAILABLE) == len(UNAVAILABLE) == 6
    assert {row.assessment_key for row in rows} == {
        assessment_key
        for assessment_key, _ in (*AVAILABLE.values(), *UNAVAILABLE.values())
    }
    assert sum(row.active for row in rows) == 6
