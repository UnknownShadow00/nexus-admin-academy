from app.models.cli_lab import CliLab
from conftest import make_student

from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson, Module
from app.models.quiz import Question, Quiz
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.training_curriculum_seed import (
    _revision_includes,
    reconcile_optional_lesson_requirements,
    sync_initial_training_activities,
    sync_weeks_3_4_prelaunch_quality,
    sync_weeks_3_6_quality,
    sync_weeks_7_10_quality,
    sync_weeks_11_14_quality,
    sync_weeks_15_18_quality,
    sync_weeks_19_22_quality,
    sync_weeks_23_24_quality,
    sync_weeks_1_4_practice_realignment,
)
from app.services.curriculum_structure import learning_role_for
from app.services.training_service import validate_training_curriculum


def _add_week(db, number):
    week = TrainingWeek(
        week_number=number,
        display_order=number,
        title=f"Week {number}",
        learning_goals=[],
        is_active=True,
        requires_previous_week=False if number == 1 else True,
    )
    db.add(week)
    return week


def _add_lab(db, lab_id, title, week_number, lab_type="guided"):
    db.add(
        LabTemplate(
            id=lab_id,
            title=title,
            description="Legacy lab",
            lab_type=lab_type,
            difficulty=2,
            week_number=week_number,
            estimated_minutes=30,
            is_published=True,
            environment_requirements={},
            success_criteria={"tasks": ["Legacy task"]},
            required_evidence={"screenshot": True},
            hints={},
        )
    )


def test_beginner_intro_lessons_are_required_and_existing_rows_converge(db):
    module = Module(
        code="MOD-001",
        title="The Ticket Is the Job",
        module_order=2,
        difficulty_band=1,
        estimated_hours=1,
    )
    db.add(module)
    db.flush()
    lessons = [
        Lesson(module_id=module.id, title="Anatomy of a Good Ticket", lesson_order=1, status="published"),
        Lesson(module_id=module.id, title="Meet the Command Line", lesson_order=2, status="published"),
    ]
    instructor_optional = Lesson(
        module_id=module.id,
        title="Instructor Optional Enrichment",
        lesson_order=3,
        status="published",
    )
    lessons.append(instructor_optional)
    db.add_all(lessons)
    week = _add_week(db, 1)
    db.flush()
    db.add_all(
        [
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-1-lesson-{lesson.id}",
                activity_type="lesson",
                content_ref=str(lesson.id),
                display_order=index,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            )
            for index, lesson in enumerate(lessons, start=1)
        ]
    )
    db.commit()

    assert reconcile_optional_lesson_requirements(db) == {"updated": 2, "skipped": False}
    activities = {
        row.content_ref: row for row in db.query(TrainingWeekActivity).all()
    }
    assert activities[str(lessons[0].id)].is_required is True
    assert activities[str(lessons[1].id)].is_required is True
    assert activities[str(instructor_optional.id)].is_required is False
    assert reconcile_optional_lesson_requirements(db) == {"updated": 0, "skipped": False}


def test_beginner_polish_revision_policy_follows_migration_ancestry():
    assert _revision_includes("0069_merge_v2_beginner_heads", "0070_beginner_content_ux_polish") is False
    assert _revision_includes("0070_beginner_content_ux_polish", "0070_beginner_content_ux_polish") is True
    assert _revision_includes("0071_forced_first_login_password_change", "0070_beginner_content_ux_polish") is True
    for rollout_revision in (
        "0060_network_linux_cloud_practical_upgrade",
        "0061_integrated_support_prove",
        "0062_beginner_learning_rollout",
    ):
        assert _revision_includes("0071_forced_first_login_password_change", rollout_revision) is True


