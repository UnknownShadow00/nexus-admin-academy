import logging
import os

from fastapi import Header, HTTPException, Request

from app.config import load_env

logger = logging.getLogger(__name__)


def _clean_secret(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().strip("\"'").strip()


async def verify_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> bool:
    load_env()

    expected = _clean_secret(os.getenv("ADMIN_SECRET_KEY"))
    provided = _clean_secret(
        x_admin_key
        or request.headers.get("X-Admin-Key")
        or request.headers.get("X-ADMIN-KEY")
    )

    logger.info(
        "admin_auth_check path=%s has_expected=%s expected_len=%s expected_prefix=%s provided_len=%s provided_prefix=%s",
        request.url.path,
        bool(expected),
        len(expected),
        expected[:8] if expected else "",
        len(provided),
        provided[:8] if provided else "",
    )

    if not expected:
        logger.error("admin_auth_missing_env path=%s", request.url.path)
        raise HTTPException(status_code=500, detail="ADMIN_SECRET_KEY is not configured")

    if not provided:
        logger.warning("admin_auth_missing_header path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Unauthorized")

    if provided != expected:
        logger.warning("admin_auth_invalid_key path=%s", request.url.path)
        raise HTTPException(status_code=403, detail="Unauthorized")

    return True
