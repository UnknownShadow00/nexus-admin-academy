"""Disposable temporary SQLite fixture; serve on loopback with lifespan off."""

# Environment must be isolated before importing app.database or app.main.
# ruff: noqa: E402
import os
import secrets
import tempfile
from pathlib import Path

scratch = tempfile.TemporaryDirectory(prefix="nexus-wave1-browser-")
database_url = f"sqlite:///{Path(scratch.name) / 'browser.db'}"

os.environ.update(
    DATABASE_URL=database_url,
    JWT_SECRET_KEY=secrets.token_hex(32),
    COOKIE_SECURE="false",
    V2_CURRICULUM_ENABLED="false",
    V2_PILOT_STUDENT_IDS="",
    APP_LOG_PATH="/tmp/core-wave1-browser.log",
    ADMIN_API_KEY=secrets.token_hex(32),
    ADMIN_USERNAME="wave1-admin",
    ADMIN_PASSWORD=os.environ["WAVE1_PASSWORD"],
    ADMIN_SECRET_KEY=secrets.token_hex(32),
    CORS_ORIGINS="http://127.0.0.1:5187",
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.models
from app.database import Base, get_db
from app.main import create_app
from app.models.student import Student
from app.models.quiz import Quiz, Question
from app.models.training import TrainingWeek, TrainingWeekActivity
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
            name="Wave 1 Learner",
            username="wave1-learner",
            email="wave1@example.test",
            password_hash=hash_password(os.environ["WAVE1_PASSWORD"]),
            total_xp=0,
        )
    )
    week = TrainingWeek(
        week_number=0,
        display_order=0,
        title="Wave 1 local evidence",
        learning_goals=[],
        requires_previous_week=False,
    )
    db.add(week)
    db.flush()
    for total in (4, 2, 6):
        quiz = Quiz(
            title=f"Truth quiz {total}",
            week_number=0,
            question_count=total,
            status="published",
            editorial_status="validated",
            answer_keys_validated=True,
            is_required=True,
            show_in_weekly_checklist=True,
        )
        db.add(quiz)
        db.flush()
        for i in range(total):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    question_text=f"Question {i + 1}",
                    option_a="Correct",
                    option_b="Wrong",
                    correct_answer="A",
                    explanation="The fixture answer is A.",
                )
            )
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"wave1-quiz-{total}",
                activity_type="quiz",
                content_ref=str(quiz.id),
                display_order=total,
                is_required=True,
            )
        )
    db.commit()
app = create_app()


def fixture_db():
    with Session() as db:
        yield db


app.dependency_overrides[get_db] = fixture_db