def test_weeks_1_4_practice_realignment_converges_seeded_curriculum(db):
    for number in range(1, 5):
        _add_week(db, number)
    _add_lab(db, 1, "IP Addressing & Subnetting Practice", 2)
    _add_lab(db, 2, "Troubleshoot a Network Connectivity Scenario", 3, "scenario")
    _add_lab(db, 3, "Windows Command-Line Diagnostics", 4)
    _add_lab(db, 4, "Hardware Component Identification", 1, "identification")
    _add_lab(db, 5, "AD Break-Fix: locked and misplaced account on a live domain", 15, "break_fix")
    db.add(CliLab(id="meet-cli-001", compartment_id="meet-the-cli", vendor_id="cisco", title="Meet the CLI", order_index=1, content={}))
    scenarios = [
        ServiceDeskScenario(stable_key=key, title=key, category="service_desk", difficulty=1, status="active")
        for key in ("locked-user-account", "inc2404", "password-reset", "mfa-reset")
    ]
    db.add_all(scenarios)
    db.flush()
    db.add_all(
        [
            ServiceDeskScenarioVersion(
                scenario_id=scenario.id,
                version_number=1,
                definition_json={},
                definition_hash=f"test-{scenario.id}",
                validation_status="valid",
                status="published",
            )
            for scenario in scenarios
        ]
    )
    db.commit()

    initial = sync_initial_training_activities(db)

    # sync_initial_training_activities already seeds each week's Apply step
    # (a service_desk_scenario activity) ahead of the realignment run, as in
    # the real curriculum — reuse those to assert Practice lands *before*
    # Apply, not just appended after it.
    apply_activities = {
        number: db.query(TrainingWeekActivity)
        .filter_by(training_week_id=week.id, activity_type="service_desk_scenario")
        .one()
        for number, week in ((n, db.query(TrainingWeek).filter_by(week_number=n).one()) for n in range(1, 5))
    }
    assert apply_activities[1].is_required is True
    assert apply_activities[2].is_required is True
    assert apply_activities[3].is_required is False
    assert apply_activities[4].is_required is False

    first = sync_weeks_1_4_practice_realignment(db)

    assert initial["created"] == 9
    assert first["created_templates"] == 1
    assert db.get(LabTemplate, 1).is_published is False
    assert db.get(LabTemplate, 2).is_published is False
    assert (db.get(LabTemplate, 3).week_number, db.get(LabTemplate, 3).lab_type) == (3, "structured_diagnostic")
    assert (db.get(LabTemplate, 4).week_number, db.get(LabTemplate, 4).lab_type) == (2, "structured_identification")
    assert (db.get(LabTemplate, 5).week_number, db.get(LabTemplate, 5).lab_type, db.get(LabTemplate, 5).is_published) == (15, "break_fix", True)

    weeks = {week.week_number: week for week in db.query(TrainingWeek).all()}
    guided_refs = {
        number: [activity.content_ref for activity in db.query(TrainingWeekActivity).filter_by(training_week_id=week.id, activity_type="guided_lab").all()]
        for number, week in weeks.items()
    }
    triage = db.query(LabTemplate).filter_by(title="Prioritize the Queue").one()
    assert guided_refs[1] == []
    assert guided_refs[2] == ["4"]
    assert guided_refs[3] == ["3"]
    assert guided_refs[4] == [str(triage.id)]
    assert db.query(TrainingWeekActivity).filter_by(activity_type="networking_lab", content_ref="meet-cli-001").one().is_required is True
    assert validate_training_curriculum(db)["valid"] is True

    week_one_cli = db.query(TrainingWeekActivity).filter_by(
        training_week_id=weeks[1].id,
        activity_type="networking_lab",
    ).one()
    assert week_one_cli.display_order < apply_activities[1].display_order

    # Practice must be sequenced before Apply, not appended after it.
    for number in (2, 3, 4):
        week = weeks[number]
        practice = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id, activity_type="guided_lab").one()
        apply_activity = db.get(TrainingWeekActivity, apply_activities[number].id)
        assert practice.display_order < apply_activity.display_order, f"week {number} Practice must precede Apply"

    second = sync_weeks_1_4_practice_realignment(db)
    assert second == {
        "updated_templates": 0,
        "created_templates": 0,
        "moved_activities": 0,
        "created_activities": 0,
        "deleted_activities": 0,
        "updated_cli_activities": 0,
        "reordered_activities": 0,
        "skipped": False,
    }


def test_week_two_required_quiz_follows_all_required_learning(db):
    weeks = {number: _add_week(db, number) for number in range(1, 5)}
    db.flush()
    _add_lab(db, 1, "IP Addressing & Subnetting Practice", 2)
    _add_lab(db, 2, "Troubleshoot a Network Connectivity Scenario", 3, "scenario")
    _add_lab(db, 3, "Windows Command-Line Diagnostics", 4)
    _add_lab(db, 4, "Hardware Component Identification", 1, "identification")
    _add_lab(db, 5, "AD Break-Fix: locked and misplaced account on a live domain", 15, "break_fix")
    db.add_all(
        [
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-lesson-1", activity_type="lesson", content_ref="1", display_order=1, is_required=True, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-quiz-78", activity_type="quiz", content_ref="78", display_order=2, is_required=True, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-video-44", activity_type="video", content_ref="44", display_order=3, is_required=True, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-service_desk_scenario-inc2404", activity_type="service_desk_scenario", content_ref="inc2404", display_order=4, is_required=True, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-capstone-test", activity_type="capstone", content_ref="test", display_order=5, is_required=False, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-review-test", activity_type="review", content_ref="test", display_order=6, is_required=False, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-support-ticket-test", activity_type="support_ticket", content_ref="test", display_order=7, is_required=False, prerequisite_mode="soft", metadata_json={}),
            TrainingWeekActivity(training_week_id=weeks[2].id, stable_id="week-2-review-prove-override", activity_type="review", content_ref="prove-test", display_order=8, is_required=False, prerequisite_mode="soft", metadata_json={"learning_role": "prove"}),
        ]
    )
    db.commit()

    result = sync_weeks_1_4_practice_realignment(db)
    ordered_types = [
        row.activity_type
        for row in db.query(TrainingWeekActivity)
        .filter_by(training_week_id=weeks[2].id)
        .order_by(TrainingWeekActivity.display_order)
    ]

    assert result["reordered_activities"] > 0
    assert ordered_types.index("video") < ordered_types.index("quiz")
    assert ordered_types.index("quiz") < ordered_types.index("guided_lab")
    assert ordered_types.index("guided_lab") < ordered_types.index("service_desk_scenario")
    ordered_rows = list(
        db.query(TrainingWeekActivity)
        .filter_by(training_week_id=weeks[2].id)
        .order_by(TrainingWeekActivity.display_order)
    )
    role_rank = {"learn": 0, "check": 1, "practice": 2, "troubleshoot": 3, "prove": 4}
    ordered_roles = [learning_role_for(row.activity_type, row.metadata_json) for row in ordered_rows]
    assert [role_rank[role] for role in ordered_roles] == sorted(role_rank[role] for role in ordered_roles)
    assert ordered_types.index("review") < ordered_types.index("guided_lab")
    assert ordered_types.index("support_ticket") < ordered_types.index("capstone")


