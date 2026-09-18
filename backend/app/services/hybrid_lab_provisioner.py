"""Fail-closed dispatch for approved hybrid-lab VM provisioners."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from typing import Any

from app.services import proxmox_service


Provisioner = Callable[..., dict[str, str] | None]


def _powershell(script: str) -> list[str]:
    return ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]


def _wait_for_marker(
    vmid: int,
    script: str,
    marker: str,
    *,
    attempts: int,
    delay: float,
) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            output = proxmox_service.guest_exec(
                vmid,
                _powershell(script),
                timeout=15,
            )
            if marker in output:
                return
        except (RuntimeError, TimeoutError) as exc:
            last_error = exc
        time.sleep(delay)

    raise TimeoutError(
        f"Windows guest did not reach required state: {marker}"
    ) from last_error


def _inc2504_printer_stale_ip(
    *,
    vmid: int,
    config: dict[str, Any],
) -> dict[str, str]:
    del config

    _wait_for_marker(
        vmid,
        """
if ((Get-LocalUser -Name 'labadmin' -ErrorAction SilentlyContinue) -and
    (Get-Process explorer -ErrorAction SilentlyContinue)) {
    'NEXUS_READY'
} else {
    'WAIT'
}
""",
        "NEXUS_READY",
        attempts=120,
        delay=2,
    )

    password = secrets.token_urlsafe(24)

    configure_script = f"""
$ErrorActionPreference = 'Stop'

$password = ConvertTo-SecureString '{password}' -AsPlainText -Force
Set-LocalUser -Name 'labadmin' -Password $password

$winlogon = 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon'
Set-ItemProperty $winlogon -Name AutoAdminLogon -Value '0'
Remove-ItemProperty $winlogon -Name AutoLogonCount -ErrorAction SilentlyContinue
Remove-ItemProperty $winlogon -Name DefaultPassword -ErrorAction SilentlyContinue
Remove-Item 'C:\\Windows\\System32\\Sysprep\\unattend.xml' -Force -ErrorAction SilentlyContinue

$adapter = Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }} | Select-Object -First 1
if (-not $adapter) {{ throw 'No active network adapter found' }}

Set-NetIPInterface -InterfaceIndex $adapter.ifIndex -Dhcp Disabled -ErrorAction SilentlyContinue
Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {{ $_.IPAddress -ne '10.10.10.10' }} |
    Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue

if (-not (Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -IPAddress '10.10.10.10' -ErrorAction SilentlyContinue)) {{
    New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress '10.10.10.10' -PrefixLength 24
}}

$badPort = 'IP_10.10.10.19'
if (-not (Get-PrinterPort -Name $badPort -ErrorAction SilentlyContinue)) {{
    Add-PrinterPort -Name $badPort -PrinterHostAddress '10.10.10.19' -PortNumber 9100
}}

if (-not (Get-Printer -Name 'Front Office Printer' -ErrorAction SilentlyContinue)) {{
    Add-Printer -Name 'Front Office Printer' -DriverName 'Universal Print Class Driver' -PortName $badPort
}} else {{
    Set-Printer -Name 'Front Office Printer' -PortName $badPort
}}

if ($env:COMPUTERNAME -ne 'NX-2504') {{
    Rename-Computer -NewName 'NX-2504' -Force
}}

'CONFIGURED'
"""

    configured = proxmox_service.guest_exec(
        vmid,
        _powershell(configure_script),
        timeout=120,
    )
    if "CONFIGURED" not in configured:
        raise RuntimeError("INC2504 configuration did not complete")

    try:
        proxmox_service.guest_exec(
            vmid,
            ["shutdown.exe", "/r", "/t", "0", "/f"],
            timeout=15,
        )
    except (RuntimeError, TimeoutError):
        pass

    _wait_for_marker(
        vmid,
        """
if ($env:COMPUTERNAME -eq 'NX-2504') {
    'NEXUS_REBOOT_READY'
} else {
    'WAIT'
}
""",
        "NEXUS_REBOOT_READY",
        attempts=90,
        delay=2,
    )

    verification = proxmox_service.guest_exec(
        vmid,
        _powershell(
            """
$ErrorActionPreference = 'Stop'

$winlogon = 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon'
Set-ItemProperty $winlogon -Name AutoAdminLogon -Value '0'
Remove-ItemProperty $winlogon -Name AutoLogonCount -ErrorAction SilentlyContinue
Remove-ItemProperty $winlogon -Name DefaultPassword -ErrorAction SilentlyContinue
Remove-ItemProperty $winlogon -Name ForceAutoLogon -ErrorAction SilentlyContinue
Remove-Item 'C:\\Windows\\System32\\Sysprep\\unattend.xml' -Force -ErrorAction SilentlyContinue

'HOSTNAME=' + $env:COMPUTERNAME

$ip = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -eq '10.10.10.10' } |
    Select-Object -First 1 -ExpandProperty IPAddress
'IP=' + $ip

$printer = Get-Printer -Name 'Front Office Printer'
'PRINTER=' + $printer.Name
'PRINTER_PORT=' + $printer.PortName

$state = Get-ItemProperty $winlogon
'AUTOLOGIN=' + $state.AutoAdminLogon
'UNATTEND_EXISTS=' + (Test-Path 'C:\\Windows\\System32\\Sysprep\\unattend.xml')
"""
        ),
        timeout=60,
    )

    actual = {
        line.strip()
        for line in verification.replace("\r", "").splitlines()
        if line.strip()
    }
    expected = {
        "HOSTNAME=NX-2504",
        "IP=10.10.10.10",
        "PRINTER=Front Office Printer",
        "PRINTER_PORT=IP_10.10.10.19",
        "AUTOLOGIN=0",
        "UNATTEND_EXISTS=False",
    }

    missing = expected - actual
    if missing:
        raise RuntimeError(
            "INC2504 final-state verification failed: "
            + ", ".join(sorted(missing))
        )

    return {"username": "labadmin", "password": password}


APPROVED_PROVISIONERS: dict[str, Provisioner] = {
    "inc2504_printer_stale_ip": _inc2504_printer_stale_ip,
}


def apply(
    handler: str,
    *,
    vmid: int,
    config: dict[str, Any],
) -> dict[str, str] | None:
    provisioner = APPROVED_PROVISIONERS.get(handler)
    if provisioner is None:
        raise RuntimeError(f"Unsupported VM provisioning handler: {handler}")
    return provisioner(vmid=vmid, config=config)
