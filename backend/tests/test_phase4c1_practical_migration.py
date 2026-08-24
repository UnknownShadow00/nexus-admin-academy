import json
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.lab import LabRun, LabTemplate
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.windows_ad_server_practical import restore_pre_4c1_practical_labs


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION_0058 = "0058_intune_endpoint_management"
REVISION_0059 = "0059_windows_ad_server_practical_upgrade"
TARGET_WEEKS = (3, 5, 6, 7, 13, 14, 15, 16, 17)


def _run(command: list[str], database_url: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "JWT_SECRET_KEY": "phase4c1-migration-test-secret-at-least-32-bytes",
            "COOKIE_SECURE": "false",
        }
    )
    subprocess.run(command, cwd=BACKEND_ROOT, env=environment, capture_output=True, check=True, text=True)


def _seed(database_url: str) -> None:
    _run([sys.executable, "seed.py"], database_url)
    _run([sys.executable, "seed_curriculum.py"], database_url)


def _target_identity(database_path: Path) -> list[tuple]:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        rows = db.execute(
            select(TrainingWeek, TrainingWeekActivity, LabTemplate)
            .join(TrainingWeekActivity, TrainingWeekActivity.training_week_id == TrainingWeek.id)
            .join(
                LabTemplate,
                (TrainingWeekActivity.activity_type == "guided_lab")
                & (TrainingWeekActivity.content_ref == LabTemplate.id.cast(TrainingWeekActivity.content_ref.type)),
            )
            .where(TrainingWeek.week_number.in_(TARGET_WEEKS))
            .order_by(TrainingWeek.week_number)
        ).all()
        return [
            (
                week.week_number,
                activity.stable_id,
                activity.content_ref,
                activity.is_required,
                (activity.metadata_json or {}).get("learning_role", "practice"),
                lab.id,
                lab.title,
                lab.lab_type,
                (lab.success_criteria or {}).get("evidence_case_workbench", {}).get("domain"),
            )
            for week, activity, lab in rows
        ]


def _active_totals(database_path: Path) -> tuple[int, int, int]:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        module_count = db.query(TrainingWeek).filter_by(is_active=True).count()
        activities = (
            db.query(TrainingWeekActivity)
            .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
            .filter(TrainingWeek.is_active.is_(True))
            .all()
        )
        return module_count, len(activities), sum(activity.is_required for activity in activities)


def _active_role_counts(database_path: Path) -> dict[str, int]:
    defaults = {
        "lesson": "learn",
        "video": "learn",
        "quiz": "check",
        "review": "check",
        "guided_lab": "practice",
        "networking_lab": "practice",
        "command_exercise": "practice",
        "terminal_exercise": "practice",
        "support_ticket": "troubleshoot",
        "service_desk_scenario": "troubleshoot",
        "capstone": "prove",
    }
    counts = {role: 0 for role in ("learn", "check", "practice", "troubleshoot", "prove")}
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        activities = (
            db.query(TrainingWeekActivity)
            .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
            .filter(TrainingWeek.is_active.is_(True))
        )
        for activity in activities:
            role = (activity.metadata_json or {}).get("learning_role", defaults[activity.activity_type])
            counts[role] += 1
    return counts


def test_phase4c1_fresh_and_historical_paths_converge_without_identity_churn(tmp_path):
    fresh_path = tmp_path / "fresh.db"
    fresh_url = f"sqlite:///{fresh_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0059], fresh_url)
    _seed(fresh_url)

    historical_path = tmp_path / "historical.db"
    historical_url = f"sqlite:///{historical_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0058], historical_url)
    _seed(historical_url)

    historical_engine = create_engine(historical_url)
    with Session(historical_engine) as db:
        restore_pre_4c1_practical_labs(db)
        before = {
            week.week_number: (activity.id, activity.stable_id, activity.content_ref, lab.id)
            for week, activity, lab in db.execute(
                select(TrainingWeek, TrainingWeekActivity, LabTemplate)
                .join(TrainingWeekActivity, TrainingWeekActivity.training_week_id == TrainingWeek.id)
                .join(
                    LabTemplate,
                    (TrainingWeekActivity.activity_type == "guided_lab")
                    & (TrainingWeekActivity.content_ref == LabTemplate.id.cast(TrainingWeekActivity.content_ref.type)),
                )
                .where(TrainingWeek.week_number.in_(TARGET_WEEKS))
            )
        }
        student = Student(
            name="Historical Student",
            email="phase4c1-history@example.test",
            username="phase4c1-history",
            password_hash="not-a-real-hash",
        )
        db.add(student)
        db.flush()
        completed = LabRun(
            lab_template_id=15,
            student_id=student.id,
            status="submitted",
            final_score=100,
            notes=json.dumps(
                {
                    "issue": "Historical completion",
                    "evidence": "Recorded before upgrade",
                    "action": "Completed old lab",
                    "verification": "Passed",
                }
            ),
        )
        db.add(completed)
        db.commit()
        historical_run_id = completed.id

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0059], historical_url)

    with Session(historical_engine) as db:
        after = {
            week.week_number: (activity.id, activity.stable_id, activity.content_ref, lab.id)
            for week, activity, lab in db.execute(
                select(TrainingWeek, TrainingWeekActivity, LabTemplate)
                .join(TrainingWeekActivity, TrainingWeekActivity.training_week_id == TrainingWeek.id)
                .join(
                    LabTemplate,
                    (TrainingWeekActivity.activity_type == "guided_lab")
                    & (TrainingWeekActivity.content_ref == LabTemplate.id.cast(TrainingWeekActivity.content_ref.type)),
                )
                .where(TrainingWeek.week_number.in_(TARGET_WEEKS))
            )
        }
        run = db.get(LabRun, historical_run_id)
        assert run is not None
        assert (run.lab_template_id, run.status, run.final_score) == (15, "submitted", 100)
        assert before == after

    assert _target_identity(fresh_path) == _target_identity(historical_path)
    assert _active_totals(fresh_path) == _active_totals(historical_path) == (35, 320, 143)
    assert _active_role_counts(fresh_path) == {
        "learn": 216,
        "check": 38,
        "practice": 29,
        "troubleshoot": 31,
        "prove": 6,
    }


def test_phase4c1_downgrade_and_reupgrade_restore_only_owned_content(tmp_path):
    database_path = tmp_path / "cycle.db"
    database_url = f"sqlite:///{database_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0059], database_url)
    _seed(database_url)
    upgraded_identity = _target_identity(database_path)

    _run([sys.executable, "-m", "alembic", "downgrade", REVISION_0058], database_url)
    engine = create_engine(database_url)
    with Session(engine) as db:
        gpo = db.get(LabTemplate, 5)
        powershell = db.get(LabTemplate, 14)
        recovery = db.get(LabTemplate, 15)
        assert gpo.lab_type == "structured_cli"
        assert gpo.success_criteria["required_commands"] == ["whoami", "gpresult /r", "gpupdate /force"]
        assert powershell.lab_type == "structured_cli"
        assert powershell.success_criteria["required_commands"] == ["get-command", "get-help get-service", "get-service"]
        assert recovery.lab_type == "structured_operations"
        target_activities = db.query(TrainingWeekActivity).filter(
            TrainingWeekActivity.content_ref.in_([str(item) for item in (3, 5, 7, 8, 9, 12, 13, 14, 15)]),
            TrainingWeekActivity.activity_type == "guided_lab",
        )
        assert all("learning_role" not in (activity.metadata_json or {}) for activity in target_activities)

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0059], database_url)
    assert _target_identity(database_path) == upgraded_identity
    assert _active_totals(database_path) == (35, 320, 143)