def test_weeks_3_6_quality_sync_builds_aligned_required_paths_idempotently(db):
    weeks = {number: _add_week(db, number) for number in range(3, 7)}
    db.flush()
    for number, week in weeks.items():
        rows = [
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-lesson-{number}",
                activity_type="lesson",
                content_ref=str(number),
                display_order=1,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-video-{next(iter({3: {117}, 4: {169}, 5: {162}, 6: {139}}[number]))}",
                activity_type="video",
                content_ref=str(next(iter({3: {117}, 4: {169}, 5: {162}, 6: {139}}[number]))),
                display_order=2,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-quiz-{ {3: 4, 4: 5, 5: 6, 6: 7}[number] }",
                activity_type="quiz",
                content_ref=str({3: 4, 4: 5, 5: 6, 6: 7}[number]),
                display_order=3,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-service-desk-test-{number}",
                activity_type="service_desk_scenario",
                content_ref=f"scenario-{number}",
                display_order=4,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
        ]
        db.add_all(rows)
    _add_lab(db, 3, "Windows Command-Line Diagnostics", 3, "structured_diagnostic")
    db.commit()

    first = sync_weeks_3_6_quality(db)

    assert first["skipped"] is False
    for number, week in weeks.items():
        db.refresh(week)
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        assert all(not row.is_required for row in activities if row.activity_type == "lesson")
        assert [row.content_ref for row in activities if row.activity_type == "quiz" and row.is_required] == [str({3: 4, 4: 5, 5: 6, 6: 7}[number])]
        assert any(row.activity_type == "guided_lab" and row.is_required for row in activities)
        required_apply = [row for row in activities if row.activity_type == "service_desk_scenario" and row.is_required]
        assert bool(required_apply) is (number in {5, 6})
        practice = next(row for row in activities if row.activity_type == "guided_lab" and row.is_required)
        apply_rows = [row for row in activities if row.activity_type == "service_desk_scenario"]
        assert not apply_rows or practice.display_order < min(row.display_order for row in apply_rows)

    cli_lab = db.get(LabTemplate, 3)
    assert cli_lab.lab_type == "structured_cli"
    assert cli_lab.success_criteria["required_commands"] == [
        "hostname",
        "whoami",
        "ipconfig /all",
        "ping 192.168.1.1",
        "nslookup intranet.nexus.internal",
        "tracert intranet.nexus.internal",
        "netstat -ano",
    ]

    second = sync_weeks_3_6_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0


def test_weeks_3_4_prelaunch_quality_waits_for_normal_seed_content(db):
    """Fresh migrations must not consume fixed lab IDs before seed.py runs."""
    _add_week(db, 3)
    _add_week(db, 4)
    db.commit()

    result = sync_weeks_3_4_prelaunch_quality(db)

    assert result == {
        "updated": 0,
        "skipped": True,
        "reason": "curriculum_not_seeded",
    }
    assert db.query(LabTemplate).count() == 0


