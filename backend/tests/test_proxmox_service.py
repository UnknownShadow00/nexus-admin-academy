from unittest.mock import MagicMock, call

import pytest

from app.services import proxmox_service


def _configure(monkeypatch, *, full_clone: bool):
    monkeypatch.setenv("PROXMOX_HOST", "pve.example")
    monkeypatch.setenv("PROXMOX_TOKEN_ID", "automation@pve!labs")
    monkeypatch.setenv("PROXMOX_TOKEN_SECRET", "secret")
    monkeypatch.setenv("PROXMOX_NODE", "pve")
    monkeypatch.setenv("PROXMOX_POOL", "nexus-labs")
    monkeypatch.setenv("VMID_POOL_START", "200")
    monkeypatch.setenv("VMID_POOL_END", "299")
    monkeypatch.setenv("PROXMOX_FULL_CLONE", "true" if full_clone else "false")


def _mock_proxmox(storage_type="lvmthin"):
    proxmox = MagicMock()
    proxmox.cluster.resources.get.return_value = [{"vmid": 200}]
    node = proxmox.nodes("pve")
    node.qemu(900).config.get.return_value = {"scsi0": "local-lvm:vm-900-disk-0,size=20G"}
    node.storage.get.return_value = [{"storage": "local-lvm", "type": storage_type}]
    node.qemu(900).clone.post.return_value = None
    return proxmox


def test_linked_clone_passes_full_zero_on_supported_storage(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = _mock_proxmox("lvmthin")
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    assert proxmox_service.clone_template(900, "unique-lab-name") == 201
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="unique-lab-name", full=0, pool="nexus-labs"
    )


def test_linked_clone_falls_back_to_full_on_unsupported_storage(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = _mock_proxmox("dir")
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.clone_template(900, "fallback-lab")
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="fallback-lab", full=1, pool="nexus-labs"
    )


def test_explicit_full_clone_skips_storage_probe(monkeypatch):
    _configure(monkeypatch, full_clone=True)
    proxmox = _mock_proxmox()
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.clone_template(900, "full-lab")
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="full-lab", full=1, pool="nexus-labs"
    )
    proxmox.nodes("pve").qemu(900).config.get.assert_not_called()



def test_vmid_pool_skips_reserved_ids(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "179")
    monkeypatch.setenv("VMID_RESERVED", "170,171,173")

    proxmox = _mock_proxmox()
    proxmox.cluster.resources.get.return_value = [
        {"vmid": 172},
        {"vmid": 174},
    ]

    assert proxmox_service._find_free_vmid(proxmox) == 175


def test_vmid_pool_fails_when_no_safe_id_remains(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "174")
    monkeypatch.setenv("VMID_RESERVED", "170,171,173")

    proxmox = _mock_proxmox()
    proxmox.cluster.resources.get.return_value = [
        {"vmid": 172},
        {"vmid": 174},
    ]

    with pytest.raises(RuntimeError, match="No free VMIDs"):
        proxmox_service._find_free_vmid(proxmox)


def test_clone_retries_next_safe_vmid_after_collision(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "179")
    monkeypatch.setenv("VMID_RESERVED", "170,171,173")

    proxmox = _mock_proxmox("lvmthin")
    proxmox.cluster.resources.get.return_value = []
    clone = proxmox.nodes("pve").qemu(900).clone.post
    clone.side_effect = [
        RuntimeError("VM 172 already exists"),
        None,
    ]

    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    assert proxmox_service.clone_template(900, "race-safe-lab") == 174

    assert clone.call_args_list == [
        call(newid=172, name="race-safe-lab", full=0, pool="nexus-labs"),
        call(newid=174, name="race-safe-lab", full=0, pool="nexus-labs"),
    ]


def test_guest_exec_returns_stdout_after_success(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 321}
    vm.agent("exec-status").get.side_effect = [
        {"exited": 0},
        {"exited": 1, "exitcode": 0, "out-data": "NX-2504\\r\\n", "err-data": ""},
    ]
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)
    monkeypatch.setattr(proxmox_service.time, "sleep", lambda _seconds: None)

    output = proxmox_service.guest_exec(
        175,
        ["cmd.exe", "/c", "hostname"],
        timeout=5,
    )

    assert output == "NX-2504\\r\\n"
    vm.agent("exec").post.assert_called_once_with(
        command=["cmd.exe", "/c", "hostname"]
    )
    assert vm.agent("exec-status").get.call_args_list == [
        call(pid=321),
        call(pid=321),
    ]


def test_guest_exec_rejects_nonzero_exit(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 322}
    vm.agent("exec-status").get.return_value = {
        "exited": 1,
        "exitcode": 5,
        "err-data": "Access denied",
    }
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match="Guest command failed with exit code 5"):
        proxmox_service.guest_exec(
            175,
            ["powershell.exe", "-NoProfile", "-Command", "exit 5"],
            timeout=5,
        )


def test_guest_exec_times_out(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 323}
    vm.agent("exec-status").get.return_value = {"exited": 0}
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)
    monkeypatch.setattr(proxmox_service.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        proxmox_service.time,
        "monotonic",
        MagicMock(side_effect=[0.0, 0.0, 6.0]),
    )

    with pytest.raises(TimeoutError, match="Guest command did not finish"):
        proxmox_service.guest_exec(
            175,
            ["cmd.exe", "/c", "hostname"],
            timeout=5,
        )
