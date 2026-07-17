import logging
import os
import time
from typing import Optional

from app.config import is_production_environment

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _settings() -> dict:
    host = (os.getenv("PROXMOX_HOST") or "").strip()
    token_id = (os.getenv("PROXMOX_TOKEN_ID") or "").strip()
    token_secret = (os.getenv("PROXMOX_TOKEN_SECRET") or "").strip()
    if not host or not token_id or not token_secret:
        raise RuntimeError("Proxmox integration is not configured")

    return {
        "host": host,
        "token_id": token_id,
        "token_secret": token_secret,
        "node": (os.getenv("PROXMOX_NODE") or "pve").strip(),
        "pool_start": int(os.getenv("VMID_POOL_START", "200")),
        "pool_end": int(os.getenv("VMID_POOL_END", "299")),
        "verify_ssl": _bool_env("PROXMOX_VERIFY_SSL", is_production_environment()),
    }


def _get_proxmox():
    from proxmoxer import ProxmoxAPI

    settings = _settings()
    return ProxmoxAPI(
        settings["host"],
        user=settings["token_id"],
        token_value=settings["token_secret"],
        verify_ssl=settings["verify_ssl"],
    )


def _find_free_vmid(proxmox) -> int:
    settings = _settings()
    existing = {int(vm["vmid"]) for vm in proxmox.cluster.resources.get(type="vm")}
    for vmid in range(settings["pool_start"], settings["pool_end"] + 1):
        if vmid not in existing:
            return vmid
    raise RuntimeError("No free VMIDs available in pool")


def clone_template(template_vmid: int, name: str) -> int:
    proxmox = _get_proxmox()
    settings = _settings()
    new_vmid = _find_free_vmid(proxmox)
    proxmox.nodes(settings["node"]).qemu(template_vmid).clone.post(
        newid=new_vmid,
        name=name,
        full=1,
    )
    logger.info("Cloned template %s -> vmid %s (%s)", template_vmid, new_vmid, name)
    return new_vmid


def start_vm(vmid: int) -> None:
    proxmox = _get_proxmox()
    settings = _settings()
    proxmox.nodes(settings["node"]).qemu(vmid).status.start.post()
    logger.info("Started VM %s", vmid)


def get_vm_ip(vmid: int, timeout: int = 120) -> Optional[str]:
    proxmox = _get_proxmox()
    settings = _settings()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ifaces = proxmox.nodes(settings["node"]).qemu(vmid).agent("network-get-interfaces").get()
            for iface in ifaces.get("result", []):
                if iface.get("name") == "lo":
                    continue
                for addr in iface.get("ip-addresses", []):
                    if addr.get("ip-address-type") == "ipv4":
                        ip = addr["ip-address"]
                        logger.info("VM %s IP: %s", vmid, ip)
                        return ip
        except Exception:
            pass
        time.sleep(5)
    logger.warning("Could not determine IP for VM %s after %ss", vmid, timeout)
    return None


def destroy_vm(vmid: int) -> None:
    proxmox = _get_proxmox()
    settings = _settings()
    try:
        proxmox.nodes(settings["node"]).qemu(vmid).status.stop.post()
        time.sleep(3)
    except Exception:
        pass
    proxmox.nodes(settings["node"]).qemu(vmid).delete()
    logger.info("Destroyed VM %s", vmid)
