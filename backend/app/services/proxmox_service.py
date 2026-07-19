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
        "full_clone": _bool_env("PROXMOX_FULL_CLONE", False),
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


def _template_storage_types(proxmox, node: str, template_vmid: int) -> set[str]:
    config = proxmox.nodes(node).qemu(template_vmid).config.get()
    volume_storages = {
        value.split(":", 1)[0]
        for key, value in config.items()
        if key.startswith(("scsi", "sata", "virtio", "ide")) and isinstance(value, str) and ":" in value
    }
    storage_rows = proxmox.nodes(node).storage.get()
    return {str(row.get("type", "")) for row in storage_rows if row.get("storage") in volume_storages}


def _linked_clone_supported(proxmox, node: str, template_vmid: int) -> bool:
    storage_types = _template_storage_types(proxmox, node, template_vmid)
    return bool(storage_types) and storage_types.issubset({"lvmthin", "zfspool", "rbd", "btrfs"})


def _wait_for_task(proxmox, node: str, upid: str | None, timeout: int = 300) -> None:
    if not upid:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = proxmox.nodes(node).tasks(upid).status.get()
        if status.get("status") == "stopped":
            if status.get("exitstatus") != "OK":
                raise RuntimeError(f"Proxmox clone task failed: {status.get('exitstatus', 'unknown error')}")
            return
        time.sleep(2)
    raise TimeoutError("Proxmox clone task did not finish before the timeout")


def clone_template(template_vmid: int, name: str) -> int:
    proxmox = _get_proxmox()
    settings = _settings()
    new_vmid = _find_free_vmid(proxmox)
    full_clone = settings["full_clone"]
    if not full_clone:
        try:
            linked_supported = _linked_clone_supported(proxmox, settings["node"], template_vmid)
        except Exception:
            linked_supported = False
            logger.warning(
                "Could not verify linked-clone support for template %s; falling back to full clone",
                template_vmid,
            )
        else:
            if not linked_supported:
                logger.warning(
                    "Template %s storage does not support linked clones; falling back to full clone",
                    template_vmid,
                )
        if not linked_supported:
            full_clone = True

    mode = "full" if full_clone else "linked"
    try:
        upid = proxmox.nodes(settings["node"]).qemu(template_vmid).clone.post(
            newid=new_vmid,
            name=name,
            full=1 if full_clone else 0,
        )
        _wait_for_task(proxmox, settings["node"], upid)
    except Exception as exc:
        raise RuntimeError(f"Proxmox {mode} clone failed for template {template_vmid}") from exc
    logger.info("Cloned template %s -> vmid %s using %s clone", template_vmid, new_vmid, mode)
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
