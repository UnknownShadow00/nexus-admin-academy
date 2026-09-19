import logging
from unittest.mock import MagicMock, call

import pytest
import proxmoxer

from app.services import proxmox_service


def test_proxmox_transport_payload_logging_is_disabled():
    assert logging.getLogger("proxmoxer.core").level >= logging.WARNING


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


def test_settings_require_resource_pool(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.delenv("PROXMOX_POOL")

    with pytest.raises(RuntimeError, match="resource pool is not configured"):
        proxmox_service._settings()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("VMID_POOL_START", "not-an-integer", "bounds must be integers"),
        ("PROXMOX_VERIFY_SSL", "sometimes", "must be a boolean value"),
    ],
)
def test_settings_reject_invalid_safety_values(monkeypatch, name, value, message):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match=message):
        proxmox_service._settings()


def test_get_proxmox_splits_token_id_into_user_and_token_name(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    client = MagicMock()
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(proxmoxer, "ProxmoxAPI", constructor)

    assert proxmox_service._get_proxmox() is client
    constructor.assert_called_once_with(
        "pve.example",
        user="automation@pve",
        token_name="labs",
        token_value="secret",
        verify_ssl=False,
    )


@pytest.mark.parametrize(
    "token_id",
    ["automation@pve", "!labs", "automation@pve!"],
)
def test_get_proxmox_rejects_malformed_token_id(monkeypatch, token_id):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("PROXMOX_TOKEN_ID", token_id)

    with pytest.raises(RuntimeError, match="user@realm!token-name"):
        proxmox_service._get_proxmox()


def test_linked_clone_passes_full_zero_on_supported_storage(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = _mock_proxmox("lvmthin")
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    assert proxmox_service.clone_template(900, "lab-1-student-2-run-3") == 201
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="lab-1-student-2-run-3", full=0, pool="nexus-labs"
    )


def test_linked_clone_falls_back_to_full_on_unsupported_storage(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = _mock_proxmox("dir")
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.clone_template(900, "lab-1-student-2-run-3")
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="lab-1-student-2-run-3", full=1, pool="nexus-labs"
    )


def test_explicit_full_clone_skips_storage_probe(monkeypatch):
    _configure(monkeypatch, full_clone=True)
    proxmox = _mock_proxmox()
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.clone_template(900, "lab-1-student-2-run-3")
    proxmox.nodes("pve").qemu(900).clone.post.assert_called_once_with(
        newid=201, name="lab-1-student-2-run-3", full=1, pool="nexus-labs"
    )
    proxmox.nodes("pve").qemu(900).config.get.assert_not_called()


def test_clone_rejects_non_nexus_name_before_api_access(monkeypatch):
    monkeypatch.setattr(
        proxmox_service,
        "_get_proxmox",
        lambda: (_ for _ in ()).throw(AssertionError("API must not be called")),
    )

    with pytest.raises(ValueError, match="assignment-owned naming convention"):
        proxmox_service.clone_template(900, "nexus-win11-auto-base")



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

    assert proxmox_service.clone_template(900, "lab-1-student-2-run-3") == 174

    assert clone.call_args_list == [
        call(newid=172, name="lab-1-student-2-run-3", full=0, pool="nexus-labs"),
        call(newid=174, name="lab-1-student-2-run-3", full=0, pool="nexus-labs"),
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


@pytest.mark.parametrize("started", [{}, {"pid": 0}, {"pid": "321"}, {"pid": True}])
def test_guest_exec_rejects_invalid_pid(monkeypatch, started):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    proxmox.nodes("pve").qemu(175).agent("exec").post.return_value = started
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match="process ID"):
        proxmox_service.guest_exec(175, ["cmd.exe", "/c", "hostname"])


def test_guest_exec_reports_abnormal_termination(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 321}
    vm.agent("exec-status").get.return_value = {
        "exited": 1,
        "signal": 9,
        "out-data": "done",
    }
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match="signal/exception 9"):
        proxmox_service.guest_exec(175, ["cmd.exe", "/c", "hostname"])


def test_guest_exec_rejects_invalid_exited_state(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 321}
    vm.agent("exec-status").get.return_value = {"exited": "yes"}
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match="invalid exited state"):
        proxmox_service.guest_exec(175, ["cmd.exe", "/c", "hostname"])


def test_guest_exec_passes_stdin_without_adding_it_to_command(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 321}
    vm.agent("exec-status").get.return_value = {"exited": 1, "exitcode": 0}
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.guest_exec(
        175,
        ["powershell.exe", "-Command", "[Console]::In.ReadToEnd()"],
        input_data="ephemeral-secret",
    )

    vm.agent("exec").post.assert_called_once_with(
        command=["powershell.exe", "-Command", "[Console]::In.ReadToEnd()"],
        **{"input-data": "ephemeral-secret"},
    )


