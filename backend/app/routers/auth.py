from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.services.auth_service import create_access_token, verify_password

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _token_response(student: Student) -> dict:
    payload = {
        "sub": str(student.id),
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
    }
    return {
        "access_token": create_access_token(payload),
        "token_type": "bearer",
        "student_id": student.id,
        "name": student.name,
    }


@router.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.username == request.username).first()
    if not student or not student.password_hash or not verify_password(request.password, student.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _token_response(student)