def test_weeks_3_4_prelaunch_quality_builds_beginner_paths_without_future_topic_deadlocks(db):
    weeks = {
        number: _add_week(db, number)
        for number in (1, 2, 3, 4, 5, 7, 8, 23)
    }
    modules = {
        3: Module(code="MOD-003", title="Windows 11 as Your Workbench", module_order=4, estimated_hours=15),
        4: Module(code="MOD-004", title="Working the Queue", module_order=5, estimated_hours=13),
    }
    db.add_all(modules.values())
    db.flush()
    lesson_specs = {
        3: (
            ("Accounts, Profiles, and Permissions", 90),
            ("The Investigator's Toolkit", 90),
            ("Command-Line Diagnostics", 120),
            ("Windows Update and Defender Basics", 60),
        ),
        4: (
            ("Priority, Impact, and Not Making It Worse", 90),
            ("Talking to Humans", 60),
        ),
    }
    lessons = {}
    for week_number, specs in lesson_specs.items():
        for order, (title, minutes) in enumerate(specs, start=1):
            lesson = Lesson(
                module_id=modules[week_number].id,
                title=title,
                lesson_order=order,
                estimated_minutes=minutes,
                status="published",
                summary={
                    "Command-Line Diagnostics": (
                        "The Windows support seven, and what their output MEANS:\n"
                        "ipconfig /all → your identity on the network. Read: IP "
                        "(169.254.x.x = DHCP failed), gateway (empty = no route "
                        "out), DNS servers (wrong = 'internet down' with working IP).\n"
                        "netstat -ano → who is talking; pair PID with Task Manager Details.\n"
                        "sfc /scannow then DISM /Online /Cleanup-Image /RestoreHealth → system file repair "
                        "sequence (DISM repairs the store sfc repairs from)."
                    ),
                    "Accounts, Profiles, and Permissions": (
                        "PROFILES: a profile is the user's world (Desktop, Documents, HKCU). "
                        "NTFS PERMISSIONS: Read/Write/Modify/Full Control; DENY beats ALLOW; "
                        "permissions inherit down folders; effective access = what actually "
                        "applies after group math."
                    ),
                    "Priority, Impact, and Not Making It Worse": (
                        "PRACTICAL ITIL VOCABULARY (Nexus original summary — enough to be dangerous): "
                        "when NOT to act is a graded anchor (safe_fix_or_escalation)."
                    ),
                }.get(title, f"Beginner lesson for {title}."),
                outcomes=(
                    ["Execute the sfc → DISM repair sequence and read its outcomes"]
                    if title == "Command-Line Diagnostics"
                    else []
                ),
            )
            db.add(lesson)
            db.flush()
            lessons[title] = lesson

    for quiz_id, title, week_number in (
        (2, "Windows Accounts and Permissions", 3),
        (3, "The Investigator's Toolkit", 3),
        (4, "Windows Command-Line Diagnostics", 3),
        (5, "Help-Desk Operations", 4),
    ):
        quiz = Quiz(
            id=quiz_id,
            title=title,
            week_number=week_number,
            quiz_purpose="practice",
            is_required=False,
            show_in_weekly_checklist=False,
            status="published",
            editorial_status="validated",
            answer_keys_validated=True,
            is_active=True,
        )
        db.add(quiz)
        db.flush()
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text="Placeholder audited question",
                option_a="Supported answer",
                option_b="Distractor",
                option_c="Distractor",
                option_d="Distractor",
                correct_answer="A",
                explanation="Placeholder explanation.",
            )
        )

    custom_quiz = Quiz(
        id=105,
        title="Help-Desk Operations",
        week_number=4,
        quiz_purpose="practice",
        is_required=False,
        show_in_weekly_checklist=False,
        status="published",
        editorial_status="validated",
        answer_keys_validated=True,
        is_active=True,
    )
    db.add(custom_quiz)
    db.flush()
    custom_question = Question(
        quiz_id=custom_quiz.id,
        question_text="Instructor-authored duplicate-title question",
        option_a="Custom correct answer",
        option_b="Custom distractor",
        option_c="Custom distractor",
        option_d="Custom distractor",
        correct_answer="A",
        explanation="Instructor-authored explanation.",
    )
    db.add(custom_question)

    _add_lab(db, 3, "Windows Command-Line Diagnostics", 3, "structured_evidence_case")
    _add_lab(db, 6, "Prioritize the Queue", 4, "structured_diagnostic")
    db.flush()
    legacy_lab = db.get(LabTemplate, 3)
    legacy_lab.success_criteria = {
        "questions": [
            {"id": "scope", "prompt": "What is the scope?"},
            {"id": "cause", "prompt": "What is the likely cause?"},
            {"id": "action", "prompt": "What is the safe next action?"},
        ]
    }
    legacy_criteria = legacy_lab.success_criteria
    historical_student = make_student(db, username="week-three-history")
    historical_run = LabRun(
        lab_template_id=legacy_lab.id,
        student_id=historical_student.id,
        status="submitted",
        final_score=100,
        structured_feedback={
            "questions": [
                {"id": "scope", "is_correct": True},
                {"id": "cause", "is_correct": True},
                {"id": "action", "is_correct": True},
            ]
        },
    )
    db.add(historical_run)
    display_order = {3: 0, 4: 0}

    def add_activity(week_number, activity_type, content_ref, *, required=False, metadata=None):
        display_order[week_number] += 1
        db.add(
            TrainingWeekActivity(
                training_week_id=weeks[week_number].id,
                stable_id=f"week-{week_number}-{activity_type}-{content_ref}",
                activity_type=activity_type,
                content_ref=str(content_ref),
                display_order=display_order[week_number],
                is_required=required,
                prerequisite_mode="soft",
                metadata_json=metadata or {},
            )
        )

    for title in lesson_specs[3]:
        add_activity(3, "lesson", lessons[title[0]].id)
    for video_id in (108, 117, 118):
        add_activity(3, "video", video_id)
    for quiz_id in (2, 3, 4):
        add_activity(3, "quiz", quiz_id)
    add_activity(3, "guided_lab", 3, required=True)
    add_activity(3, "service_desk_scenario", "password-reset")

    for title in lesson_specs[4]:
        add_activity(4, "lesson", lessons[title[0]].id)
    for video_id in (1, 2, 4, 5, 46, 62, 169, 181):
        add_activity(4, "video", video_id)
    add_activity(4, "quiz", 5)
    add_activity(4, "guided_lab", 6, required=True)
    add_activity(4, "service_desk_scenario", "mfa-reset")
    db.commit()

    first = sync_weeks_3_4_prelaunch_quality(db)
    assert first["skipped"] is False
    db.refresh(custom_question)
    assert custom_question.question_text == "Instructor-authored duplicate-title question"
    assert custom_question.correct_answer == "A"
    assert custom_question.explanation == "Instructor-authored explanation."

    lessons_by_id = {lesson.id: lesson for lesson in lessons.values()}
    required_titles = {
        number: {
            lessons_by_id[int(row.content_ref)].title
            for row in db.query(TrainingWeekActivity).filter_by(
                training_week_id=weeks[number].id,
                activity_type="lesson",
                is_required=True,
            )
        }
        for number in (3, 4)
    }
    assert required_titles[3] == {
        "Accounts, Profiles, and Permissions",
        "The Investigator's Toolkit",
        "Command-Line Diagnostics",
    }
    assert required_titles[4] == {
        "Priority, Impact, and Not Making It Worse",
        "Talking to Humans",
    }
    assert lessons["Windows Update and Defender Basics"].estimated_minutes == 30

    required_quizzes = {
        number: {
            int(row.content_ref)
            for row in db.query(TrainingWeekActivity).filter_by(
                training_week_id=weeks[number].id,
                activity_type="quiz",
                is_required=True,
            )
        }
        for number in (3, 4)
    }
    assert required_quizzes == {3: {2, 3, 4}, 4: {5}}

    week_three_cases = db.query(TrainingWeekActivity).filter_by(
        training_week_id=weeks[3].id,
        activity_type="service_desk_scenario",
    ).all()
    assert [(row.content_ref, row.is_required) for row in week_three_cases] == [("inc2501", True)]
    assert db.query(TrainingWeekActivity).filter_by(
        training_week_id=weeks[4].id,
        activity_type="service_desk_scenario",
    ).count() == 0
    assert {
        int(row.content_ref)
        for row in db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[2].id,
            activity_type="video",
        )
    } == {1, 46}
    assert {
        int(row.content_ref)
        for row in db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[5].id,
            activity_type="video",
        )
    } == {62}
    assert {
        int(row.content_ref)
        for row in db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[7].id,
            activity_type="video",
        )
    } == {5}
    assert {
        int(row.content_ref)
        for row in db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[8].id,
            activity_type="video",
        )
    } == {2, 4}
    assert {
        int(row.content_ref)
        for row in db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[23].id,
            activity_type="video",
        )
    } == {181}

    cli_activity = db.query(TrainingWeekActivity).filter_by(
        training_week_id=weeks[3].id,
        activity_type="guided_lab",
        is_required=True,
    ).one()
    cli = db.get(LabTemplate, int(cli_activity.content_ref))
    assert cli.id != legacy_lab.id
    assert cli.title == "Windows Command-Line Diagnostics Practice"
    assert cli.lab_type == "structured_cli"
    assert cli.success_criteria["required_commands"] == [
        "hostname",
        "whoami",
        "ipconfig /all",
        "ping 192.168.1.1",
        "nslookup intranet.nexus.internal",
        "tracert intranet.nexus.internal",
        "netstat -ano",
    ]
    db.refresh(legacy_lab)
    db.refresh(historical_run)
    assert legacy_lab.success_criteria == legacy_criteria
    assert historical_run.lab_template_id == legacy_lab.id
    assert [
        item["id"] for item in historical_run.structured_feedback["questions"]
    ] == ["scope", "cause", "action"]
    week_four_labs = db.query(TrainingWeekActivity).filter_by(
        training_week_id=weeks[4].id,
        activity_type="guided_lab",
        is_required=True,
    ).all()
    assert {learning_role_for(row.activity_type, row.metadata_json) for row in week_four_labs} == {
        "practice",
        "troubleshoot",
    }

    for number in (3, 4):
        ordered = db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[number].id
        ).order_by(TrainingWeekActivity.display_order).all()
        ranks = {
            "learn": 0,
            "check": 1,
            "practice": 2,
            "troubleshoot": 3,
            "prove": 4,
        }
        assert [ranks[learning_role_for(row.activity_type, row.metadata_json)] for row in ordered] == sorted(
            ranks[learning_role_for(row.activity_type, row.metadata_json)] for row in ordered
        )

    command_lesson = lessons["Command-Line Diagnostics"]
    assert "DISM" in command_lesson.summary
    assert command_lesson.summary.index("DISM") < command_lesson.summary.index("sfc")
    assert "Domain Name System (DNS)" in command_lesson.summary
    assert "process identifier (PID)" in command_lesson.summary
    assert "component store that System File Checker (SFC) uses as its source" in command_lesson.summary
    assert "DISM → SFC" in command_lesson.outcomes[0]
    accounts_lesson = lessons["Accounts, Profiles, and Permissions"]
    assert "HKCU" not in accounts_lesson.summary
    assert "WINDOWS FILE PERMISSIONS (NTFS)" in accounts_lesson.summary
    priority_lesson = lessons["Priority, Impact, and Not Making It Worse"]
    assert "safe_fix_or_escalation" not in priority_lesson.summary
    assert "COMMON SERVICE-DESK TERMS" in priority_lesson.summary

    second = sync_weeks_3_4_prelaunch_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0


