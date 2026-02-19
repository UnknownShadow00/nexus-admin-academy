import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import load_env
from app.services.admin_auth import _clean_secret, _session_token

router = APIRouter(prefix="/api/admin/session", tags=["admin-session"])


class AdminLoginRequest(BaseModel):
    admin_key: str


@router.get("/status")
def admin_session_status(request: Request):
    load_env()
    expected = _clean_secret(os.getenv("ADMIN_SECRET_KEY"))
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_SECRET_KEY is not configured")

    token = _clean_secret(request.cookies.get("admin_session"))
    is_admin = bool(token and token == _session_token(expected))
    return {"success": True, "data": {"authenticated": is_admin}}


@router.post("/login")
def admin_session_login(payload: AdminLoginRequest, response: Response):
    load_env()
    expected = _clean_secret(os.getenv("ADMIN_SECRET_KEY"))
    provided = _clean_secret(payload.admin_key)

    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_SECRET_KEY is not configured")
    if not provided or provided != expected:
        raise HTTPException(status_code=403, detail="Unauthorized")

    expiry = datetime.now(timezone.utc) + timedelta(hours=12)
    response.set_cookie(
        key="admin_session",
        value=_session_token(expected),
        httponly=True,
        secure=False,
        samesite="lax",
        expires=int(expiry.timestamp()),
        max_age=60 * 60 * 12,
        path="/",
    )
    return {"success": True, "data": {"authenticated": True}}


@router.post("/logout")
def admin_session_logout(response: Response):
    response.delete_cookie(key="admin_session", path="/")
    return {"success": True, "data": {"authenticated": False}}

