from datetime import datetime, timezone

from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.learning import Lesson, Module
from app.models.lesson_progress import StudentLessonProgress
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.beginner_learning import (
    A_PLUS_WEEKS,
    HYBRID_LABS_ENABLED,
    NETWORK_PLUS_WEEKS,
    SWITCH_LABS_UNLOCK_WEEK,
    build_learning_phase,
)
from app.services.service_desk_progression import (
    build_service_desk_progression,
    scenario_access,
)
from app.services.training_curriculum_seed import sync_beginner_learning_rollout
from conftest import make_student


def _week_state(week_number, *, complete=False, locked=False):
    return {
        "week_number": week_number,
        "is_complete": complete,
        "locked": locked,
    }


def test_new_student_starts_in_aplus_and_network_plus_is_locked():
    states = [
        _week_state(week_number, locked=week_number != A_PLUS_WEEKS[0])
        for week_number in (*A_PLUS_WEEKS, *NETWORK_PLUS_WEEKS)
    ]

    phase = build_learning_phase(states, current_week=A_PLUS_WEEKS[0])

    assert phase["key"] == "aplus"
    assert phase["label"] == "CompTIA A+"
    assert phase["network_plus_locked"] is True
    assert phase["switch_labs_unlocked"] is False


def test_network_plus_begins_after_aplus_and_switch_labs_unlock_at_halfway():
    states = [
        *[_week_state(week, complete=True) for week in A_PLUS_WEEKS],
        _week_state(9, complete=True),
        _week_state(10, complete=True),
        _week_state(11),
        _week_state(12, locked=True),
    ]

    phase = build_learning_phase(states, current_week=SWITCH_LABS_UNLOCK_WEEK)

    assert phase["key"] == "network_plus"
    assert phase["network_plus_locked"] is False
    assert phase["network_plus_progress_percent"] == 50
    assert phase["switch_labs_unlocked"] is True


def test_topic_gating_locks_advanced_and_hybrid_scenarios():
    progression = {
        "direct_assignment_override_keys": set(),
        "curriculum_unlocked_keys": set(),
        "unlocked_pack_keys": {"starter-support", "advanced-troubleshooting"},
        "passed_keys": set(),
        "guided_completed_keys": set(),
        "assigned_keys": set(),
        "curriculum_current_keys": set(),
        "topic_gating_enabled": True,
        "topic_unlocked_keys": {"locked-user-account"},
        "in_progress_keys": set(),
    }

    beginner = scenario_access(progression, "locked-user-account")
    advanced = scenario_access(progression, "inc2506")
    hybrid = scenario_access(progression, "inc2504")

    assert beginner["unlocked"] is True
    assert advanced["unlocked"] is False
    assert hybrid["unlocked"] is False
    assert HYBRID_LABS_ENABLED is False


def test_unlocked_aplus_ticket_remains_available_during_network_plus():
    progression = {
        "direct_assignment_override_keys": set(),
        "curriculum_unlocked_keys": set(),
        "unlocked_pack_keys": {"starter-support", "core-desktop"},
        "passed_keys": {"locked-user-account"},
        "guided_completed_keys": set(),
        "assigned_keys": set(),
        "curriculum_current_keys": set(),
        "topic_gating_enabled": True,
        "topic_unlocked_keys": {"locked-user-account", "inc2503"},
        "in_progress_keys": set(),
    }

    access = scenario_access(progression, "locked-user-account")

    assert access["unlocked"] is True
    assert access["queue_type"] == "practice"


