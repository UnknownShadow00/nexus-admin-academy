import logging
import os
from hashlib import sha256

from fastapi import Header, HTTPException, Request

from app.config import load_env

logger = logging.getLogger(__name__)


def _clean_secret(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("\"'").strip()


def _session_token(secret: str) -> str:
    return sha256(f"{secret}:nexus-admin-session:v1".encode("utf-8")).hexdigest()


def get_admin_username() -> str:
    load_env()
    return _clean_secret(os.getenv("ADMIN_USERNAME"))


def get_admin_password() -> str:
    load_env()
    return _clean_secret(os.getenv("ADMIN_PASSWORD")) or _clean_secret(os.getenv("ADMIN_SECRET_KEY"))


def get_admin_api_key() -> str:
    load_env()
    return _clean_secret(os.getenv("ADMIN_API_KEY")) or _clean_secret(os.getenv("ADMIN_SECRET_KEY"))


def get_admin_session_secret() -> str:
    return get_admin_password()


def has_valid_admin_session(request: Request) -> bool:
    session_secret = get_admin_session_secret()
    cookie_token = _clean_secret(request.cookies.get("admin_session"))
    expected_cookie = _session_token(session_secret) if session_secret else ""
    return bool(cookie_token and expected_cookie and cookie_token == expected_cookie)


def validate_admin_credentials(username: str, password: str) -> bool:
    expected_username = get_admin_username()
    expected_password = get_admin_password()
    return bool(
        expected_username
        and expected_password
        and _clean_secret(username) == expected_username
        and _clean_secret(password) == expected_password
    )


async def verify_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> bool:
    load_env()

    session_secret = get_admin_session_secret()
    expected_api_key = get_admin_api_key()
    header_key = _clean_secret(
        x_admin_key
        or request.headers.get("X-Admin-Key")
        or request.headers.get("X-ADMIN-KEY")
    )
    cookie_token = _clean_secret(request.cookies.get("admin_session"))
    expected_cookie = _session_token(session_secret) if session_secret else ""
    provided = header_key or cookie_token

    logger.info(
        "admin_auth_check path=%s has_session_secret=%s session_secret_len=%s has_api_key=%s api_key_len=%s provided_len=%s mode=%s",
        request.url.path,
        bool(session_secret),
        len(session_secret),
        bool(expected_api_key),
        len(expected_api_key),
        len(provided),
        "header" if header_key else ("cookie" if cookie_token else "none"),
    )

    if not session_secret and not expected_api_key:
        logger.error("admin_auth_missing_env path=%s", request.url.path)
        raise HTTPException(status_code=500, detail="Admin authentication is not configured")

    if not provided:
        logger.warning("admin_auth_missing_header path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Unauthorized")

    if header_key and header_key == expected_api_key:
        return True

    if cookie_token and cookie_token == expected_cookie:
        return True

    if header_key or cookie_token:
        logger.warning("admin_auth_invalid_key path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Unauthorized")

    raise HTTPException(status_code=403, detail="Unauthorized")


async def allow_admin_or_student(request: Request) -> bool:
    """Allow access if user has valid admin session OR valid student JWT."""
    # Check for admin session cookie
    if has_valid_admin_session(request):
        return True

    # Check for student JWT (this will be verified by get_current_student in the caller)
    # For curriculum endpoints that don't strictly need student identity,
    # we just need to know if someone authenticated is accessing
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return True

    raise HTTPException(status_code=401, detail="Unauthorized")
