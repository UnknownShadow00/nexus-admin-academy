from pathlib import Path

import yaml


def test_printer_lab_uses_inc2504_allowlisted_metadata():
    path = (
        Path(__file__).resolve().parents[1]
        / "content"
        / "labs"
        / "module-aplus-core1-printers-mfds.yaml"
    )
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    lab = next(
        item
        for item in document["labs"]
        if item["title"] == "Print Path Lab: From Application to Paper"
    )

    assert lab["proxmox_template_vmid"] == 173
    assert lab["environment_requirements"]["service_desk_scenario"] == "inc2504"
    assert lab["environment_requirements"]["concurrency"] == "single_active_instance"
    assert lab["environment_requirements"]["provisioning"] == {
        "handler": "inc2504_printer_stale_ip"
    }
    assert lab["success_criteria"]["vm_required"] is True
    assert "break_script" not in lab
