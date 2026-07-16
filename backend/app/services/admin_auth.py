import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException, Request

from app.config import load_env

logger = logging.getLogger(__name__)

# Server-side admin session store. In-memory is fine for this deployment:
# single uvicorn worker, 1 admin. A restart logs the admin out, which is
# acceptable (12h sessions anyway).
_ADMIN_SESSIONS: dict[str, datetime] = {}
ADMIN_SESSION_TTL_HOURS = 12


def _clean_secret(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("\"'").strip()


def _prune_expired_sessions() -> None:
    now = datetime.now(timezone.utc)
    for token in [t for t, expiry in _ADMIN_SESSIONS.items() if expiry <= now]:
        del _ADMIN_SESSIONS[token]


def create_admin_session() -> str:
    _prune_expired_sessions()
    token = secrets.token_urlsafe(32)
    _ADMIN_SESSIONS[token] = datetime.now(timezone.utc) + timedelta(hours=ADMIN_SESSION_TTL_HOURS)
    return token


def revoke_admin_session(token: str | None) -> None:
    if token:
        _ADMIN_SESSIONS.pop(_clean_secret(token), None)


def is_valid_admin_session_token(token: str) -> bool:
    if not token:
        return False
    _prune_expired_sessions()
    # compare_digest over every stored token keeps the lookup constant-time
    return any(secrets.compare_digest(token, stored) for stored in _ADMIN_SESSIONS)


def get_admin_username() -> str:
    load_env()
    return _clean_secret(os.getenv("ADMIN_USERNAME"))


def get_admin_password() -> str:
    load_env()
    return _clean_secret(os.getenv("ADMIN_PASSWORD")) or _clean_secret(os.getenv("ADMIN_SECRET_KEY"))


def get_admin_api_key() -> str:
    load_env()
    return _clean_secret(os.getenv("ADMIN_API_KEY")) or _clean_secret(os.getenv("ADMIN_SECRET_KEY"))


def has_valid_admin_session(request: Request) -> bool:
    return is_valid_admin_session_token(_clean_secret(request.cookies.get("admin_session")))


def validate_admin_credentials(username: str, password: str) -> bool:
    expected_username = get_admin_username()
    expected_password = get_admin_password()
    return bool(
        expected_username
        and expected_password
        and secrets.compare_digest(_clean_secret(username), expected_username)
        and secrets.compare_digest(_clean_secret(password), expected_password)
    )


async def verify_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> bool:
    load_env()

    expected_api_key = get_admin_api_key()
    header_key = _clean_secret(
        x_admin_key
        or request.headers.get("X-Admin-Key")
        or request.headers.get("X-ADMIN-KEY")
    )
    cookie_token = _clean_secret(request.cookies.get("admin_session"))

    logger.info(
        "admin_auth_check path=%s mode=%s",
        request.url.path,
        "header" if header_key else ("cookie" if cookie_token else "none"),
    )

    if not expected_api_key and not get_admin_password():
        logger.error("admin_auth_missing_env path=%s", request.url.path)
        raise HTTPException(status_code=500, detail="Admin authentication is not configured")

    if header_key and expected_api_key and secrets.compare_digest(header_key, expected_api_key):
        return True

    if is_valid_admin_session_token(cookie_token):
        return True

    if header_key or cookie_token:
        logger.warning("admin_auth_invalid_key path=%s", request.url.path)

    raise HTTPException(status_code=403, detail="Unauthorized")


async def allow_admin_or_student(request: Request) -> bool:
    """Allow access if user has valid admin session OR valid student JWT."""
    # Check for admin session cookie
    if has_valid_admin_session(request):
        return True

    # Check for a student JWT — must actually decode, not just be present
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        from app.services.auth_service import STUDENT_SESSION_COOKIE

        token = request.cookies.get(STUDENT_SESSION_COOKIE) or ""
    if token:
        from app.services.auth_service import decode_token

        decode_token(token)  # raises 401 on invalid/expired tokens
        return True

    raise HTTPException(status_code=401, detail="Unauthorized")
