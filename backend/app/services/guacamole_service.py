import os
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

GUACAMOLE_URL = os.getenv("GUACAMOLE_URL", "")
GUACAMOLE_ADMIN_USER = os.getenv("GUACAMOLE_ADMIN_USER", "guacadmin")
GUACAMOLE_ADMIN_PASS = os.getenv("GUACAMOLE_ADMIN_PASS", "")


def _get_token() -> str:
    resp = requests.post(
        f"{GUACAMOLE_URL}/api/tokens",
        data={"username": GUACAMOLE_ADMIN_USER, "password": GUACAMOLE_ADMIN_PASS},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["authToken"]


def create_connection(vm_ip: str, vmid: int, protocol: str = "rdp") -> Optional[str]:
    token = _get_token()
    headers = {"Guacamole-Token": token, "Content-Type": "application/json"}

    payload = {
        "name": f"lab-vm-{vmid}",
        "protocol": protocol,
        "parameters": {
            "hostname": vm_ip,
            "port": "3389" if protocol == "rdp" else "22",
            "ignore-cert": "true",
        },
        "attributes": {},
    }

    resp = requests.post(
        f"{GUACAMOLE_URL}/api/session/data/postgresql/connections",
        json=payload,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    conn_id = resp.json()["identifier"]
    logger.info("Created Guacamole connection %s for VM %s", conn_id, vmid)
    return conn_id


def get_token_url(conn_id: str) -> str:
    token = _get_token()
    encoded = f"c/{conn_id}"
    import base64
    encoded_b64 = base64.b64encode(encoded.encode()).decode()
    return f"{GUACAMOLE_URL}/#/client/{encoded_b64}?token={token}"


def delete_connection(conn_id: str) -> None:
    token = _get_token()
    headers = {"Guacamole-Token": token}
    resp = requests.delete(
        f"{GUACAMOLE_URL}/api/session/data/postgresql/connections/{conn_id}",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("Deleted Guacamole connection %s", conn_id)