def test_weeks_3_6_quality_sync_preserves_promotion_gate_quiz_purpose(db):
    """Quiz 5 backs PROMOTION_GATES Gate 1 (seed.py: {"week": 4}). Production

    curates it to quiz_purpose="gate" outside the ordinary seed. The sync must
    never downgrade that to "required"/"practice" or the gate becomes
    permanently unsatisfiable (progression_service only counts quiz_purpose
    == "gate" toward a required_quiz gate).
    """
    weeks = {number: _add_week(db, number) for number in range(3, 7)}
    db.flush()
    for number, week in weeks.items():
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-lesson-{number}",
                activity_type="lesson",
                content_ref=str(number),
                display_order=1,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            )
        )
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-quiz-{ {3: 4, 4: 5, 5: 6, 6: 7}[number] }",
                activity_type="quiz",
                content_ref=str({3: 4, 4: 5, 5: 6, 6: 7}[number]),
                display_order=2,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            )
        )
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-video-{next(iter({3: {117}, 4: {169}, 5: {162}, 6: {139}}[number]))}",
                activity_type="video",
                content_ref=str(next(iter({3: {117}, 4: {169}, 5: {162}, 6: {139}}[number]))),
                display_order=3,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            )
        )
    db.add(Quiz(id=5, title="Help-Desk Operations", week_number=4, quiz_purpose="gate", is_required=True, show_in_weekly_checklist=True))
    db.add(Quiz(id=4, title="Other Quiz", week_number=3, quiz_purpose="practice", is_required=False))
    _add_lab(db, 3, "Windows Command-Line Diagnostics", 3, "structured_diagnostic")
    db.commit()

    sync_weeks_3_6_quality(db)

    gate_quiz = db.get(Quiz, 5)
    assert gate_quiz.quiz_purpose == "gate"
    assert gate_quiz.is_required is True
    assert gate_quiz.show_in_weekly_checklist is True


