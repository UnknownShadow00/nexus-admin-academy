import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.models.cli_lab import CliLabAttempt
from app.models.lab import LabRun, LabTemplate
from app.models.progression import Role, StudentRole
from app.models.quiz import QuizAttempt
from app.models.student import Student
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.training_service import build_training_week


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
PRODUCTION_BASELINE_COMMIT = "c6212e6994f624a7883b0f2cd9036eaa0d6421a2"
PRE_MICROSOFT_WORKPLACE_COMMIT = "0966389e036ecde65564d508fba1bdebd1c347e5"
REVISION_0059 = "0059_windows_ad_server_practical_upgrade"
REVISION_0060 = "0060_network_linux_cloud_practical_upgrade"
TARGETS = {8: 2, 11: 10, 12: 11, 18: 16, 19: 17, 20: 18, 22: 20}


def _run(command: list[str], database_url: str, cwd: Path = BACKEND_ROOT) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": database_url,
            "JWT_SECRET_KEY": "phase4c2-migration-test-secret-at-least-32-bytes",
            "COOKIE_SECURE": "false",
        }
    )
    subprocess.run(command, cwd=cwd, env=environment, capture_output=True, check=True, text=True)


def _seed(database_url: str, cwd: Path = BACKEND_ROOT) -> None:
    _run([sys.executable, "seed.py"], database_url, cwd)
    _run([sys.executable, "seed_curriculum.py"], database_url, cwd)


def _archived_backend(tmp_path: Path, commit: str, name: str) -> Path:
    check = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if check.returncode != 0:
        pytest.skip(f"historical commit {commit} is not reachable")

    source_root = tmp_path / name
    source_root.mkdir()
    archive_path = tmp_path / f"{name}.tar"
    with archive_path.open("wb") as archive_file:
        subprocess.run(
            ["git", "archive", commit, "backend"],
            cwd=REPO_ROOT,
            stdout=archive_file,
            check=True,
        )
    with tarfile.open(archive_path) as archive:
        archive.extractall(source_root, filter="data")
    return source_root / "backend"


