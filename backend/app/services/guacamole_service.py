"""Guacamole REST integration for isolated, per-assignment student access.

The administrator token is used only server-side to manage connections and
short-lived users.  Student-facing URLs always contain a token issued to a
temporary user with READ permission on one connection.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)
_CLIENT = httpx.Client(timeout=_TIMEOUT)


def _settings() -> dict:
    base_url = (os.getenv("GUACAMOLE_URL") or "").strip().rstrip("/")
    username = (
        os.getenv("GUACAMOLE_ADMIN_USERNAME") or os.getenv("GUACAMOLE_ADMIN_USER") or ""
    ).strip()
    password = os.getenv("GUACAMOLE_ADMIN_PASSWORD") or os.getenv("GUACAMOLE_ADMIN_PASS") or ""
    if not base_url or not username or not password:
        raise RuntimeError("Guacamole integration is not configured")
    return {
        "base_url": base_url,
        "username": username,
        "password": password,
        "datasource": (os.getenv("GUACAMOLE_DATASOURCE") or "postgresql").strip(),
    }


def _response_json(response: httpx.Response, operation: str) -> dict:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Guacamole {operation} failed with HTTP {response.status_code}") from exc
    try:
        value = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Guacamole {operation} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Guacamole {operation} returned an invalid response")
    return value


def _get_token(username: str, password: str) -> str:
    settings = _settings()
    response = _CLIENT.post(
        f"{settings['base_url']}/api/tokens",
        data={"username": username, "password": password},
    )
    token = _response_json(response, "authentication").get("authToken")
    if not token:
        raise RuntimeError("Guacamole authentication did not return a token")
    return str(token)


def _admin_token() -> str:
    settings = _settings()
    return _get_token(settings["username"], settings["password"])


def encode_client_identifier(connection_id: str, datasource: str = "postgresql") -> str:
    """Return Guacamole's unpadded base64url client identifier.

    Guacamole 1.6.0 builds this from ``id + NUL + 'c' + NUL + datasource``.
    """
    raw = f"{connection_id}\x00c\x00{datasource}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _api_url(resource: str) -> str:
    settings = _settings()
    return f"{settings['base_url']}/api/session/data/{quote(settings['datasource'], safe='')}/{resource}"


def create_connection(vm_ip: str, vmid: int) -> str:
    token = _admin_token()
    response = _CLIENT.post(
        _api_url("connections"),
        params={"token": token},
        json={
            "parentIdentifier": "ROOT",
            "name": f"Lab VM {vmid}",
            "protocol": "rdp",
            "parameters": {
                "hostname": vm_ip,
                "port": "3389",
                "ignore-cert": "true",
                "security": "any",
            },
            "attributes": {"max-connections": "1", "max-connections-per-user": "1"},
        },
    )
    identifier = _response_json(response, "connection creation").get("identifier")
    if not identifier:
        raise RuntimeError("Guacamole connection creation did not return an identifier")
    logger.info("Created Guacamole connection %s for VM %s", identifier, vmid)
    return str(identifier)


def delete_connection(connection_id: str) -> None:
    token = _admin_token()
    response = _CLIENT.delete(
        _api_url(f"connections/{quote(str(connection_id), safe='')}"),
        params={"token": token},
    )
    if response.status_code not in {200, 204, 404}:
        _response_json(response, "connection deletion")
    logger.info("Deleted Guacamole connection %s", connection_id)


def delete_user(username: str) -> None:
    if not username:
        return
    token = _admin_token()
    response = _CLIENT.delete(
        _api_url(f"users/{quote(username, safe='')}"),
        params={"token": token},
    )
    if response.status_code not in {200, 204, 404}:
        _response_json(response, "temporary user deletion")
    logger.info("Deleted temporary Guacamole user %s", username)


def create_scoped_access(connection_id: str, assignment_id: int, previous_username: str | None = None) -> dict:
    """Create one temporary user with READ access to exactly one connection."""
    if previous_username:
        delete_user(previous_username)

    settings = _settings()
    admin_token = _admin_token()
    username = f"lab-{assignment_id}-{secrets.token_hex(8)}"
    password = secrets.token_urlsafe(32)
    created = False
    try:
        response = _CLIENT.post(
            _api_url("users"),
            params={"token": admin_token},
            json={
                "username": username,
                "password": password,
                "disabled": False,
                "attributes": {"guac-full-name": f"Lab assignment {assignment_id}"},
            },
        )
        if response.status_code not in {200, 201, 204}:
            _response_json(response, "temporary user creation")
        created = True

        response = _CLIENT.patch(
            _api_url(f"users/{quote(username, safe='')}/permissions"),
            params={"token": admin_token},
            json=[{
                "op": "add",
                "path": f"/connectionPermissions/{connection_id}",
                "value": "READ",
            }],
        )
        if response.status_code not in {200, 204}:
            _response_json(response, "connection permission grant")

        student_token = _get_token(username, password)
        client_id = encode_client_identifier(str(connection_id), settings["datasource"])
        url = f"{settings['base_url']}/#/client/{client_id}?token={quote(student_token, safe='')}"
        logger.info("Issued scoped Guacamole access for assignment %s", assignment_id)
        return {"username": username, "url": url}
    except Exception:
        if created:
            try:
                delete_user(username)
            except Exception:
                logger.warning("Could not clean up temporary Guacamole user for assignment %s", assignment_id)
        raise
    finally:
        # Do not persist or log this credential. Rebinding limits its lifetime in
        # this frame; the temporary Guacamole account is deleted on refresh/end.
        password = ""
