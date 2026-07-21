import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-pytest")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# Force, don't setdefault: TestClient talks plain http, so a Secure cookie
# from the host env/.env would silently break every cookie-auth test.
os.environ["COOKIE_SECURE"] = "false"

import pytest  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: F401,E402 — registers all models with Base
from app.database import Base, get_db  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.services.auth_service import create_access_token, hash_password  # noqa: E402

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def _reset_schema():
    Base.metadata.create_all(_ENGINE)
    yield
    Base.metadata.drop_all(_ENGINE)


@pytest.fixture()
def db(_reset_schema):
    session = _Session()
    try:
        yield session
    finally:
        session.close()


def _override_get_db():
    session = _Session()
    try:
        yield session
    finally:
        session.close()


def make_client(*routers):
    app = FastAPI()

    @app.exception_handler(StarletteHTTPException)
    async def structured_prerequisite_handler(_: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and detail.get("code") == "PREREQUISITE_NOT_MET":
            return JSONResponse(status_code=exc.status_code, content=detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    for router in routers:
        app.include_router(router)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def make_student(db_session, username="student1", password="pass123"):
    student = Student(
        name="Test Student",
        email=f"{username}@test.local",
        username=username,
        password_hash=hash_password(password),
        total_xp=0,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


def auth_headers(student):
    token = create_access_token({
        "sub": str(student.id),
        "name": student.name,
        "email": student.email or "",
        "is_mentor": student.is_mentor,
    })
    return {"Authorization": f"Bearer {token}"}