def test_weeks_11_14_quality_sync_replaces_reading_gates_with_practice(db):
    weeks = {number: _add_week(db, number) for number in range(11, 15)}
    quizzes = {11: 13, 12: 14, 13: 15, 14: 16}
    videos = {11: "9", 12: "141", 13: "140"}
    db.flush()
    for number, week in weeks.items():
        rows = [
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-lesson-test",
                activity_type="lesson",
                content_ref=str(number),
                display_order=1,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-quiz-{quizzes[number]}",
                activity_type="quiz",
                content_ref=str(quizzes[number]),
                display_order=3,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-service-desk-test",
                activity_type="service_desk_scenario",
                content_ref=f"scenario-{number}",
                display_order=4,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
        ]
        if number in videos:
            rows.append(
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-video-{videos[number]}",
                    activity_type="video",
                    content_ref=videos[number],
                    display_order=2,
                    is_required=True,
                    prerequisite_mode="soft",
                    metadata_json={},
                )
            )
        db.add_all(rows)
    db.commit()

    first = sync_weeks_11_14_quality(db)

    assert first["skipped"] is False
    for number, week in weeks.items():
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        assert all(not row.is_required for row in activities if row.activity_type == "lesson")
        assert [row.content_ref for row in activities if row.activity_type == "quiz" and row.is_required] == [str(quizzes[number])]
        assert not [row for row in activities if row.activity_type == "service_desk_scenario" and row.is_required]
        practice = [row for row in activities if row.activity_type == "guided_lab" and row.is_required]
        assert len(practice) == 1
        apply_rows = [row for row in activities if row.activity_type == "service_desk_scenario"]
        assert practice[0].display_order < min(row.display_order for row in apply_rows)
    assert not db.query(TrainingWeekActivity).filter_by(
        training_week_id=weeks[12].id,
        activity_type="video",
        is_required=True,
    ).count()

    second = sync_weeks_11_14_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0