def _build_historical_0059(tmp_path: Path, database_url: str) -> None:
    """Reproduce the production lineage instead of fresh-seeding at 0059.

    IDs 19-25 arose after the original curriculum was already populated. A
    fresh seed using the 0059 checkout is therefore not historical and is the
    exact identity-drift path this phase repairs. Seed at the pinned pre-4B.1
    commit, then upgrade that populated database with the pinned 0059 source.
    """
    lineage_backend = _archived_backend(
        tmp_path,
        PRE_MICROSOFT_WORKPLACE_COMMIT,
        "pre_microsoft_workplace_source",
    )
    baseline_backend = _archived_backend(
        tmp_path,
        PRODUCTION_BASELINE_COMMIT,
        "production_0059_source",
    )
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], database_url, lineage_backend)
    _seed(database_url, lineage_backend)
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], database_url, baseline_backend)
    _seed(database_url, baseline_backend)


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
            .where(TrainingWeek.week_number.in_(TARGETS))
            .order_by(TrainingWeek.week_number)
        ).all()
        return [
            (
                week.week_number,
                activity.id,
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


def _canonical_target_state(database_path: Path) -> list[tuple]:
    """Fresh databases cannot share auto-increment activity PKs with the
    production file, so convergence is measured by durable stable identity,
    content identity, role, and authored case state. Historical-path tests
    separately assert that the real production activity PKs do not change."""
    return [item[:1] + item[2:] for item in _target_identity(database_path)]


def _active_totals(database_path: Path) -> tuple[int, int, int, int]:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        activities = (
            db.query(TrainingWeekActivity)
            .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
            .filter(TrainingWeek.is_active.is_(True))
            .all()
        )
        required = sum(activity.is_required for activity in activities)
        return (
            db.query(TrainingWeek).filter_by(is_active=True).count(),
            len(activities),
            required,
            len(activities) - required,
        )


def _role_counts(database_path: Path) -> dict[str, int]:
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


def _week_21_required_videos(database_path: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        week = db.query(TrainingWeek).filter_by(week_number=21).one()
        return {
            row.content_ref
            for row in db.query(TrainingWeekActivity).filter_by(
                training_week_id=week.id,
                activity_type="video",
                is_required=True,
            )
        }


def _owned_0059_state(database_path: Path) -> tuple[list[tuple], list[tuple]]:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        labs = []
        for week_number, lab_id in TARGETS.items():
            lab = db.get(LabTemplate, lab_id)
            week = db.query(TrainingWeek).filter_by(week_number=week_number).one()
            activity = db.query(TrainingWeekActivity).filter_by(
                training_week_id=week.id,
                activity_type="guided_lab",
                content_ref=str(lab_id),
            ).one()
            labs.append(
                (
                    week_number,
                    lab.id,
                    lab.title,
                    lab.description,
                    lab.lab_type,
                    lab.difficulty,
                    lab.estimated_minutes,
                    lab.is_published,
                    lab.environment_requirements,
                    lab.setup_instructions,
                    lab.success_criteria,
                    lab.required_evidence,
                    lab.hints,
                    activity.id,
                    activity.stable_id,
                    activity.is_required,
                    activity.estimated_minutes,
                    activity.metadata_json,
                )
            )
        week_21 = db.query(TrainingWeek).filter_by(week_number=21).one()
        videos = [
            (row.id, row.stable_id, row.content_ref, row.is_required, row.metadata_json)
            for row in db.query(TrainingWeekActivity)
            .filter(
                TrainingWeekActivity.training_week_id == week_21.id,
                TrainingWeekActivity.activity_type == "video",
                TrainingWeekActivity.content_ref.in_(["54", "55", "56"]),
            )
            .order_by(TrainingWeekActivity.content_ref)
        ]
        return labs, videos


def _activity_identity(database_path: Path, week_number: int, activity_type: str, content_ref: str) -> tuple:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        week = db.query(TrainingWeek).filter_by(week_number=week_number).one()
        row = db.query(TrainingWeekActivity).filter_by(
            training_week_id=week.id,
            activity_type=activity_type,
            content_ref=content_ref,
        ).one()
        return row.id, row.stable_id, row.content_ref


def _legacy_network_template_count(database_path: Path) -> int:
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        return db.query(LabTemplate).filter_by(title="Troubleshoot a Network Connectivity Scenario").count()


def test_phase4c2_historical_0059_lineage_and_fresh_paths_converge_without_identity_or_progress_churn(tmp_path):
    fresh_path = tmp_path / "fresh.db"
    fresh_url = f"sqlite:///{fresh_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], fresh_url)
    _seed(fresh_url)

    historical_path = tmp_path / "historical.db"
    historical_url = f"sqlite:///{historical_path}"
    _build_historical_0059(tmp_path, historical_url)
    original_owned_0059_state = _owned_0059_state(historical_path)
    original_week_9_identity = _activity_identity(historical_path, 9, "guided_lab", "1")
    original_legacy_network_count = _legacy_network_template_count(historical_path)

    # Current application code may be deployed before the migration is run.
    # A deliberate 0059 pin must keep 0059 lab definitions and requirement
    # flags even when the current seed entrypoint is invoked.
    _seed(historical_url)
    with Session(create_engine(historical_url)) as db:
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == REVISION_0059
        assert "evidence_case_workbench" not in (db.get(LabTemplate, 2).success_criteria or {})
    assert _owned_0059_state(historical_path) == original_owned_0059_state

    historical_engine = create_engine(historical_url)
    with Session(historical_engine) as db:
        assert db.execute(select(TrainingWeekActivity)).scalars().all()
        before_identity = _target_identity(historical_path)
        student = Student(
            name="Phase 4C.2 Historical Student",
            email="phase4c2-history@example.test",
            username="phase4c2-history",
            password_hash="not-a-real-hash",
            total_xp=725,
        )
        db.add(student)
        db.flush()
        role = db.query(Role).order_by(Role.rank_order).first()
        student.current_role_id = role.id
        student_role = StudentRole(
            student_id=student.id,
            role_id=role.id,
            promotion_notes="Historical role award",
        )
        quiz_attempt = QuizAttempt(
            student_id=student.id,
            quiz_id=23,
            answers={"historical": "answer"},
            score=88,
            xp_awarded=25,
            best_score=88,
            first_attempt_xp=25,
        )
        run = LabRun(
            lab_template_id=18,
            student_id=student.id,
            status="submitted",
            final_score=100,
            structured_feedback={"score_pct": 100, "questions": []},
            submitted_at=datetime(2026, 8, 1, tzinfo=UTC),
            notes="Historical Linux completion",
        )
        cli_attempt = CliLabAttempt(
            student_id=student.id,
            lab_id="dev-sw-act-23",
            completed_at=datetime(2026, 8, 2, tzinfo=UTC),
            xp_awarded=50,
            command_log=[{"cmd": "show vlan brief"}],
        )
        video_key = db.execute(
            select(TrainingWeekActivity.content_ref).join(TrainingWeek).where(
                TrainingWeek.week_number == 21,
                TrainingWeekActivity.activity_type == "video",
                TrainingWeekActivity.content_ref == "54",
            )
        ).scalar_one()
        from app.models.curriculum_video import CurriculumVideo

        video = db.get(CurriculumVideo, int(video_key))
        watch = VideoWatch(student_id=student.id, video_key=video.video_key)
        db.add_all([run, cli_attempt, watch, student_role, quiz_attempt])
        db.commit()
        progress_ids = (student.id, run.id, cli_attempt.id, watch.id, student_role.id, quiz_attempt.id, role.id)
        assert next(
            item
            for item in build_training_week(db, student, 20)["activities"]
            if item["content_ref"] == "18" and item["activity_type"] == "guided_lab"
        )["complete"] is True

    drift_path = tmp_path / "partial-history.db"
    shutil.copy2(historical_path, drift_path)
    drift_url = f"sqlite:///{drift_path}"
    drift_engine = create_engine(drift_url)
    with Session(drift_engine) as db:
        week_11 = db.query(TrainingWeek).filter_by(week_number=11).one()
        db.query(TrainingWeekActivity).filter_by(
            training_week_id=week_11.id,
            activity_type="guided_lab",
            content_ref="10",
        ).delete()
        original_week_8_type = db.get(LabTemplate, 2).lab_type
        db.commit()
    with pytest.raises(subprocess.CalledProcessError):
        _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], drift_url)
    with Session(drift_engine) as db:
        assert db.get(LabTemplate, 2).lab_type == original_week_8_type == "structured_cli"

    video_drift_path = tmp_path / "partial-video-history.db"
    shutil.copy2(historical_path, video_drift_path)
    video_drift_url = f"sqlite:///{video_drift_path}"
    video_drift_engine = create_engine(video_drift_url)
    with Session(video_drift_engine) as db:
        week_21 = db.query(TrainingWeek).filter_by(week_number=21).one()
        db.query(TrainingWeekActivity).filter_by(
            training_week_id=week_21.id,
            activity_type="video",
            content_ref="56",
        ).delete()
        original_week_8_type = db.get(LabTemplate, 2).lab_type
        video_54 = db.query(TrainingWeekActivity).filter_by(
            training_week_id=week_21.id,
            activity_type="video",
            content_ref="54",
        ).one()
        assert video_54.is_required is True
        db.commit()
    with pytest.raises(subprocess.CalledProcessError):
        _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], video_drift_url)
    with Session(video_drift_engine) as db:
        week_21 = db.query(TrainingWeek).filter_by(week_number=21).one()
        video_54 = db.query(TrainingWeekActivity).filter_by(
            training_week_id=week_21.id,
            activity_type="video",
            content_ref="54",
        ).one()
        assert db.get(LabTemplate, 2).lab_type == original_week_8_type == "structured_cli"
        assert video_54.is_required is True

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], historical_url)
    with Session(historical_engine) as db:
        student = db.get(Student, progress_ids[0])
        run = db.get(LabRun, progress_ids[1])
        cli_attempt = db.get(CliLabAttempt, progress_ids[2])
        watch = db.get(VideoWatch, progress_ids[3])
        student_role = db.get(StudentRole, progress_ids[4])
        quiz_attempt = db.get(QuizAttempt, progress_ids[5])
        assert (student.total_xp, run.lab_template_id, run.status, run.final_score) == (725, 18, "submitted", 100)
        assert student.current_role_id == progress_ids[6]
        assert (student_role.role_id, student_role.promotion_notes) == (progress_ids[6], "Historical role award")
        assert (quiz_attempt.quiz_id, quiz_attempt.score, quiz_attempt.xp_awarded) == (23, 88, 25)
        assert (cli_attempt.lab_id, cli_attempt.completed_at is not None, cli_attempt.xp_awarded) == ("dev-sw-act-23", True, 50)
        assert watch is not None
        after_identity = _target_identity(historical_path)
        assert [item[:5] + item[6:7] for item in after_identity] == [
            item[:5] + item[6:7] for item in before_identity
        ]
        assert next(
            item
            for item in build_training_week(db, student, 20)["activities"]
            if item["content_ref"] == "18" and item["activity_type"] == "guided_lab"
        )["complete"] is True

    assert _canonical_target_state(fresh_path) == _canonical_target_state(historical_path)
    assert _active_totals(fresh_path) == _active_totals(historical_path) == (35, 320, 141, 179)
    assert _role_counts(fresh_path) == _role_counts(historical_path) == {
        "learn": 216,
        "check": 38,
        "practice": 23,
        "troubleshoot": 36,
        "prove": 7,
    }
    assert _week_21_required_videos(fresh_path) == _week_21_required_videos(historical_path) == {"53", "55"}

    _seed(historical_url)
    first_repeat_identity = _target_identity(historical_path)
    _seed(historical_url)
    assert _target_identity(historical_path) == first_repeat_identity
    assert _activity_identity(historical_path, 9, "guided_lab", "1") == original_week_9_identity
    assert _legacy_network_template_count(fresh_path) == 0
    assert _legacy_network_template_count(historical_path) == original_legacy_network_count
    assert _active_totals(historical_path) == (35, 320, 141, 179)

    _run([sys.executable, "-m", "alembic", "downgrade", REVISION_0059], historical_url)
    with Session(historical_engine) as db:
        assert db.get(LabTemplate, 18).lab_type == "structured_cli"
        assert db.get(LabRun, progress_ids[1]).status == "submitted"
        assert db.get(CliLabAttempt, progress_ids[2]).completed_at is not None
        assert db.get(VideoWatch, progress_ids[3]) is not None
        assert db.get(StudentRole, progress_ids[4]).role_id == progress_ids[6]
        assert db.get(QuizAttempt, progress_ids[5]).score == 88
    assert _week_21_required_videos(historical_path) >= {"53", "54", "55", "56"}
    assert _owned_0059_state(historical_path) == original_owned_0059_state

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], historical_url)
    assert _canonical_target_state(fresh_path) == _canonical_target_state(historical_path)
    assert _active_totals(historical_path) == (35, 320, 141, 179)
    with Session(historical_engine) as db:
        assert db.get(Student, progress_ids[0]).current_role_id == progress_ids[6]
        assert db.get(StudentRole, progress_ids[4]).role_id == progress_ids[6]
        assert db.get(QuizAttempt, progress_ids[5]).score == 88


