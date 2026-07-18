import hmac
import logging
import os
import secrets
import time
from hashlib import sha256

from fastapi import Header, HTTPException, Request

from app.config import load_env

logger = logging.getLogger(__name__)


def _clean_secret(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("\"'").strip()


# Security fix (Part 9): admin sessions were sha256(password + constant) —
# deterministic, never expiring, derivable offline. Now each login issues a
# random token stored server-side with an expiry. Single-process store is
# appropriate for this deployment (one backend container, 1 mentor admin).
ADMIN_SESSION_TTL_SECONDS = int(os.getenv("ADMIN_SESSION_TTL_SECONDS", "43200"))  # 12h
_active_admin_sessions: dict[str, float] = {}


def issue_admin_session() -> str:
    token = secrets.token_urlsafe(32)
    _active_admin_sessions[token] = time.time() + ADMIN_SESSION_TTL_SECONDS
    return token


def revoke_admin_session(token: str) -> None:
    _active_admin_sessions.pop(_clean_secret(token), None)


def _session_token(secret: str) -> str:
    # retained for backward compatibility with any stored legacy cookie check
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
    cookie_token = _clean_secret(request.cookies.get("admin_session"))
    if not cookie_token:
        return False
    expiry = _active_admin_sessions.get(cookie_token)
    if expiry is None:
        return False
    if time.time() > expiry:
        _active_admin_sessions.pop(cookie_token, None)
        return False
    return True


def validate_admin_credentials(username: str, password: str) -> bool:
    expected_username = get_admin_username()
    expected_password = get_admin_password()
    if not (expected_username and expected_password):
        return False
    user_ok = hmac.compare_digest(_clean_secret(username), expected_username)
    pass_ok = hmac.compare_digest(_clean_secret(password), expected_password)
    return user_ok and pass_ok


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

    if header_key and expected_api_key and hmac.compare_digest(header_key, expected_api_key):
        return True

    if cookie_token and has_valid_admin_session(request):
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

    # Security fix (Part 9): previously ANY "Bearer <anything>" string passed.
    # Now the JWT must actually verify.
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from app.services.auth_service import decode_token
        try:
            decode_token(auth_header.removeprefix("Bearer ").strip())
            return True
        except Exception:
            pass

    # After a page refresh the frontend has no in-memory token — only the
    # httpOnly student_session cookie (same JWT get_current_student accepts).
    from app.services.auth_service import STUDENT_SESSION_COOKIE, decode_token
    cookie_token = request.cookies.get(STUDENT_SESSION_COOKIE)
    if cookie_token:
        try:
            decode_token(cookie_token)
            return True
        except Exception:
            pass

    raise HTTPException(status_code=401, detail="Unauthorized")
