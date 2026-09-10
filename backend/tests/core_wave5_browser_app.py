"""Disposable Wave 5 browser fixture: six evidence states, V2 explicitly off."""

# Environment must be isolated before importing application modules.
# ruff: noqa: E402
import os
import secrets
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

scratch = tempfile.TemporaryDirectory(prefix="nexus-wave5-browser-")
database_url = f"sqlite:///{Path(scratch.name) / 'browser.db'}"

os.environ.update(
    DATABASE_URL=database_url,
    JWT_SECRET_KEY=secrets.token_hex(32),
    COOKIE_SECURE="false",
    V2_CURRICULUM_ENABLED="false",
    V2_PILOT_STUDENT_IDS="",
    APP_LOG_PATH="/tmp/core-wave5-browser.log",
    ADMIN_API_KEY=secrets.token_hex(32),
    ADMIN_USERNAME="wave5-admin",
    ADMIN_PASSWORD=os.environ["WAVE5_PASSWORD"],
    ADMIN_SECRET_KEY=secrets.token_hex(32),
    CORS_ORIGINS=os.environ.get("WAVE5_FRONTEND_ORIGIN", "http://127.0.0.1:5191"),
)

import app.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import create_app
from app.models.flashcard import FlashcardReview
from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskAttemptGrade,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.auth_service import hash_password
from core_wave2_fixture import seed_beginner

engine = create_engine(database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def assessment_results(quiz: Quiz, *, correct: bool) -> list[dict]:
    rows = []
    for position, question in enumerate(sorted(quiz.questions, key=lambda row: row.id)):
        chosen = question.correct_answer if correct else "B"
        rows.append(
            {
                "question_id": question.id,
                "question_number": position + 1,
                "question_text": question.question_text,
                "student_answer": chosen,
                "student_answer_text": getattr(question, f"option_{chosen.lower()}")
                or "",
                "correct_answer": question.correct_answer,
                "correct_answers": question.all_correct_answers,
                "correct_answer_text": getattr(
                    question, f"option_{question.correct_answer.lower()}"
                )
                or "",
                "is_multi_select": question.is_multi_select,
                "is_correct": correct,
                "explanation": question.explanation or "",
                "concepts": question.tags or [],
                "options": {
                    letter: value
                    for letter in "ABCDEFGH"
                    if (value := getattr(question, f"option_{letter.lower()}"))
                },
                "passing_percentage": 70,
            }
        )
    return rows


with Session() as db:
    for index in range(1, 7):
        db.add(
            Student(
                name=f"Wave 5 Learner {index}",
                username=f"wave5-learner-{index}",
                email=f"wave5-{index}@example.test",
                password_hash=hash_password(os.environ["WAVE5_PASSWORD"]),
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
    guided_lab = LabTemplate(
        id=990,
        title="Guided ticket triage",
        description="Practice triage with procedural guidance.",
        lab_type="legacy",
        week_number=1,
        is_published=True,
    )
    db.add(guided_lab)
    week_one = db.query(TrainingWeek).filter_by(week_number=1).one()
    db.add(
        TrainingWeekActivity(
            training_week_id=week_one.id,
            stable_id="wave5-guided-triage",
            activity_type="guided_lab",
            content_ref=str(guided_lab.id),
            display_order=9,
            is_required=True,
            metadata_json={"learning_role": "practice", "assistance_level": "guided"},
        )
    )
    db.commit()

    students = {
        index: db.query(Student).filter_by(username=f"wave5-learner-{index}").one()
        for index in range(1, 7)
    }
    lessons = db.query(Lesson).order_by(Lesson.id).all()

    # B: lesson complete only; E: practice only.
    db.add(
        StudentLessonProgress(
            student_id=students[2].id,
            lesson_id=first_lesson.id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        QuizAttempt(
            student_id=students[5].id,
            quiz_id=practice.id,
            answers={"checked_question_ids": []},
            results=[],
            score=0,
            xp_awarded=0,
            best_score=0,
            first_attempt_xp=0,
            status="practice_complete",
            submitted_at=datetime.now(timezone.utc),
        )
    )

    # C: failed assessment; D: failed then passed.
    for learner, passed_history in ((3, (False,)), (4, (False, True))):
        db.add(
            StudentLessonProgress(
                student_id=students[learner].id,
                lesson_id=first_lesson.id,
                completed_at=datetime.now(timezone.utc),
            )
        )
        for correct in passed_history:
            db.add(
                QuizAttempt(
                    student_id=students[learner].id,
                    quiz_id=orientation.id,
                    answers={},
                    results=assessment_results(orientation, correct=correct),
                    score=len(orientation.questions) if correct else 0,
                    xp_awarded=0,
                    best_score=len(orientation.questions) if correct else 0,
                    first_attempt_xp=0,
                    status="submitted",
                    submitted_at=datetime.now(timezone.utc),
                )
            )
        db.add(
            FlashcardReview(
                student_id=students[learner].id,
                question_id=orientation.questions[0].id,
                due_date=date.today(),
                last_wrong_answer="B",
            )
        )

    # F: completed orientation, guided lab evidence, and one passed Service Desk assessment.
    for lesson in lessons:
        db.add(
            StudentLessonProgress(
                student_id=students[6].id,
                lesson_id=lesson.id,
                completed_at=datetime.now(timezone.utc),
            )
        )
    db.add(
        QuizAttempt(
            student_id=students[6].id,
            quiz_id=orientation.id,
            answers={},
            results=assessment_results(orientation, correct=True),
            score=len(orientation.questions),
            xp_awarded=0,
            best_score=len(orientation.questions),
            first_attempt_xp=0,
            status="submitted",
            submitted_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        LabRun(
            student_id=students[6].id,
            lab_template_id=guided_lab.id,
            status="submitted",
            submitted_at=datetime.now(timezone.utc),
        )
    )
    scenario = ServiceDeskScenario(
        stable_key="wave5-printer-ticket",
        title="Printer queue incident",
        description="Troubleshoot a printer queue.",
        category="hardware",
        difficulty=1,
        status="active",
    )
    db.add(scenario)
    db.flush()
    version = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=1,
        definition_json={},
        definition_hash="5" * 64,
        validation_status="valid",
        status="published",
        published_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.flush()
    attempt = ServiceDeskAttempt(
        student_id=students[6].id,
        scenario_version_id=version.id,
        mode="simulation",
        experience_mode="assessment",
        status="completed",
        current_state={},
        current_state_hash="6" * 64,
        state_version=1,
        attempt_number=1,
        completed_at=datetime.now(timezone.utc),
        score=90,
        passed=True,
    )
    db.add(attempt)
    db.flush()
    db.add(
        ServiceDeskAttemptGrade(
            attempt_id=attempt.id,
            scenario_version_id=version.id,
            rubric_version="wave5-fixture",
            technical_complete=True,
            critical_failure=False,
            overall_score=90,
            passed=True,
            feedback_summary="Passed the stored rubric.",
            details_json={},
        )
    )
    db.commit()

app = create_app()


def fixture_db():
    with Session() as db:
        yield db


app.dependency_overrides[get_db] = fixture_db
