import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PROXMOX_HOST = os.getenv("PROXMOX_HOST", "")
PROXMOX_TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID", "")
PROXMOX_TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET", "")
PROXMOX_NODE = os.getenv("PROXMOX_NODE", "pve")
VMID_POOL_START = int(os.getenv("VMID_POOL_START", "200"))
VMID_POOL_END = int(os.getenv("VMID_POOL_END", "299"))


def _get_proxmox():
    from proxmoxer import ProxmoxAPI
    return ProxmoxAPI(
        PROXMOX_HOST,
        user=PROXMOX_TOKEN_ID,
        token_value=PROXMOX_TOKEN_SECRET,
        verify_ssl=False,
    )


def _find_free_vmid(proxmox) -> int:
    existing = {int(vm["vmid"]) for vm in proxmox.cluster.resources.get(type="vm")}
    for vmid in range(VMID_POOL_START, VMID_POOL_END + 1):
        if vmid not in existing:
            return vmid
    raise RuntimeError("No free VMIDs available in pool")


def clone_template(template_vmid: int, name: str) -> int:
    proxmox = _get_proxmox()
    new_vmid = _find_free_vmid(proxmox)
    proxmox.nodes(PROXMOX_NODE).qemu(template_vmid).clone.post(
        newid=new_vmid,
        name=name,
        full=1,
    )
    logger.info("Cloned template %s → vmid %s (%s)", template_vmid, new_vmid, name)
    return new_vmid


def start_vm(vmid: int) -> None:
    proxmox = _get_proxmox()
    proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post()
    logger.info("Started VM %s", vmid)


def get_vm_ip(vmid: int, timeout: int = 120) -> Optional[str]:
    proxmox = _get_proxmox()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ifaces = proxmox.nodes(PROXMOX_NODE).qemu(vmid).agent("network-get-interfaces").get()
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
    try:
        proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.stop.post()
        time.sleep(3)
    except Exception:
        pass
    proxmox.nodes(PROXMOX_NODE).qemu(vmid).delete()
    logger.info("Destroyed VM %s", vmid)