def test_phase4c2_downgrade_restores_only_owned_0059_content(tmp_path):
    database_path = tmp_path / "cycle.db"
    database_url = f"sqlite:///{database_path}"
    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], database_url)
    _seed(database_url)
    upgraded = _target_identity(database_path)

    _run([sys.executable, "-m", "alembic", "downgrade", REVISION_0059], database_url)
    engine = create_engine(database_url)
    with Session(engine) as db:
        assert db.get(LabTemplate, 2).lab_type == "structured_cli"
        assert db.get(LabTemplate, 2).success_criteria["required_commands"][0] == "ipconfig /all"
        assert db.get(LabTemplate, 16).success_criteria["terminal_profile"] == "linux"
        assert db.get(LabTemplate, 20).lab_type == "structured_cloud"
        target_activities = db.query(TrainingWeekActivity).filter(
            TrainingWeekActivity.activity_type == "guided_lab",
            TrainingWeekActivity.content_ref.in_([str(value) for value in TARGETS.values()]),
        )
        assert all("learning_role" not in (activity.metadata_json or {}) for activity in target_activities)
    assert _week_21_required_videos(database_path) >= {"53", "54", "55", "56"}

    _run([sys.executable, "-m", "alembic", "upgrade", REVISION_0060], database_url)
    assert _target_identity(database_path) == upgraded
    assert _active_totals(database_path) == (35, 320, 141, 179)