def test_guest_exec_rejects_truncated_output(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.agent("exec").post.return_value = {"pid": 321}
    vm.agent("exec-status").get.return_value = {
        "exited": 1,
        "exitcode": 0,
        "out-data": "partial",
        "out-truncated": True,
    }
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match="output was truncated"):
        proxmox_service.guest_exec(175, ["cmd.exe", "/c", "hostname"])


def _destruction_proxmox(vmid=175, *, name="lab-1-student-2-run-3", status="stopped"):
    proxmox = MagicMock()
    proxmox.pools("nexus-labs").get.return_value = {
        "members": [{"type": "qemu", "vmid": vmid, "name": name}]
    }
    proxmox.nodes("pve").qemu(vmid).status.current.get.return_value = {"status": status}
    proxmox.nodes("pve").qemu(vmid).delete.return_value = None
    return proxmox


def test_destroy_vm_allows_owned_dynamic_pool_member(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "179")
    monkeypatch.setenv("VMID_RESERVED", "170,171,173")
    proxmox = _destruction_proxmox()
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.destroy_vm(175)

    proxmox.nodes("pve").qemu(175).status.stop.post.assert_not_called()
    proxmox.nodes("pve").qemu(175).delete.assert_called_once_with()


def test_destroy_vm_stops_running_owned_vm_before_delete(monkeypatch):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "179")
    proxmox = _destruction_proxmox(status="running")
    vm = proxmox.nodes("pve").qemu(175)
    vm.status.stop.post.return_value = "UPID:stop"
    vm.delete.return_value = "UPID:delete"
    proxmox.nodes("pve").tasks("UPID:stop").status.get.return_value = {
        "status": "stopped",
        "exitstatus": "OK",
    }
    proxmox.nodes("pve").tasks("UPID:delete").status.get.return_value = {
        "status": "stopped",
        "exitstatus": "OK",
    }
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    proxmox_service.destroy_vm(175)

    vm.status.stop.post.assert_called_once_with()
    vm.delete.assert_called_once_with()


@pytest.mark.parametrize(
    ("vmid", "message"),
    [(169, "outside the dynamic VMID pool"), (173, "reserved VMID")],
)
def test_destroy_vm_denies_unsafe_vmid_before_api_mutation(monkeypatch, vmid, message):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "179")
    monkeypatch.setenv("VMID_RESERVED", "170,171,173")
    proxmox = _destruction_proxmox(vmid)
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match=message):
        proxmox_service.destroy_vm(vmid)

    proxmox.nodes("pve").qemu(vmid).delete.assert_not_called()


@pytest.mark.parametrize(
    ("pool", "message"),
    [
        ({"members": []}, "outside Proxmox pool"),
        (
            {"members": [{"type": "qemu", "vmid": 175, "name": "nexus-win11-auto-base"}]},
            "without a Nexus-owned name",
        ),
    ],
)
def test_destroy_vm_denies_non_owned_pool_resource(monkeypatch, pool, message):
    _configure(monkeypatch, full_clone=False)
    monkeypatch.setenv("VMID_POOL_START", "170")
    monkeypatch.setenv("VMID_POOL_END", "179")
    proxmox = _destruction_proxmox()
    proxmox.pools("nexus-labs").get.return_value = pool
    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)

    with pytest.raises(RuntimeError, match=message):
        proxmox_service.destroy_vm(175)

    proxmox.nodes("pve").qemu(175).delete.assert_not_called()


def test_start_vm_waits_for_start_task_and_confirms_running(monkeypatch):
    _configure(monkeypatch, full_clone=False)

    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.status.start.post.return_value = "UPID:start-task"
    vm.status.current.get.return_value = {"status": "running"}

    waiter = MagicMock()

    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)
    monkeypatch.setattr(proxmox_service, "_wait_for_task", waiter)

    proxmox_service.start_vm(175)

    vm.status.start.post.assert_called_once_with()
    waiter.assert_called_once_with(
        proxmox,
        "pve",
        "UPID:start-task",
        operation="start",
    )
    vm.status.current.get.assert_called_once_with()


def test_start_vm_fails_if_vm_is_not_running_after_task(monkeypatch):
    _configure(monkeypatch, full_clone=False)

    proxmox = MagicMock()
    vm = proxmox.nodes("pve").qemu(175)
    vm.status.start.post.return_value = "UPID:start-task"
    vm.status.current.get.return_value = {"status": "stopped"}

    monkeypatch.setattr(proxmox_service, "_get_proxmox", lambda: proxmox)
    monkeypatch.setattr(proxmox_service, "_wait_for_task", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="did not reach running state"):
        proxmox_service.start_vm(175)
