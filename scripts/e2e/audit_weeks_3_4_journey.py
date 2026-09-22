"""Prove the legacy Weeks 1-4 journey against an isolated, fully seeded DB.

The script deliberately refuses non-SQLite and the repository's nexus.db. It
creates progress only in the caller-provided throwaway database.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException

from app.database import SessionLocal
from app.models.cli_lab import CliLabAttempt
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabRun
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import Quiz, QuizAttempt
from app.models.service_desk import (
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.auth_service import hash_password
from app.services.progression_service import derive_current_week, require_week_reached
from app.services.service_desk_progression import (
    build_service_desk_progression,
    scenario_access,
)
from app.services.training_service import (
    build_training_overview,
    build_training_week,
    network_cli_gate_is_unlocked,
)


def _assert_isolated_database() -> Path:
    database_url = os.environ.get("DATABASE_URL", "")
    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite" or not parsed.path:
        raise SystemExit("Refusing to run: DATABASE_URL must point to a throwaway SQLite file.")
    target = Path(parsed.path).resolve()
    production = (Path(__file__).resolve().parents[2] / "backend" / "nexus.db").resolve()
    if target == production:
        raise SystemExit("Refusing to run against backend/nexus.db.")
    return target


def _required_activities(db, week_number: int) -> list[TrainingWeekActivity]:
    week = db.query(TrainingWeek).filter_by(week_number=week_number).one()
    return (
        db.query(TrainingWeekActivity)
        .filter_by(training_week_id=week.id, is_required=True)
        .order_by(TrainingWeekActivity.display_order, TrainingWeekActivity.id)
        .all()
    )


def _complete_activity(db, student: Student, activity: TrainingWeekActivity) -> None:
    now = datetime.now(timezone.utc)
    ref = activity.content_ref
    if activity.activity_type == "lesson":
        db.add(
            StudentLessonProgress(
                student_id=student.id,
                lesson_id=int(ref),
                completed_at=now,
            )
        )
    elif activity.activity_type == "video":
        video = db.get(CurriculumVideo, int(ref))
        db.add(VideoWatch(student_id=student.id, video_key=video.video_key))
    elif activity.activity_type == "quiz":
        quiz = db.get(Quiz, int(ref))
        total = max(1, len(quiz.questions), int(quiz.question_count or 0))
        db.add(
            QuizAttempt(
                student_id=student.id,
                quiz_id=quiz.id,
                answers={},
                results=[],
                score=total,
                best_score=total,
                xp_awarded=0,
                first_attempt_xp=0,
            )
        )
    elif activity.activity_type == "guided_lab":
        db.add(
            LabRun(
                student_id=student.id,
                lab_template_id=int(ref),
                status="submitted",
                submitted_at=now,
                final_score=100,
                structured_feedback={"journey_audit": True},
            )
        )
    elif activity.activity_type == "networking_lab":
        db.add(
            CliLabAttempt(
                student_id=student.id,
                lab_id=ref,
                completed_at=now,
                command_log=[{"audit": "completed"}],
            )
        )
    elif activity.activity_type == "service_desk_scenario":
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=ref).one()
        version = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id, status="published")
            .order_by(ServiceDeskScenarioVersion.version_number.desc())
            .first()
        )
        attempt_number = (
            db.query(ServiceDeskAttempt)
            .filter_by(student_id=student.id, scenario_version_id=version.id)
            .count()
            + 1
        )
        db.add(
            ServiceDeskAttempt(
                student_id=student.id,
                scenario_version_id=version.id,
                mode="simulation",
                experience_mode="assessment",
                status="completed",
                current_state={},
                current_state_hash="0" * 64,
                state_version=1,
                attempt_number=attempt_number,
                completed_at=now,
                score=100,
                passed=True,
            )
        )
    else:
        raise AssertionError(f"Unhandled required activity: {activity.activity_type}")
    db.commit()


def _complete_week(db, student: Student, week_number: int) -> list[str]:
    completed = []
    for activity in _required_activities(db, week_number):
        _complete_activity(db, student, activity)
        completed.append(f"{activity.activity_type}:{activity.content_ref}")
    return completed


def main() -> None:
    target = _assert_isolated_database()
    db = SessionLocal()
    try:
        username = os.environ.get(
            "NEXUS_E2E_W34_USERNAME",
            f"weeks-3-4-journey-{int(datetime.now().timestamp())}",
        )
        password = os.environ.get(
            "NEXUS_E2E_W34_PASSWORD", "DisposableJourney!2026"
        )
        student = Student(
            name="Disposable Weeks 3-4 Journey",
            email=f"{username}@example.invalid",
            username=username,
            password_hash=hash_password(password),
            total_xp=0,
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        checkpoints = []
        assert derive_current_week(student.id, db) == 0
        for week_number in (0, 1, 2):
            completed = _complete_week(db, student, week_number)
            reached = derive_current_week(student.id, db)
            assert reached == week_number + 1
            checkpoints.append(
                {"completed_week": week_number, "now_at": reached, "activities": completed}
            )

        week_three = build_training_week(db, student, 3)
        week_three_roles = defaultdict(list)
        for item in week_three["activities"]:
            week_three_roles[item["learning_role"]].append(item["title"])
        assert any(item["content_ref"] == "3" for item in week_three["activities"])
        before_learning = scenario_access(
            build_service_desk_progression(db, student), "inc2501"
        )
        assert before_learning["unlocked"] is False

        for activity in _required_activities(db, 3):
            if activity.activity_type == "service_desk_scenario":
                access = scenario_access(
                    build_service_desk_progression(db, student), activity.content_ref
                )
                assert access["unlocked"] is True
            _complete_activity(db, student, activity)
        assert derive_current_week(student.id, db) == 4

        week_four = build_training_week(db, student, 4)
        week_four_roles = defaultdict(list)
        for item in week_four["activities"]:
            week_four_roles[item["learning_role"]].append(item["title"])
        assert set(week_four_roles["practice"]) == {"Prioritize the Queue"}
        assert set(week_four_roles["troubleshoot"]) == {
            "Work the Queue: Three Tickets"
        }
        completed_week_four = _complete_week(db, student, 4)
        assert derive_current_week(student.id, db) == 5

        overview = build_training_overview(db, student)
        network_plus_week = next(
            week for week in overview["weeks"] if week["week_number"] == 9
        )
        assert network_plus_week["status"] == "locked"
        assert network_cli_gate_is_unlocked(db, student) is False
        hybrid = scenario_access(build_service_desk_progression(db, student), "inc2504")
        assert hybrid["unlocked"] is False
        try:
            require_week_reached(db, student, 9)
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("Future Network+ week unexpectedly bypassed its gate")

        print(
            json.dumps(
                {
                    "database": str(target),
                    "student_id": student.id,
                    "username": student.username,
                    "checkpoints": checkpoints,
                    "week_3_roles": dict(week_three_roles),
                    "week_4_roles": dict(week_four_roles),
                    "week_4_completed": completed_week_four,
                    "after_week_4": derive_current_week(student.id, db),
                    "network_plus_locked": True,
                    "hybrid_inc2504_locked": True,
                },
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