def test_weeks_7_10_quality_sync_rebuilds_network_practice_and_uses_cli_labs(db):
    weeks = {number: _add_week(db, number) for number in range(7, 11)}
    week_3 = _add_week(db, 3)
    week_6 = _add_week(db, 6)
    db.flush()
    required_quizzes = {7: 8, 8: 9, 9: 10, 10: 12}
    sample_videos = {7: 137, 8: 18, 9: 14, 10: 12}
    for number, week in weeks.items():
        db.add_all(
            [
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-lesson-test",
                    activity_type="lesson",
                    content_ref=str(number),
                    display_order=1,
                    is_required=True,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-video-{sample_videos[number]}",
                    activity_type="video",
                    content_ref=str(sample_videos[number]),
                    display_order=2,
                    is_required=False,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-quiz-{required_quizzes[number]}",
                    activity_type="quiz",
                    content_ref=str(required_quizzes[number]),
                    display_order=3,
                    is_required=False,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-service-desk-test",
                    activity_type="service_desk_scenario",
                    content_ref=f"scenario-{number}",
                    display_order=4,
                    is_required=True,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
            ]
        )
    for order, lab_id in enumerate(("dev-sw-act-04", "dev-sw-act-18"), start=5):
        db.add(CliLab(id=lab_id, compartment_id="switching", vendor_id="cisco", title=lab_id, order_index=order, content={}))
        db.add(
            TrainingWeekActivity(
                training_week_id=weeks[10].id,
                stable_id=f"week-10-networking_lab-{lab_id}",
                activity_type="networking_lab",
                content_ref=lab_id,
                display_order=order,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            )
        )
    _add_lab(db, 1, "IP Addressing & Subnetting Practice", 2)
    _add_lab(db, 2, "Troubleshoot a Network Connectivity Scenario", 3)
    db.add_all(
        [
            TrainingWeekActivity(
                training_week_id=week_3.id,
                stable_id="week-3-service_desk_scenario-password-reset",
                activity_type="service_desk_scenario",
                content_ref="password-reset",
                display_order=9,
                is_required=False,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_6.id,
                stable_id="week-6-service_desk_scenario-inc2505",
                activity_type="service_desk_scenario",
                content_ref="inc2505",
                display_order=9,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
        ]
    )
    db.commit()

    first = sync_weeks_7_10_quality(db)

    assert first["skipped"] is False
    assert (db.get(LabTemplate, 1).week_number, db.get(LabTemplate, 1).lab_type, db.get(LabTemplate, 1).is_published) == (9, "structured_subnet", True)
    assert (db.get(LabTemplate, 2).week_number, db.get(LabTemplate, 2).lab_type, db.get(LabTemplate, 2).is_published) == (8, "structured_cli", True)
    for number, week in weeks.items():
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        assert all(not row.is_required for row in activities if row.activity_type == "lesson")
        assert [row.content_ref for row in activities if row.activity_type == "quiz" and row.is_required] == [str(required_quizzes[number])]
        assert not [row for row in activities if row.activity_type == "service_desk_scenario" and row.is_required]
    week_6_apply = db.query(TrainingWeekActivity).filter_by(
        training_week_id=week_6.id,
        activity_type="service_desk_scenario",
    ).all()
    assert [(row.content_ref, row.is_required) for row in week_6_apply] == [
        ("password-reset", True),
        ("inc2505", False),
    ]
    required_switching = {
        row.content_ref
        for row in db.query(TrainingWeekActivity).filter_by(training_week_id=weeks[10].id, activity_type="networking_lab", is_required=True)
    }
    assert required_switching == {"dev-sw-act-04", "dev-sw-act-18"}

    second = sync_weeks_7_10_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0


def test_weeks_15_18_quality_sync_rebuilds_fake_lab_and_adds_command_practice(db):
    weeks = {number: _add_week(db, number) for number in range(15, 19)}
    quizzes = {15: 17, 16: 18, 17: 19, 18: 20}
    videos = {15: "135", 16: "178", 17: "170", 18: "128"}
    db.flush()
    for number, week in weeks.items():
        db.add_all(
            [
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-lesson-test",
                    activity_type="lesson",
                    content_ref=str(number),
                    display_order=1,
                    is_required=True,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-video-{videos[number]}",
                    activity_type="video",
                    content_ref=videos[number],
                    display_order=2,
                    is_required=number != 18,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-quiz-{quizzes[number]}",
                    activity_type="quiz",
                    content_ref=str(quizzes[number]),
                    display_order=3,
                    is_required=False,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
            ]
        )
    _add_lab(db, 5, "AD Break-Fix: locked and misplaced account on a live domain", 15, "break_fix")
    db.add(
        TrainingWeekActivity(
            training_week_id=weeks[15].id,
            stable_id="week-15-guided_lab-5",
            activity_type="guided_lab",
            content_ref="5",
            display_order=4,
            is_required=True,
            prerequisite_mode="soft",
            metadata_json={},
        )
    )
    db.commit()

    first = sync_weeks_15_18_quality(db)

    assert first["skipped"] is False
    rebuilt = db.get(LabTemplate, 5)
    assert (rebuilt.title, rebuilt.lab_type) == ("Diagnose the Group Policy Result", "structured_cli")
    assert rebuilt.success_criteria["required_commands"] == ["whoami", "gpresult /r", "gpupdate /force"]
    for number, week in weeks.items():
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        assert all(not row.is_required for row in activities if row.activity_type == "lesson")
        assert [row.content_ref for row in activities if row.activity_type == "quiz" and row.is_required] == [str(quizzes[number])]
        assert len([row for row in activities if row.activity_type == "guided_lab" and row.is_required]) == 1
    linux_lab = db.query(LabTemplate).filter_by(week_number=18, title="Investigate the Linux Host").one()
    assert linux_lab.success_criteria["terminal_profile"] == "linux"

    second = sync_weeks_15_18_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0


def test_weeks_19_22_quality_sync_adds_linux_and_cloud_practice(db):
    weeks = {number: _add_week(db, number) for number in range(19, 23)}
    quizzes = {19: 21, 20: 22, 21: 23, 22: 24}
    videos = {19: "128", 20: "145", 21: "53", 22: "132"}
    db.flush()
    for number, week in weeks.items():
        db.add_all(
            [
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-lesson-test",
                    activity_type="lesson",
                    content_ref=str(number),
                    display_order=1,
                    is_required=True,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-video-{videos[number]}",
                    activity_type="video",
                    content_ref=videos[number],
                    display_order=2,
                    is_required=True,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-quiz-{quizzes[number]}",
                    activity_type="quiz",
                    content_ref=str(quizzes[number]),
                    display_order=3,
                    is_required=False,
                    prerequisite_mode="soft",
                    metadata_json={},
                ),
            ]
        )
    db.commit()

    first = sync_weeks_19_22_quality(db)

    assert first["skipped"] is False
    for number, week in weeks.items():
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        assert all(not row.is_required for row in activities if row.activity_type == "lesson")
        assert [row.content_ref for row in activities if row.activity_type == "quiz" and row.is_required] == [str(quizzes[number])]
        # Week 21 no longer gets a guided lab from this sync: Phase 4B.1
        # (sync_microsoft_workplace_foundations) owns that content now,
        # relocated to week 26's Entra module. See that constant's comment
        # in training_curriculum_seed.py's WEEKS_19_22_QUALITY week 21 entry.
        expected_lab_count = 0 if number == 21 else 1
        assert len([row for row in activities if row.activity_type == "guided_lab" and row.is_required]) == expected_lab_count
    required_week_21_videos = {
        row.content_ref
        for row in db.query(TrainingWeekActivity).filter_by(
            training_week_id=weeks[21].id,
            activity_type="video",
            is_required=True,
        )
    }
    assert required_week_21_videos == {"53"}
    linux_labs = db.query(LabTemplate).filter(LabTemplate.week_number.in_([19, 20])).all()
    assert {lab.success_criteria["terminal_profile"] for lab in linux_labs} == {"linux"}

    second = sync_weeks_19_22_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0


