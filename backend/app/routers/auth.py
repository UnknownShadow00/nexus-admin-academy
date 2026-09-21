from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import use_secure_cookies
from app.database import get_db
from app.models.student import Student
from app.services.auth_service import (
    STUDENT_SESSION_COOKIE,
    create_access_token,
    get_authenticated_student,
    hash_password,
    normalize_username,
    validate_new_password,
    verify_password,
)
from app.services.a_plus_access import get_a_plus_progress

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=1, max_length=128)
    confirm_password: str = Field(min_length=1, max_length=128)


def _student_payload(student: Student) -> dict:
    return {
        "sub": str(student.id),
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
        "av": student.auth_version,
        "must_change_password": bool(student.must_change_password),
    }


def _set_student_cookie(response: Response, token: str) -> None:
    secure_cookie = use_secure_cookies()
    response.set_cookie(
        key=STUDENT_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24,
        path="/",
    )


def _token_response(student: Student, response: Response | None = None) -> dict:
    token = create_access_token(_student_payload(student))
    if response is not None:
        _set_student_cookie(response, token)

    return {
        "access_token": token,
        "token_type": "bearer",
        "student_id": student.id,
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
        "must_change_password": bool(student.must_change_password),
    }


def _me_response(student: Student) -> dict:
    payload = {
        "student_id": student.id,
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
        "must_change_password": bool(student.must_change_password),
    }
    return {"success": True, "data": payload}


@router.post("/auth/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    student = db.query(Student).filter(func.lower(Student.username) == normalize_username(request.username)).first()
    if not student or not student.password_hash or not verify_password(request.password, student.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    from app.routers.capstones import has_unlocked_capstones

    payload = _token_response(student, response)
    if student.must_change_password:
        return payload
    payload["has_unlocked_capstones"] = has_unlocked_capstones(db, student)
    payload.update(get_a_plus_progress(db, student))
    return payload


@router.get("/auth/me")
def me(db: Session = Depends(get_db), current_student: Student = Depends(get_authenticated_student)):
    from app.routers.capstones import has_unlocked_capstones

    response = _me_response(current_student)
    if current_student.must_change_password:
        return response
    response["data"]["has_unlocked_capstones"] = has_unlocked_capstones(db, current_student)
    response["data"].update(get_a_plus_progress(db, current_student))
    return response


@router.post("/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_authenticated_student),
):
    if not current_student.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change is not required for this account",
        )
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    try:
        validate_new_password(request.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if current_student.password_hash and verify_password(request.new_password, current_student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the temporary password",
        )

    current_student.password_hash = hash_password(request.new_password)
    current_student.must_change_password = False
    current_student.auth_version += 1
    db.commit()
    db.refresh(current_student)
    return _token_response(current_student, response)


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=STUDENT_SESSION_COOKIE, path="/")
    return {"success": True, "data": {"authenticated": False}}
