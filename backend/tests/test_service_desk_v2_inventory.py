"""Wave 1 drift guards for the generated V2 Service Desk inventory."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import seed_v2_foundation
from app.models.certification import ModuleAssessment
from scripts.generate_service_desk_v2_inventory import (
    collect_inventory,
    note_only_assessments,
    wave2_invariant_failures,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_BASELINE = {
    "assess.aplus-core1-hardware-fault-isolation.service_desk",
    "assess.aplus-core1-mobile-device-support.service_desk",
    "assess.aplus-core1-network-services-troubleshooting.service_desk",
    "assess.aplus-core1-printers-mfds.service_desk",
    "assess.aplus-core2-connected-endpoint-mobile-security.service_desk",
    "assess.aplus-core2-cross-platform-app-cloud-support.service_desk",
    "assess.aplus-core2-identity-endpoint-hardening.service_desk",
    "assess.aplus-core2-service-desk-workflow.service_desk",
    "assess.aplus-core2-threat-malware-response.service_desk",
    "assess.aplus-core2-windows-admin-cli-networking.service_desk",
}


def test_inventory_generator_is_scratch_only_and_committed_outputs_match(tmp_path):
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("sqlite:////tmp/"):
        database_url = f"sqlite:///{tmp_path / 'sd-p0-inventory.db'}"
    markdown = tmp_path / "inventory.md"
    fixture_json = tmp_path / "inventory.json"
    env = {**os.environ, "DATABASE_URL": database_url, "V2_CURRICULUM_ENABLED": "false"}
    result = subprocess.run(
        [
            str(REPO_ROOT / "backend/.venv/bin/python"),
            "scripts/generate_service_desk_v2_inventory.py",
            "--output",
            str(markdown),
            "--json-output",
            str(fixture_json),
        ],
        cwd=REPO_ROOT / "backend",
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert f"DATABASE_URL={database_url}" in result.stdout
    assert markdown.read_text(encoding="utf-8") == (
        REPO_ROOT / "docs/service_desk_v2_assessment_inventory.md"
    ).read_text(encoding="utf-8")
    assert fixture_json.read_text(encoding="utf-8") == (
        REPO_ROOT / "docs/service_desk_v2_assessment_inventory.json"
    ).read_text(encoding="utf-8")


def test_inventory_covers_every_service_desk_row_and_records_wave2_baseline(db):
    seed_v2_foundation.run(db)
    rows = collect_inventory(db, feature_enabled=False)
    assessment_count = db.query(ModuleAssessment).filter_by(
        assessment_role="service_desk"
    ).count()

    assert len(rows) == assessment_count == 12
    assert set(note_only_assessments(rows)) == EXPECTED_BASELINE
    assert set(wave2_invariant_failures(rows)) == EXPECTED_BASELINE
