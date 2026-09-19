from pathlib import Path

import yaml


def _load_labs(filename):
    path = (
        Path(__file__).resolve().parents[1]
        / "content"
        / "labs"
        / filename
    )
    return yaml.safe_load(path.read_text(encoding="utf-8"))["labs"]


def test_published_printer_practical_remains_non_vm_curriculum():
    lab = next(
        item
        for item in _load_labs("module-aplus-core1-printers-mfds.yaml")
        if item["title"] == "Print Path Lab: From Application to Paper"
    )

    assert lab["is_published"] is True
    assert "proxmox_template_vmid" not in lab
    assert "environment_requirements" not in lab
    assert "vm_required" not in lab["success_criteria"]


def test_inc2504_hybrid_metadata_is_isolated_in_unpublished_poc():
    [lab] = _load_labs("inc2504-hybrid-poc.yaml")

    assert lab["title"] == "INC2504 Hybrid Lab POC (Disabled)"
    assert lab["is_published"] is False
    assert lab["proxmox_template_vmid"] == 173
    assert lab["environment_requirements"]["service_desk_scenario"] == "inc2504"
    assert lab["environment_requirements"]["concurrency"] == "single_active_instance"
    assert lab["environment_requirements"]["provisioning"] == {
        "handler": "inc2504_printer_stale_ip"
    }
    assert lab["success_criteria"]["vm_required"] is True
    assert "break_script" not in lab
