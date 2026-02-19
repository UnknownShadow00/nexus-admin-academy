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


async def verify_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> bool:
    load_env()

    expected = _clean_secret(os.getenv("ADMIN_SECRET_KEY"))
    header_key = _clean_secret(
        x_admin_key
        or request.headers.get("X-Admin-Key")
        or request.headers.get("X-ADMIN-KEY")
    )
    cookie_token = _clean_secret(request.cookies.get("admin_session"))
    expected_cookie = _session_token(expected) if expected else ""
    provided = header_key or cookie_token

    logger.info(
        "admin_auth_check path=%s has_expected=%s expected_len=%s provided_len=%s mode=%s",
        request.url.path,
        bool(expected),
        len(expected),
        len(provided),
        "header" if header_key else ("cookie" if cookie_token else "none"),
    )

    if not expected:
        logger.error("admin_auth_missing_env path=%s", request.url.path)
        raise HTTPException(status_code=500, detail="ADMIN_SECRET_KEY is not configured")

    if not provided:
        logger.warning("admin_auth_missing_header path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Unauthorized")

    if header_key and header_key == expected:
        return True

    if cookie_token and cookie_token == expected_cookie:
        return True

    if header_key or cookie_token:
        logger.warning("admin_auth_invalid_key path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Unauthorized")

    raise HTTPException(status_code=403, detail="Unauthorized")
