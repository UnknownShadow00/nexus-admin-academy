from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.config import use_secure_cookies
from app.database import get_db
from app.models.student import Student, StudentAuthState
from app.services.auth_service import (
    STUDENT_SESSION_COOKIE,
    create_access_token,
    get_authenticated_student,
    get_current_student,
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


def _completed_token_response(student: Student, db: Session, response: Response) -> dict:
    from app.routers.capstones import has_unlocked_capstones

    payload = _token_response(student, response)
    payload["has_unlocked_capstones"] = has_unlocked_capstones(db, student)
    payload.update(get_a_plus_progress(db, student))
    return payload


def _rotate_forced_password(
    db: Session,
    *,
    student_id: int,
    expected_auth_version: int,
    password_hash: str,
) -> bool:
    """Atomically claim a required rotation before replacing its credential."""
    claimed = db.execute(
        update(StudentAuthState)
        .where(
            StudentAuthState.student_id == student_id,
            StudentAuthState.must_change_password.is_(True),
            StudentAuthState.auth_version == expected_auth_version,
        )
        .values(
            must_change_password=False,
            auth_version=expected_auth_version + 1,
        )
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        db.rollback()
        return False
    db.execute(
        update(Student)
        .where(Student.id == student_id)
        .values(password_hash=password_hash)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    db.expire_all()
    return True


@router.post("/auth/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    student = db.query(Student).filter(func.lower(Student.username) == normalize_username(request.username)).first()
    if not student or not student.password_hash or not verify_password(request.password, student.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if student.must_change_password:
        return _token_response(student, response)
    return _completed_token_response(student, db, response)


@router.get("/auth/me")
def me(db: Session = Depends(get_db), current_student: Student = Depends(get_authenticated_student)):
    from app.routers.capstones import has_unlocked_capstones

    response = _me_response(current_student)
    if current_student.must_change_password:
        return response
    response["data"]["has_unlocked_capstones"] = has_unlocked_capstones(db, current_student)
    response["data"].update(get_a_plus_progress(db, current_student))
    return response


@router.get("/auth/authorize", status_code=status.HTTP_204_NO_CONTENT)
def authorize(_current_student: Student = Depends(get_current_student)) -> Response:
    """Nginx auth_request target for application surfaces outside the SPA."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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

    expected_auth_version = current_student.auth_version
    if not _rotate_forced_password(
        db,
        student_id=current_student.id,
        expected_auth_version=expected_auth_version,
        password_hash=hash_password(request.new_password),
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password was already changed. Sign in again with the new password.",
        )
    return _completed_token_response(current_student, db, response)


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=STUDENT_SESSION_COOKIE, path="/")
    return {"success": True, "data": {"authenticated": False}}