def _seed_topic_week(db, week_number, scenario_key):
    module = Module(
        code=f"MOD-{week_number:03d}",
        title=f"Topic {week_number}",
        module_order=week_number,
    )
    db.add(module)
    db.flush()
    lesson = Lesson(
        module_id=module.id,
        title=f"Topic {week_number} lesson",
        lesson_order=1,
        status="published",
    )
    db.add(lesson)
    week = TrainingWeek(
        week_number=week_number,
        display_order=week_number,
        title=f"Topic {week_number}",
        learning_goals=[],
        requires_previous_week=False,
    )
    db.add(week)
    db.flush()
    db.add_all(
        [
            TrainingWeekActivity(
                stable_id=f"week-{week_number}-lesson-{lesson.id}",
                training_week_id=week.id,
                activity_type="lesson",
                content_ref=str(lesson.id),
                display_order=1,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                stable_id=f"week-{week_number}-service-desk-{scenario_key}",
                training_week_id=week.id,
                activity_type="service_desk_scenario",
                content_ref=scenario_key,
                display_order=2,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
        ]
    )
    db.commit()
    return lesson


def test_completing_aplus_topic_unlocks_related_beginner_ticket(db):
    student = make_student(db, "aplus-topic-ticket")
    lesson = _seed_topic_week(db, 1, "locked-user-account")

    before = build_service_desk_progression(db, student)
    assert scenario_access(before, "locked-user-account")["unlocked"] is False

    db.add(
        StudentLessonProgress(
            student_id=student.id,
            lesson_id=lesson.id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    after = build_service_desk_progression(db, student)
    assert scenario_access(after, "locked-user-account")["unlocked"] is True


def test_network_plus_ticket_unlocks_only_after_related_topic(db):
    student = make_student(db, "network-topic-ticket")
    lesson = _seed_topic_week(db, 9, "inc2503")

    before = build_service_desk_progression(db, student)
    assert scenario_access(before, "inc2503")["unlocked"] is False

    db.add(
        StudentLessonProgress(
            student_id=student.id,
            lesson_id=lesson.id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    after = build_service_desk_progression(db, student)
    assert scenario_access(after, "inc2503")["unlocked"] is True


def test_rollout_reorders_existing_weeks_without_resetting_progress(db):
    student = make_student(db, "preserved-progress")
    module = Module(code="MOD-001", title="Support", module_order=1)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="Existing lesson", lesson_order=1, status="published")
    db.add(lesson)
    db.flush()
    progress = StudentLessonProgress(
        student_id=student.id,
        lesson_id=lesson.id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(progress)
    for week_number, display_order in ((9, 9), (10, 23), (11, 24), (12, 25), (13, 10)):
        db.add(
            TrainingWeek(
                week_number=week_number,
                display_order=display_order,
                title=f"Week {week_number}",
                learning_goals=[],
            )
        )
    db.flush()
    week_10 = db.query(TrainingWeek).filter_by(week_number=10).one()
    lab = CliLab(
        id="dev-sw-act-04",
        compartment_id="learn-switching",
        vendor_id="cisco-ios",
        title="Restore the Silent Port",
        order_index=4,
        content={},
    )
    db.add(lab)
    db.flush()
    attempt = CliLabAttempt(
        student_id=student.id,
        lab_id=lab.id,
        completed_at=datetime.now(timezone.utc),
        xp_awarded=50,
    )
    db.add(attempt)
    activity = TrainingWeekActivity(
        stable_id="week-10-networking_lab-dev-sw-act-04",
        training_week_id=week_10.id,
        activity_type="networking_lab",
        content_ref=lab.id,
        display_order=1,
        is_required=True,
        prerequisite_mode="soft",
        metadata_json={},
    )
    db.add(activity)
    db.commit()
    progress_id = progress.id
    attempt_id = attempt.id

    first = sync_beginner_learning_rollout(db)
    second = sync_beginner_learning_rollout(db)

    assert first["weeks_updated"] > 0
    assert first["networking_labs_optionalized"] == 1
    assert second == {"weeks_updated": 0, "networking_labs_optionalized": 0}
    assert db.query(TrainingWeek).filter_by(week_number=10).one().display_order == 10
    assert db.query(TrainingWeek).filter_by(week_number=13).one().display_order == 13
    assert db.get(TrainingWeekActivity, activity.id).is_required is False
    assert db.get(StudentLessonProgress, progress_id).completed_at is not None
    assert db.get(CliLabAttempt, attempt_id).completed_at is not None
