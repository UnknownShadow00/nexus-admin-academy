import base64
import logging
import os
import secrets
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


def _lab_username(lab_run_id: int) -> str:
    return f"lab-run-{lab_run_id}"


def _upsert_user(settings: dict, admin_token: str, username: str, password: str) -> None:
    headers = {"Guacamole-Token": admin_token, "Content-Type": "application/json"}
    body = {"username": username, "password": password, "attributes": {}}
    resp = requests.post(
        f"{settings['url']}/api/session/data/{settings['datasource']}/users",
        json=body,
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 400:
        # User already exists — reset its password so we can issue a fresh token
        resp = requests.put(
            f"{settings['url']}/api/session/data/{settings['datasource']}/users/{username}",
            json=body,
            headers=headers,
            timeout=10,
        )
    resp.raise_for_status()


def get_student_token_url(conn_id: str, lab_run_id: int) -> str:
    """Create/refresh a per-lab-run Guacamole user with READ on only this
    connection and return a client URL authenticated as that user — never
    the Guacamole admin."""
    settings = _settings()
    admin_token = _get_token()
    username = _lab_username(lab_run_id)
    password = secrets.token_urlsafe(24)

    _upsert_user(settings, admin_token, username, password)

    headers = {"Guacamole-Token": admin_token, "Content-Type": "application/json"}
    patch = [{"op": "add", "path": f"/connectionPermissions/{conn_id}", "value": "READ"}]
    resp = requests.patch(
        f"{settings['url']}/api/session/data/{settings['datasource']}/users/{username}/permissions",
        json=patch,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()

    resp = requests.post(
        f"{settings['url']}/api/tokens",
        data={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    student_token = resp.json()["authToken"]

    encoded_b64 = _client_identifier(conn_id, settings["datasource"])
    return f"{settings['url']}/#/client/{encoded_b64}?token={student_token}"


def delete_lab_user(lab_run_id: int) -> None:
    settings = _settings()
    admin_token = _get_token()
    username = _lab_username(lab_run_id)
    resp = requests.delete(
        f"{settings['url']}/api/session/data/{settings['datasource']}/users/{username}",
        headers={"Guacamole-Token": admin_token},
        timeout=10,
    )
    if resp.status_code == 404:
        return
    resp.raise_for_status()
    logger.info("Deleted Guacamole lab user %s", username)


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
