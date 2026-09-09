"""Disposable Wave 3 browser fixture: loopback SQLite, V2 explicitly off."""

# Environment must be isolated before importing application modules.
# ruff: noqa: E402
import os
import secrets
import tempfile
from pathlib import Path

scratch = tempfile.TemporaryDirectory(prefix="nexus-wave3-browser-")
database_url = f"sqlite:///{Path(scratch.name) / 'browser.db'}"

os.environ.update(
    DATABASE_URL=database_url,
    JWT_SECRET_KEY=secrets.token_hex(32),
    COOKIE_SECURE="false",
    V2_CURRICULUM_ENABLED="false",
    V2_PILOT_STUDENT_IDS="",
    APP_LOG_PATH="/tmp/core-wave3-browser.log",
    ADMIN_API_KEY=secrets.token_hex(32),
    ADMIN_USERNAME="wave3-admin",
    ADMIN_PASSWORD=os.environ["WAVE3_PASSWORD"],
    ADMIN_SECRET_KEY=secrets.token_hex(32),
    CORS_ORIGINS=os.environ.get("WAVE3_FRONTEND_ORIGIN", "http://127.0.0.1:5188"),
)

import app.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import create_app
from app.models.student import Student
from app.services.auth_service import hash_password
from core_wave2_fixture import seed_beginner

engine = create_engine(database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
with Session() as db:
    for index in range(1, 4):
        db.add(
            Student(
                name=f"Wave 3 Learner {index}",
                username=f"wave3-learner-{index}",
                email=f"wave3-{index}@example.test",
                password_hash=hash_password(os.environ["WAVE3_PASSWORD"]),
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
