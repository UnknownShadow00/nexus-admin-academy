"""Disposable Wave 4 browser fixture: loopback SQLite, V2 explicitly off."""

# Environment must be isolated before importing application modules.
# ruff: noqa: E402
import os
import secrets
import tempfile
from pathlib import Path

scratch = tempfile.TemporaryDirectory(prefix="nexus-wave4-browser-")
database_url = f"sqlite:///{Path(scratch.name) / 'browser.db'}"

os.environ.update(
    DATABASE_URL=database_url,
    JWT_SECRET_KEY=secrets.token_hex(32),
    COOKIE_SECURE="false",
    V2_CURRICULUM_ENABLED="false",
    V2_PILOT_STUDENT_IDS="",
    APP_LOG_PATH="/tmp/core-wave4-browser.log",
    ADMIN_API_KEY=secrets.token_hex(32),
    ADMIN_USERNAME="wave4-admin",
    ADMIN_PASSWORD=os.environ["WAVE4_PASSWORD"],
    ADMIN_SECRET_KEY=secrets.token_hex(32),
    CORS_ORIGINS=os.environ.get("WAVE4_FRONTEND_ORIGIN", "http://127.0.0.1:5190"),
)

import app.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import create_app
from app.models.quiz import Question, Quiz
from app.models.learning import Lesson
from app.models.student import Student
from app.services.auth_service import hash_password
from core_wave2_fixture import seed_beginner

engine = create_engine(database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
with Session() as db:
    for index in range(1, 5):
        db.add(
            Student(
                name=f"Wave 4 Learner {index}",
                username=f"wave4-learner-{index}",
                email=f"wave4-{index}@example.test",
                password_hash=hash_password(os.environ["WAVE4_PASSWORD"]),
                total_xp=0,
            )
        )
    db.commit()
    seed_beginner(db)
    orientation = db.get(Quiz, 42)
    first_lesson = db.query(Lesson).order_by(Lesson.id).first()
    practice = Quiz(
        id=99,
        title="Ticket Intake Practice Check",
        week_number=0,
        domain_id=orientation.domain_id,
        lesson_id=first_lesson.id,
        question_count=2,
        status="published",
        quiz_purpose="practice",
        is_required=False,
        show_in_weekly_checklist=False,
        show_in_practice_library=True,
        editorial_status="validated",
        answer_keys_validated=True,
        explanations_complete=True,
    )
    db.add(practice)
    db.flush()
    db.add_all(
        [
            Question(
                quiz_id=practice.id,
                question_text="Where should a technician record troubleshooting steps?",
                option_a="Progress notes",
                option_b="Requester name",
                correct_answer="A",
                explanation="Progress notes preserve the factual sequence of checks and observations.",
                tags=["ticket notes"],
            ),
            Question(
                quiz_id=practice.id,
                question_text="Which detail helps identify the affected workstation?",
                option_a="Device information",
                option_b="Expected resolution date",
                correct_answer="A",
                explanation="Device information ties the symptom and evidence to the affected workstation.",
                tags=["ticket intake"],
            ),
        ]
    )
    db.commit()

app = create_app()


def fixture_db():
    with Session() as db:
        yield db


app.dependency_overrides[get_db] = fixture_db
