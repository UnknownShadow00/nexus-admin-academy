import base64
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def _settings() -> dict:
    url = (os.getenv("GUACAMOLE_URL") or "").strip().rstrip("/")
    admin_user = (os.getenv("GUACAMOLE_ADMIN_USER") or "guacadmin").strip()
    admin_pass = (os.getenv("GUACAMOLE_ADMIN_PASS") or "").strip()
    datasource = (os.getenv("GUACAMOLE_DATASOURCE") or "postgresql").strip()
    if not url or not admin_user or not admin_pass:
        raise RuntimeError("Guacamole integration is not configured")
    return {"url": url, "admin_user": admin_user, "admin_pass": admin_pass, "datasource": datasource}


def _get_token() -> str:
    settings = _settings()
    resp = requests.post(
        f"{settings['url']}/api/tokens",
        data={"username": settings["admin_user"], "password": settings["admin_pass"]},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["authToken"]


def create_connection(vm_ip: str, vmid: int, protocol: str = "rdp") -> Optional[str]:
    settings = _settings()
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
        f"{settings['url']}/api/session/data/{settings['datasource']}/connections",
        json=payload,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    conn_id = resp.json()["identifier"]
    logger.info("Created Guacamole connection %s for VM %s", conn_id, vmid)
    return conn_id


def _client_identifier(conn_id: str, datasource: str) -> str:
    # Guacamole client URLs encode base64("{identifier}\0c\0{datasource}")
    return base64.b64encode(f"{conn_id}\0c\0{datasource}".encode("utf-8")).decode("utf-8")


def get_token_url(conn_id: str) -> str:
    settings = _settings()
    token = _get_token()
    encoded_b64 = _client_identifier(conn_id, settings["datasource"])
    return f"{settings['url']}/#/client/{encoded_b64}?token={token}"


def delete_connection(conn_id: str) -> None:
    settings = _settings()
    token = _get_token()
    headers = {"Guacamole-Token": token}
    resp = requests.delete(
        f"{settings['url']}/api/session/data/{settings['datasource']}/connections/{conn_id}",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    logger.info("Deleted Guacamole connection %s", conn_id)
