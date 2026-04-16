from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import use_secure_cookies
from app.database import get_db
from app.models.student import Student
from app.services.admin_auth import (
    _clean_secret,
    _session_token,
    get_admin_session_secret,
    has_valid_admin_session,
    validate_admin_credentials,
)
from app.services.auth_service import create_access_token

router = APIRouter(prefix="/api/admin/session", tags=["admin-session"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.get("/status")
def admin_session_status(request: Request):
    session_secret = get_admin_session_secret()
    if not session_secret:
        raise HTTPException(status_code=500, detail="Admin session is not configured")
    return {"success": True, "data": {"authenticated": has_valid_admin_session(request)}}


@router.post("/login")
def admin_session_login(payload: AdminLoginRequest, response: Response):
    username = _clean_secret(payload.username)
    password = _clean_secret(payload.password)
    session_secret = get_admin_session_secret()

    if not session_secret:
        raise HTTPException(status_code=500, detail="Admin session is not configured")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if not validate_admin_credentials(username, password):
        raise HTTPException(status_code=403, detail="Unauthorized")

    expiry = datetime.now(timezone.utc) + timedelta(hours=12)
    secure_cookie = use_secure_cookies()
    response.set_cookie(
        key="admin_session",
        value=_session_token(session_secret),
        httponly=True,
        secure=secure_cookie,
        samesite="none" if secure_cookie else "lax",
        expires=int(expiry.timestamp()),
        max_age=60 * 60 * 12,
        path="/",
    )
    return {"success": True, "data": {"authenticated": True}}


@router.post("/logout")
def admin_session_logout(response: Response):
    response.delete_cookie(key="admin_session", path="/")
    return {"success": True, "data": {"authenticated": False}}


@router.get("/student-token")
def get_student_token(request: Request, db: Session = Depends(get_db)):
    """Admin endpoint: returns JWT token for a mentor to switch to student view."""
    if not has_valid_admin_session(request):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Get first mentor account
    mentor = db.query(Student).filter(Student.is_mentor == True).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="No mentor account found")

    # Create JWT token for the mentor
    payload = {
        "sub": str(mentor.id),
        "name": mentor.name,
        "email": mentor.email or "",
        "is_mentor": mentor.is_mentor,
    }
    token = create_access_token(payload)
    return {
        "success": True,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "student_id": mentor.id,
            "name": mentor.name,
        },
    }
