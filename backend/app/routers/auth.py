from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import use_secure_cookies
from app.database import get_db
from app.models.student import Student
from app.services.auth_service import STUDENT_SESSION_COOKIE, create_access_token, get_current_student, verify_password

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _student_payload(student: Student) -> dict:
    return {
        "sub": str(student.id),
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
    }


def _set_student_cookie(response: Response, token: str) -> None:
    secure_cookie = use_secure_cookies()
    response.set_cookie(
        key=STUDENT_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite="none" if secure_cookie else "lax",
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
    }


def _me_response(student: Student) -> dict:
    payload = {
        "student_id": student.id,
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
    }
    return {"success": True, "data": payload}


@router.post("/auth/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.username == request.username).first()
    if not student or not student.password_hash or not verify_password(request.password, student.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _token_response(student, response)


@router.get("/auth/me")
def me(current_student: Student = Depends(get_current_student)):
    return _me_response(current_student)


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=STUDENT_SESSION_COOKIE, path="/")
    return {"success": True, "data": {"authenticated": False}}
