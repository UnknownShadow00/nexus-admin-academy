import os
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.config import load_env
from app.database import get_db
from app.models.student import Student

def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}

try:
    from passlib.context import CryptContext
except ImportError:
    class CryptContext:
        def __init__(self, schemes=None, deprecated="auto"):
            self.schemes = schemes or []
            self.deprecated = deprecated

        def hash(self, plain: str) -> str:
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 390000)
            return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(digest)}"

        def verify(self, plain: str, hashed: str) -> bool:
            try:
                scheme, salt_b64, digest_b64 = hashed.split("$", 2)
            except ValueError:
                return False
            if scheme != "pbkdf2_sha256":
                return False
            salt = _b64url_decode(salt_b64)
            expected = _b64url_decode(digest_b64)
            actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 390000)
            return hmac.compare_digest(actual, expected)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
STUDENT_SESSION_COOKIE = "student_session"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def normalize_username(username: str) -> str:
    """Trim surrounding whitespace and Unicode-casefold a username.

    Used for case-insensitive matching; DB lookups pair this with SQL
    lower(), which agrees with casefold() for the ASCII usernames this
    platform seeds. Passwords are never normalized — they stay case-sensitive.
    """
    return (username or "").strip().casefold()


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def ensure_student_access(current_student: Student, student_id: int) -> None:
    if current_student.is_mentor or current_student.id == student_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    load_env()
    secret_key = os.environ["JWT_SECRET_KEY"]
    algorithm = os.environ["JWT_ALGORITHM"]
    if algorithm not in ALLOWED_JWT_ALGORITHMS:
        raise RuntimeError("JWT_ALGORITHM must be HS256, HS384, or HS512")
    expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def decode_token(token: str) -> dict:
    try:
        load_env()
        secret_key = os.environ["JWT_SECRET_KEY"]
        algorithm = os.environ["JWT_ALGORITHM"]
        if algorithm not in ALLOWED_JWT_ALGORITHMS:
            raise RuntimeError("JWT_ALGORITHM must be HS256, HS384, or HS512")
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except HTTPException:
        raise
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")


def get_current_student(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Student:
    token = token or request.cookies.get(STUDENT_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    try:
        student_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")
    return student
