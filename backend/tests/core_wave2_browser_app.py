"""Disposable temporary SQLite fixture; serve on loopback with lifespan off."""

# Environment must be isolated before importing app.database or app.main.
# ruff: noqa: E402
import os
import secrets
import tempfile
from pathlib import Path

scratch = tempfile.TemporaryDirectory(prefix="nexus-wave2-browser-")
database_url = f"sqlite:///{Path(scratch.name) / 'browser.db'}"

os.environ.update(
    DATABASE_URL=database_url,
    JWT_SECRET_KEY=secrets.token_hex(32),
    COOKIE_SECURE="false",
    V2_CURRICULUM_ENABLED="false",
    V2_PILOT_STUDENT_IDS="",
    APP_LOG_PATH="/tmp/core-wave2-browser.log",
    ADMIN_API_KEY=secrets.token_hex(32),
    ADMIN_USERNAME="wave2-admin",
    ADMIN_PASSWORD=os.environ["WAVE2_PASSWORD"],
    ADMIN_SECRET_KEY=secrets.token_hex(32),
    CORS_ORIGINS="http://127.0.0.1:5187",
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models
from app.database import Base, get_db
from app.main import create_app
from app.models.student import Student
from core_wave2_fixture import seed_beginner
from app.services.auth_service import hash_password

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
with Session() as db:
    db.add(
        Student(
            name="Wave 2 Learner",
            username="wave2-learner",
            email="wave2@example.test",
            password_hash=hash_password(os.environ["WAVE2_PASSWORD"]),
            total_xp=0,
        )
    )
    db.commit()
    seed_beginner(db)
app = create_app()


def fixture_db():
    with Session() as db:
        yield db


app.dependency_overrides[get_db] = fixture_db
