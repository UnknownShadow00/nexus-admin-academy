import pytest

from app.services import hybrid_lab_provisioner, proxmox_service


def test_inc2504_provisioner_configures_reboots_and_verifies(monkeypatch):
    commands = []
    monkeypatch.setattr(
        hybrid_lab_provisioner.secrets,
        "token_urlsafe",
        lambda _size: "temporary-lab-password",
    )

    outputs = iter([
        'WAIT',
        'NEXUS_READY',
        'CONFIGURED\r\n',
        '',
        'NEXUS_REBOOT_READY',
        (
            'HOSTNAME=NX-2504\r\n'
            'IP=10.10.10.10\r\n'
            'PRINTER=Front Office Printer\r\n'
            'PRINTER_PORT=IP_10.10.10.19\r\n'
            'AUTOLOGIN=0\r\n'
            'UNATTEND_EXISTS=False\r\n'
        ),
    ])

    def guest_exec(vmid, command, **kwargs):
        commands.append((vmid, command, kwargs))
        return next(outputs)

    monkeypatch.setattr(proxmox_service, 'guest_exec', guest_exec)
    monkeypatch.setattr(hybrid_lab_provisioner.time, 'sleep', lambda _seconds: None)

    credentials = hybrid_lab_provisioner.apply(
        'inc2504_printer_stale_ip',
        vmid=175,
        config={'handler': 'inc2504_printer_stale_ip'},
    )

    assert credentials == {
        'username': 'labadmin',
        'password': 'temporary-lab-password',
        'ip_address': '10.10.10.10',
    }

    assert all(vmid == 175 for vmid, _command, _kwargs in commands)
    assert any('shutdown.exe' in command for _vmid, command, _kwargs in commands)
    assert [
        kwargs["input_data"]
        for _vmid, _command, kwargs in commands
        if "input_data" in kwargs
    ] == ["temporary-lab-password"]

    combined = '\n'.join(
        ' '.join(command)
        for _vmid, command, _kwargs in commands
    )

    assert '10.10.10.10' in combined
    assert '10.10.10.19' in combined
    assert 'Front Office Printer' in combined
    assert 'NX-2504' in combined
    assert 'Panther' in combined
    assert 'unattend.xml' in combined
    assert 'temporary-lab-password' not in combined


def test_unknown_provisioner_fails_closed():
    with pytest.raises(RuntimeError, match='Unsupported VM provisioning handler'):
        hybrid_lab_provisioner.apply(
            'not-approved',
            vmid=175,
            config={'handler': 'not-approved'},
        )


@pytest.mark.parametrize(
    "config",
    [
        None,
        [],
        {},
        {"handler": 2504},
        {"handler": "different"},
        {"handler": "inc2504_printer_stale_ip", "script": "arbitrary"},
    ],
)
def test_inc2504_provisioner_rejects_invalid_metadata(config):
    with pytest.raises(RuntimeError, match="metadata|handler"):
        hybrid_lab_provisioner.apply(
            "inc2504_printer_stale_ip",
            vmid=175,
            config=config,
        )


def test_inc2504_provisioner_fails_closed_when_final_state_is_incomplete(monkeypatch):
    outputs = iter([
        "NEXUS_READY",
        "CONFIGURED\n",
        "",
        "NEXUS_REBOOT_READY",
        (
            "HOSTNAME=NX-2504\n"
            "IP=10.10.10.10\n"
            "PRINTER=Front Office Printer\n"
            "PRINTER_PORT=IP_10.10.10.19\n"
            "AUTOLOGIN=0\n"
        ),
    ])
    monkeypatch.setattr(
        proxmox_service,
        "guest_exec",
        lambda vmid, command, **kwargs: next(outputs),
    )

    with pytest.raises(RuntimeError, match="UNATTEND_EXISTS=False"):
        hybrid_lab_provisioner.apply(
            "inc2504_printer_stale_ip",
            vmid=175,
            config={"handler": "inc2504_printer_stale_ip"},
        )


def test_wait_for_marker_retries_temporary_guest_agent_unavailable(monkeypatch):
    class FakeResourceException(Exception):
        pass

    calls = {"count": 0}

    def guest_exec(vmid, command, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise FakeResourceException(
                "500 Internal Server Error: QEMU guest agent is not running"
            )
        return "NEXUS_REBOOT_READY"

    monkeypatch.setattr(
        hybrid_lab_provisioner,
        "ResourceException",
        FakeResourceException,
    )
    monkeypatch.setattr(proxmox_service, "guest_exec", guest_exec)
    monkeypatch.setattr(hybrid_lab_provisioner.time, "sleep", lambda _seconds: None)

    hybrid_lab_provisioner._wait_for_marker(
        175,
        "CHECK",
        "NEXUS_REBOOT_READY",
        attempts=2,
        delay=0,
    )

    assert calls["count"] == 2


def test_wait_for_marker_fails_closed_on_other_proxmox_error(monkeypatch):
    class FakeResourceException(Exception):
        pass

    def guest_exec(vmid, command, **kwargs):
        raise FakeResourceException("403 Permission check failed")

    monkeypatch.setattr(
        hybrid_lab_provisioner,
        "ResourceException",
        FakeResourceException,
    )
    monkeypatch.setattr(proxmox_service, "guest_exec", guest_exec)

    with pytest.raises(FakeResourceException, match="Permission check failed"):
        hybrid_lab_provisioner._wait_for_marker(
            175,
            "CHECK",
            "NEXUS_REBOOT_READY",
            attempts=2,
            delay=0,
        )


def test_inc2504_tolerates_guest_agent_loss_during_reboot(monkeypatch):
    class FakeResourceException(Exception):
        pass

    outputs = iter(
        [
            "NEXUS_READY",
            "CONFIGURED",
            "NEXUS_REBOOT_READY",
            (
                "HOSTNAME=NX-2504\n"
                "IP=10.10.10.10\n"
                "PRINTER=Front Office Printer\n"
                "PRINTER_PORT=IP_10.10.10.19\n"
                "AUTOLOGIN=0\n"
                "UNATTEND_EXISTS=False\n"
            ),
        ]
    )

    def guest_exec(_vmid, command, **_kwargs):
        if command[0] == "shutdown.exe":
            raise FakeResourceException(
                "500 Internal Server Error: QEMU guest agent is not running"
            )
        return next(outputs)

    monkeypatch.setattr(
        hybrid_lab_provisioner,
        "ResourceException",
        FakeResourceException,
    )
    monkeypatch.setattr(proxmox_service, "guest_exec", guest_exec)
    monkeypatch.setattr(hybrid_lab_provisioner.time, "sleep", lambda _seconds: None)

    credentials = hybrid_lab_provisioner.apply(
        "inc2504_printer_stale_ip",
        vmid=175,
        config={"handler": "inc2504_printer_stale_ip"},
    )

    assert credentials["ip_address"] == "10.10.10.10"