def test_weeks_23_24_quality_sync_moves_integrated_quiz_and_adds_final_practice(db):
    week_23 = _add_week(db, 23)
    week_24 = _add_week(db, 24)
    db.flush()
    db.add_all(
        [
            TrainingWeekActivity(
                training_week_id=week_23.id,
                stable_id="week-23-lesson-61",
                activity_type="lesson",
                content_ref="61",
                display_order=1,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_23.id,
                stable_id="week-23-video-174",
                activity_type="video",
                content_ref="174",
                display_order=2,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_23.id,
                stable_id="week-23-quiz-48",
                activity_type="quiz",
                content_ref="48",
                display_order=3,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_24.id,
                stable_id="week-24-lesson-63",
                activity_type="lesson",
                content_ref="63",
                display_order=1,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
            TrainingWeekActivity(
                training_week_id=week_24.id,
                stable_id="week-24-quiz-25",
                activity_type="quiz",
                content_ref="25",
                display_order=2,
                is_required=True,
                prerequisite_mode="soft",
                metadata_json={},
            ),
        ]
    )
    db.commit()

    first = sync_weeks_23_24_quality(db)

    assert first["skipped"] is False
    week_23_activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week_23.id).all()
    week_24_activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week_24.id).all()
    assert [row.content_ref for row in week_23_activities if row.activity_type == "quiz" and row.is_required] == ["25"]
    assert not [row for row in week_24_activities if row.activity_type == "quiz"]
    assert all(not row.is_required for row in week_23_activities + week_24_activities if row.activity_type == "lesson")
    assert len([row for row in week_23_activities if row.activity_type == "guided_lab" and row.is_required]) == 1
    assert len([row for row in week_24_activities if row.activity_type == "guided_lab" and row.is_required]) == 1

    capstone_ref = next(row.content_ref for row in week_24_activities if row.activity_type == "guided_lab" and row.is_required)
    capstone_lab = db.get(LabTemplate, int(capstone_ref))
    assert capstone_lab.title == "Final Support Shift"
    assert capstone_lab.lab_type == "structured_capstone"
    assert len(capstone_lab.success_criteria["questions"]) == 7
    assert capstone_lab.success_criteria["required_commands"] == ["ipconfig /all", "nslookup helpdesk.nexus.internal", "gpresult /r"]
    db.refresh(week_24)
    assert week_24.title == "Capstone: Final Support Shift"

    second = sync_weeks_23_24_quality(db)
    assert second["created_templates"] == 0
    assert second["created_activities"] == 0
    assert second["updated_activities"] == 0
