"""Run real Nexus APIs on a newly created disposable SQLite database.

Development only. No production DB, environment file, services or accounts.
Start the frontend separately with VITE_API_URL pointing to this loopback API.
"""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8018)
    parser.add_argument("--frontend-port", type=int, default=5188)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or not 1024 <= args.frontend_port <= 65535:
        parser.error("Choose unprivileged local ports")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", args.port))

    scratch = Path(tempfile.mkdtemp(prefix="nexus-academy-phase1-"))
    os.chmod(scratch, 0o700)
    credentials = {
        role: {"username": f"academy-preview-{role}", "password": secrets.token_urlsafe(18)}
        for role in ["v2", "legacy", "admin"]
    }
    os.environ.update({
        "APP_ENV": "development", "DATABASE_URL": f"sqlite:///{scratch / 'preview.db'}",
        "JWT_SECRET_KEY": secrets.token_urlsafe(48), "JWT_ALGORITHM": "HS256",
        "COOKIE_SECURE": "false", "AI_ENABLED": "false",
        "ADMIN_USERNAME": credentials["admin"]["username"], "ADMIN_PASSWORD": credentials["admin"]["password"],
        "ADMIN_SECRET_KEY": secrets.token_urlsafe(48), "ADMIN_API_KEY": secrets.token_urlsafe(48),
        "CORS_ORIGINS": f"http://127.0.0.1:{args.frontend_port}",
        "APP_LOG_PATH": str(scratch / "api.log"), "UPLOAD_DIR": str(scratch / "uploads"),
        "V2_CURRICULUM_ENABLED": "true", "V2_BEGINNER_PATH_ENABLED": "true",
    })
    backend = Path(__file__).resolve().parents[2] / "backend"
    sys.path.insert(0, str(backend))
    import app.models  # noqa: F401
    from app.database import Base, engine, SessionLocal
    from app.models.learning import Lesson
    from app.models.login_streak import LoginStreak
    from app.models.student import Student
    from app.models.training import TrainingWeek, TrainingWeekActivity
    from app.services.auth_service import hash_password
    from app.services.v2_content_loader import load_module
    from app.services.v2_interaction_loader import load_interactions
    from seed import seed_module0_and_methodology

    assert engine.url.database == str(scratch / "preview.db")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_module0_and_methodology(db)
        db.flush()
        lessons = db.query(Lesson).filter_by(status="published").order_by(Lesson.lesson_order).all()
        week = TrainingWeek(week_number=0, display_order=0, title="Nexus Orientation", is_active=True, requires_previous_week=False, learning_goals=[])
        db.add(week)
        db.flush()
        for i, lesson in enumerate(lessons):
            db.add(TrainingWeekActivity(training_week_id=week.id, stable_id=f"preview-orientation-{i}", activity_type="lesson", content_ref=str(lesson.id), display_order=i, is_required=True, estimated_minutes=lesson.estimated_minutes, metadata_json={}))
        load_module(db, commit=True)
        load_interactions(db, path=str(backend / "content/interactions/nexus-beginner-aplus-v1.yaml"), commit=True)
        for role in ["v2", "legacy"]:
            student = Student(name="Taylor Preview" if role == "v2" else "Morgan Preview", email=f"{role}@example.invalid", username=credentials[role]["username"], password_hash=hash_password(credentials[role]["password"]), total_xp=340 if role == "v2" else 0)
            db.add(student)
            db.flush()
            db.add(LoginStreak(student_id=student.id, current_streak=3 if role == "v2" else 1, longest_streak=5 if role == "v2" else 1, last_login=date.today() - timedelta(days=1)))
            credentials[role]["student_id"] = student.id
        db.commit()
    os.environ["V2_PILOT_STUDENT_IDS"] = str(credentials["v2"]["student_id"])
    credentials.update({"api": f"http://127.0.0.1:{args.port}", "frontend": f"http://127.0.0.1:{args.frontend_port}", "database": str(scratch / "preview.db")})
    path = scratch / "credentials.json"
    path.write_text(json.dumps(credentials, indent=2))
    os.chmod(path, 0o600)
    print(f"Disposable API: http://127.0.0.1:{args.port}\nFixture credentials: {path}", flush=True)
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
