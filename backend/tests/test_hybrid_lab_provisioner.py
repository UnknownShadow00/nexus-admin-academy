from unittest.mock import call

import pytest

from app.services import hybrid_lab_provisioner, proxmox_service


def test_inc2504_provisioner_configures_reboots_and_verifies(monkeypatch):
    commands = []

    monkeypatch.setattr(
        hybrid_lab_provisioner.secrets,
        'token_urlsafe',
        lambda _size: 'temporary-lab-password',
    )

    outputs = iter([
        'WAIT',
        'NEXUS_READY',
        'CONFIGURED',
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
        commands.append((vmid, command))
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
    }

    assert all(vmid == 175 for vmid, _command in commands)
    assert any('shutdown.exe' in command for _vmid, command in commands)

    combined = '\n'.join(
        ' '.join(command)
        for _vmid, command in commands
    )

    assert '10.10.10.10' in combined
    assert '10.10.10.19' in combined
    assert 'Front Office Printer' in combined
    assert 'NX-2504' in combined


def test_unknown_provisioner_fails_closed():
    with pytest.raises(RuntimeError, match='Unsupported VM provisioning handler'):
        hybrid_lab_provisioner.apply(
            'not-approved',
            vmid=175,
            config={'handler': 'not-approved'},
        )
