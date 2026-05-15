import os
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import load_env
from app.database import get_db
from app.models.student import Student

def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


try:
    from jose import JWTError, jwt
except ImportError:
    class JWTError(Exception):
        pass

    class _FallbackJWT:
        @staticmethod
        def encode(payload: dict, secret_key: str, algorithm: str = "HS256") -> str:
            if algorithm != "HS256":
                raise JWTError("Unsupported algorithm")
            header = {"alg": algorithm, "typ": "JWT"}
            prepared = dict(payload)
            if isinstance(prepared.get("exp"), datetime):
                prepared["exp"] = int(prepared["exp"].timestamp())
            header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
            payload_segment = _b64url_encode(json.dumps(prepared, separators=(",", ":")).encode("utf-8"))
            signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
            signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
            return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"

        @staticmethod
        def decode(token: str, secret_key: str, algorithms: list[str]) -> dict:
            if "HS256" not in algorithms:
                raise JWTError("Unsupported algorithm")
            try:
                header_segment, payload_segment, signature_segment = token.split(".")
            except ValueError as exc:
                raise JWTError("Invalid token") from exc

            signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
            expected_signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
            provided_signature = _b64url_decode(signature_segment)
            if not hmac.compare_digest(expected_signature, provided_signature):
                raise JWTError("Invalid signature")

            payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
            exp = payload.get("exp")
            if exp is not None and int(exp) <= int(datetime.now(timezone.utc).timestamp()):
                raise JWTError("Token expired")
            return payload

    jwt = _FallbackJWT()

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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        if "sub" not in payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
        return payload
    except HTTPException:
        raise
    except (JWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")


def get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Student:
    payload = decode_token(token)
    try:
        student_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")
    return student
