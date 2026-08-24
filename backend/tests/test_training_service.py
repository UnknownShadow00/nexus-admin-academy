from datetime import datetime, timezone

import pytest

from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson, Module
from app.models.lesson_notes import StudentLessonNote
from app.models.lesson_progress import StudentLessonProgress
from app.models.quiz import (
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_STATUS_PUBLISHED,
    Question,
    Quiz,
    QuizAttempt,
)
from app.models.ticket import Ticket, TicketSubmission
from app.models.service_desk import ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.training_service import (
    build_training_module,
    build_training_overview,
    build_training_progress,
    build_training_week,
    validate_training_curriculum,
)
from app.services.curriculum_structure import (
    MODULES,
    STAGES,
    ModuleDefinition,
    StageDefinition,
    learning_role_for,
    structure_definition_issues,
)
from app.services.training_curriculum_seed import (
    reconcile_week_zero_requirements,
    sync_initial_training_activities,
    sync_advanced_networking_resequence,
)
from app.services.training_curriculum_seed import VIDEO_WEEKS
from app.services.training_quiz_mapping import VIDEO_QUIZ_MAPPINGS
from conftest import make_student


@pytest.fixture()
def student(db):
    return make_student(db, "training-service-student")


def add_week(db, number, title=None, *, active=True, requires_previous=True):
    week = TrainingWeek(
        week_number=number,
        display_order=number,
        title=title or f"Week {number}",
        description=f"Training for week {number}",
        learning_goals=[f"Goal {number}"],
        estimated_minutes=120,
        is_active=active,
        requires_previous_week=requires_previous,
    )
    db.add(week)
    db.flush()
    return week


def add_activity(db, week, stable_id, activity_type, content_ref, order, *, required=True, metadata=None):
    activity = TrainingWeekActivity(
        training_week_id=week.id,
        stable_id=stable_id,
        activity_type=activity_type,
        content_ref=str(content_ref),
        display_order=order,
        is_required=required,
        estimated_minutes=10,
        metadata_json=metadata or {},
    )
    db.add(activity)
    db.flush()
    return activity


def add_video(db, video_id=10, *, title="How Computers Work", quiz_title=None):
    video = CurriculumVideo(
        id=video_id,
        video_key=f"video-{video_id}",
        section="Computer Basics",
        section_order=1,
        title=title,
        duration="10:00",
        url="https://example.test/video",
        quiz_title=quiz_title,
        exam_code="220-1201",
        job_relevance="job_critical",
        video_order=video_id,
        active=True,
    )
    db.add(video)
    db.flush()
    return video


def add_quiz(db, quiz_id=20, *, title="Computer Basics Quiz", week=1, visible=True):
    quiz = Quiz(
        id=quiz_id,
        title=title,
        question_count=2,
        week_number=week,
        domain_id="1.0",
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED if visible else "needs_edit",
        answer_keys_validated=visible,
        explanations_complete=visible,
        is_active=True,
        is_required=True,
        show_in_weekly_checklist=True,
        show_in_practice_library=False,
    )
    db.add(quiz)
    db.flush()
    for index in range(2):
        db.add(
            Question(
                quiz_id=quiz.id,
                question_text=f"Question {index}",
                option_a="A",
                option_b="B",
                option_c="C",
                option_d="D",
                correct_answer="A",
                explanation="Because A",
            )
        )
    db.flush()
    return quiz


def test_week_and_activity_ordering_and_optional_items(db, student):
    add_week(db, 2)
    week_one = add_week(db, 1)
    video = add_video(db)
    add_activity(db, week_one, "w1-video", "video", video.id, 20)
    add_activity(db, week_one, "w1-optional-review", "review", "week-1", 30, required=False)
    add_activity(db, week_one, "w1-missing", "video", 999, 10)
    db.commit()

    overview = build_training_overview(db, student)

    assert [week["week_number"] for week in overview["weeks"]] == [1, 2]
    detail = build_training_week(db, student, week_one.week_number)
    assert [item["stable_id"] for item in detail["activities"]] == ["w1-missing", "w1-video", "w1-optional-review"]
    assert detail["required_total"] == 2
    assert detail["optional_total"] == 1


def test_stage_module_definitions_have_stable_unique_ids_and_one_week_mapping():
    assert structure_definition_issues() == []
    assert len({stage.stable_id for stage in STAGES}) == len(STAGES)
    assert len({module.stable_id for module in MODULES}) == len(MODULES)
    assert len({module.source_week_number for module in MODULES}) == len(MODULES) == 35


def test_structure_validation_fails_loudly_for_duplicate_or_orphaned_metadata():
    stages = (
        StageDefinition("stage.test", "Test", "Test stage", 0),
        StageDefinition("stage.test", "Duplicate", "Duplicate stage", 1),
    )
    modules = (
        ModuleDefinition("module.test.one", "stage.missing", "One", "One", 0, 1),
        ModuleDefinition("module.test.two", "stage.test", "Two", "Two", 0, 1),
    )
    codes = {issue["code"] for issue in structure_definition_issues(stages, modules)}
    assert {"DUPLICATE_STAGE_ID", "MISSING_STAGE", "DUPLICATE_MODULE_MAPPING"}.issubset(codes)


def test_learning_roles_are_presentation_metadata_not_completion_evidence():
    assert learning_role_for("lesson") == "learn"
    assert learning_role_for("quiz") == "check"
    assert learning_role_for("guided_lab") == "practice"
    assert learning_role_for("service_desk_scenario") == "troubleshoot"
    assert learning_role_for("capstone") == "prove"
    assert learning_role_for("guided_lab", {"learning_role": "prove"}) == "prove"


def test_fresh_advanced_and_completed_students_resolve_stages_and_modules(db, student):
    weeks = [add_week(db, number, requires_previous=number > 0) for number in range(3)]
    videos = [add_video(db, 100 + number, title=f"Video {number}") for number in range(3)]
    for number, (week, video) in enumerate(zip(weeks, videos, strict=True)):
        add_activity(db, week, f"activity-{number}", "video", video.id, 1)
    db.commit()

    fresh = build_training_overview(db, student)
    assert fresh["current_stage"]["stable_id"] == "stage.orientation"
    assert fresh["current_module"]["stable_id"] == "module.orientation.nexus"
    assert fresh["current_activity"]["stable_id"] == "activity-0"

    db.add(VideoWatch(student_id=student.id, video_key=videos[0].video_key))
    db.commit()
    advanced = build_training_overview(db, student)
    assert advanced["current_stage"]["stable_id"] == "stage.endpoint_foundations"
    assert advanced["current_module"]["stable_id"] == "module.endpoint.support_workflow"
    assert build_training_module(db, student, "module.orientation.nexus")["is_complete"] is True

    db.add_all(VideoWatch(student_id=student.id, video_key=video.video_key) for video in videos[1:])
    db.commit()
    completed = build_training_overview(db, student)
    assert completed["training_complete"] is True
    assert completed["current_module"]["stable_id"] == "module.endpoint.pc_hardware"


def test_existing_activity_completion_remains_authoritative_after_module_mapping(db, student):
    week = add_week(db, 5, requires_previous=False)
    video = add_video(db, 105, title="Existing completed activity")
    activity = add_activity(db, week, "stable-existing-completion", "video", video.id, 1)
    db.add(VideoWatch(student_id=student.id, video_key=video.video_key))
    db.commit()

    detail = build_training_module(db, student, "module.windows.troubleshooting")

    assert detail["activities"][0]["stable_id"] == activity.stable_id
    assert detail["activities"][0]["complete"] is True
    assert detail["is_complete"] is True


def test_unmapped_active_activity_and_invalid_learning_role_fail_validation(db, student):
    week = add_week(db, 99, requires_previous=False)
    video = add_video(db, 199)
    add_activity(db, week, "unmapped", "video", video.id, 1, metadata={"learning_role": "mastered"})
    db.commit()

    validation = validate_training_curriculum(db)
    codes = {issue["code"] for issue in validation["issues"]}
    assert {"UNMAPPED_ACTIVE_WEEK", "UNMAPPED_ACTIVE_ACTIVITY", "INVALID_LEARNING_ROLE"}.issubset(codes)
    assert validation["unmapped_activity_count"] == 1
    assert validation["valid"] is False


def test_sequence_drift_detected_and_resolved_by_advanced_networking_resequence(db, student):
    # Minimal weeks at the real week_numbers this Phase 4A.1 check cares
    # about: 9 (last support-networking week, unaffected), 10-12 (advanced
    # networking, to be moved later), 13-15 (Identity & Access, to move
    # earlier). display_order starts equal to week_number, matching today's
    # un-resequenced data.
    for number in (9, 10, 11, 12, 13, 14, 15):
        week = add_week(db, number, requires_previous=False)
        video = add_video(db, 1000 + number, title=f"Week {number} video")
        add_activity(db, week, f"week-{number}-video", "video", video.id, 1)
    db.commit()

    # Before resequencing, display_order still matches week_number, which
    # contradicts the intended Stage order in curriculum_structure.py (the
    # network_administration Stage's modules -- weeks 10-12 -- are supposed
    # to come after identity_access's modules -- weeks 13-15).
    before = validate_training_curriculum(db)
    assert "SEQUENCE_DRIFT" in {issue["code"] for issue in before["issues"]}

    result = sync_advanced_networking_resequence(db)
    assert result == {"weeks_checked": 6, "weeks_updated": 6}

    after = validate_training_curriculum(db)
    assert "SEQUENCE_DRIFT" not in {issue["code"] for issue in after["issues"]}

    # Idempotent: a second run changes nothing.
    assert sync_advanced_networking_resequence(db) == {"weeks_checked": 6, "weeks_updated": 0}

    # week_number -- the stable identity key everything else keys off -- is
    # untouched; only display_order moves.
    weeks_by_number = {
        w.week_number: w
        for w in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_(range(9, 16))).all()
    }
    assert weeks_by_number[9].display_order == 9
    assert weeks_by_number[10].display_order == 13
    assert weeks_by_number[11].display_order == 14
    assert weeks_by_number[12].display_order == 15
    assert weeks_by_number[13].display_order == 10
    assert weeks_by_number[14].display_order == 11
    assert weeks_by_number[15].display_order == 12
    for number in range(9, 16):
        assert weeks_by_number[number].week_number == number


def test_service_desk_activity_is_validated_and_completed_only_by_passed_attempt(db, student):
    week = add_week(db, 1, requires_previous=False)
    scenario = ServiceDeskScenario(stable_key="training-service-desk", title="Training Service Desk", description="A test scenario for curriculum integration.", category="Identity", difficulty=1, status="active")
    db.add(scenario)
    db.flush()
    version = ServiceDeskScenarioVersion(scenario_id=scenario.id, version_number=1, definition_json={}, definition_hash="a" * 64, validation_status="valid", status="published")
    db.add(version)
    db.flush()
    add_activity(db, week, "w1-service-desk", "service_desk_scenario", scenario.stable_key, 1)
    db.commit()

    assert validate_training_curriculum(db)["valid"] is True
    before = build_training_week(db, student, 1)["activities"][0]
    assert before["complete"] is False
    assert before["destination_route"] == "/service-desk/tickets/TRAINING-SERVICE-DESK?returnTo=%2Ftraining%2Fmodule%2Fmodule.endpoint.support_workflow"

    db.add(ServiceDeskAttempt(student_id=student.id, scenario_version_id=version.id, mode="learning", status="completed", current_state={}, current_state_hash="b" * 64, state_version=0, attempt_number=1, score=100, passed=True))
    db.commit()
    after = build_training_week(db, student, 1)["activities"][0]
    assert after["complete"] is True


def test_required_activity_blocks_next_week_but_optional_does_not(db, student):
    week_one = add_week(db, 1)
    week_two = add_week(db, 2)
    required_video = add_video(db, 10)
    optional_video = add_video(db, 11, title="Optional Deep Dive")
    add_activity(db, week_one, "w1-required", "video", required_video.id, 1, required=True)
    add_activity(db, week_one, "w1-optional", "video", optional_video.id, 2, required=False)
    add_activity(db, week_two, "w2-required", "video", optional_video.id, 1, required=True)
    db.commit()

    before = build_training_overview(db, student)
    assert before["current_week"]["week_number"] == 1
    assert before["weeks"][1]["status"] == "locked"
    assert before["next_activity"]["stable_id"] == "w1-required"

    db.add(VideoWatch(student_id=student.id, video_key=required_video.video_key))
    db.commit()
    after = build_training_overview(db, student)
    assert after["weeks"][0]["status"] == "complete"
    assert after["weeks"][1]["status"] == "in_progress"
    assert after["current_week"]["week_number"] == 2
    assert after["next_activity"]["stable_id"] == "w2-required"


def test_lesson_note_does_not_complete_a_required_training_activity(db, student):
    week_one = add_week(db, 1, requires_previous=False)
    week_two = add_week(db, 2)
    module = Module(code="MOD-001", title="Week 1", module_order=1)
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="Read a real lesson", lesson_order=1, status="published")
    db.add(lesson)
    db.flush()
    add_activity(db, week_one, "w1-lesson", "lesson", lesson.id, 1)
    add_activity(db, week_two, "w2-review", "review", "week-2", 1)
    db.add(StudentLessonNote(student_id=student.id, lesson_id=lesson.id, content="Optional study note."))
    db.commit()

    before = build_training_overview(db, student)
    assert before["weeks"][0]["required_complete"] == 0
    assert before["weeks"][0]["required_total"] == 1
    assert before["weeks"][1]["status"] == "locked"
    assert before["next_activity"]["stable_id"] == "w1-lesson"

    db.add(StudentLessonProgress(student_id=student.id, lesson_id=lesson.id, completed_at=datetime.now(timezone.utc)))
    db.commit()
    after = build_training_overview(db, student)
    assert after["weeks"][0]["required_complete"] == 1
    assert after["weeks"][0]["completion_percent"] == 100.0
    assert after["weeks"][1]["status"] == "complete"  # a review activity is intentionally untracked


def test_video_quiz_lab_ticket_and_networking_completion_are_server_derived(db, student):
    week = add_week(db, 1, requires_previous=False)
    video = add_video(db, quiz_title="Computer Basics Quiz")
    quiz = add_quiz(db)
    lab = LabTemplate(
        id=30,
        title="Identify Components",
        description="Identify real components",
        difficulty=1,
        week_number=1,
        is_published=True,
        environment_requirements={},
        success_criteria={},
        required_evidence={},
        hints={},
    )
    ticket = Ticket(
        id=40,
        title="Laptop will not start",
        description="Diagnose the laptop",
        difficulty=1,
        week_number=1,
        objective_ids=[],
        domain_id="1.0",
        required_checkpoints={},
        required_evidence={},
        scoring_anchors={},
        hints=[],
        parameters={},
    )
    cli_lab = CliLab(
        id="cli-basics",
        compartment_id="meet-the-cli",
        vendor_id="cisco",
        title="Meet the CLI",
        order_index=1,
        content={},
    )
    capstone = CapstoneTemplate(
        id=50,
        title="Foundation Capstone",
        week_number=1,
        is_published=True,
        requirements={},
        deliverables={},
        rubric={},
    )
    db.add_all([lab, ticket, cli_lab, capstone])
    db.flush()
    activities = [
        add_activity(db, week, "video", "video", video.id, 1),
        add_activity(db, week, "quiz", "quiz", quiz.id, 2),
        add_activity(db, week, "lab", "guided_lab", lab.id, 3),
        add_activity(db, week, "ticket", "support_ticket", ticket.id, 4),
        add_activity(db, week, "cli", "networking_lab", cli_lab.id, 5),
        add_activity(db, week, "capstone", "capstone", capstone.id, 6, required=False),
    ]
    db.commit()

    initial = build_training_week(db, student, 1)
    assert [item["status"] for item in initial["activities"]] == ["not_started"] * 6
    assert initial["activities"][0]["linked_quiz"]["id"] == quiz.id
    assert initial["activities"][0]["linked_quiz"]["action"] == "take"

    db.add(VideoWatch(student_id=student.id, video_key=video.video_key))
    db.add(
        QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=[],
            score=2,
            best_score=2,
            first_attempt_xp=10,
            xp_awarded=10,
        )
    )
    db.add(LabRun(lab_template_id=lab.id, student_id=student.id, status="submitted"))
    db.add(
        TicketSubmission(
            student_id=student.id,
            ticket_id=ticket.id,
            writeup="Complete",
            xp_awarded=10,
            status="passed",
            ai_feedback={},
            collaborator_ids=[],
            methodology_steps_mentioned={},
        )
    )
    db.add(CliLabAttempt(student_id=student.id, lab_id=cli_lab.id, completed_at=quiz.created_at, command_log=[]))
    db.add(CapstoneRun(capstone_template_id=capstone.id, student_id=student.id, status="submitted", passed=False))
    db.commit()

    complete = build_training_week(db, student, 1)
    by_id = {item["stable_id"]: item for item in complete["activities"]}
    assert all(by_id[item.stable_id]["complete"] for item in activities)
    assert by_id["video"]["linked_quiz"]["action"] == "review"
    assert by_id["video"]["linked_quiz"]["score"] == 2
    assert complete["required_complete"] == complete["required_total"]


def test_structured_lab_requires_a_passing_graded_submission(db, student):
    """A deterministic (structured_*) lab must not count as complete just
    because a LabRun row exists in "submitted" status — it must have gone
    through server-side structured grading and scored a pass. This also
    covers the case of a lab template that was rebuilt in place: an old
    free-text submission against the same template id (no structured_feedback)
    must not silently satisfy the new exercise."""
    week = add_week(db, 2, requires_previous=False)
    lab = LabTemplate(
        id=31,
        title="Structured Hardware Check",
        description="Deterministic questions",
        lab_type="structured_identification",
        difficulty=1,
        week_number=2,
        is_published=True,
        environment_requirements={},
        success_criteria={"questions": [{"id": "q1", "correct": ["a"]}]},
        required_evidence={},
        hints={},
    )
    db.add(lab)
    db.flush()
    activity = add_activity(db, week, "lab", "guided_lab", lab.id, 1)
    db.commit()

    # Legacy free-text submission against the same template id: submitted,
    # but never graded through the structured path.
    db.add(LabRun(lab_template_id=lab.id, student_id=student.id, status="submitted"))
    db.commit()
    legacy = build_training_week(db, student, 2)
    legacy_activity = {item["stable_id"]: item for item in legacy["activities"]}[activity.stable_id]
    assert legacy_activity["complete"] is False

    # A graded-but-failing structured attempt must not count either.
    db.query(LabRun).filter_by(lab_template_id=lab.id, student_id=student.id).delete()
    db.add(
        LabRun(
            lab_template_id=lab.id,
            student_id=student.id,
            status="submitted",
            final_score=50,
            structured_feedback={"questions": [{"id": "q1", "correct": False}], "score_pct": 50},
        )
    )
    db.commit()
    failing = build_training_week(db, student, 2)
    failing_activity = {item["stable_id"]: item for item in failing["activities"]}[activity.stable_id]
    assert failing_activity["complete"] is False

    # A passing structured attempt counts.
    db.query(LabRun).filter_by(lab_template_id=lab.id, student_id=student.id).delete()
    db.add(
        LabRun(
            lab_template_id=lab.id,
            student_id=student.id,
            status="submitted",
            final_score=100,
            structured_feedback={"questions": [{"id": "q1", "correct": True}], "score_pct": 100},
        )
    )
    db.commit()
    passing = build_training_week(db, student, 2)
    passing_activity = {item["stable_id"]: item for item in passing["activities"]}[activity.stable_id]
    assert passing_activity["complete"] is True


def test_failed_required_quiz_blocks_until_passed(db, student):
    week = add_week(db, 1, requires_previous=False)
    quiz = add_quiz(db)
    add_activity(db, week, "required-quiz", "quiz", quiz.id, 1, required=True)
    db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, results=[], score=1, best_score=1, first_attempt_xp=0, xp_awarded=0))
    db.commit()

    failed = build_training_week(db, student, 1)
    assert failed["activities"][0]["status"] == "in_progress"
    assert failed["activities"][0]["complete"] is False
    assert failed["activities"][0]["score_percent"] == 50

    db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, results=[], score=2, best_score=2, first_attempt_xp=0, xp_awarded=0))
    db.commit()
    assert build_training_week(db, student, 1)["activities"][0]["complete"] is True


def test_server_graded_ticket_completes_week_without_waiting_for_mentor(db, student):
    week = add_week(db, 1, requires_previous=False)
    ticket = Ticket(
        id=40,
        title="Beginner ticket",
        description="Submit a diagnosis",
        difficulty=1,
        week_number=1,
        objective_ids=[],
        domain_id="1.0",
        required_checkpoints={},
        required_evidence={},
        scoring_anchors={},
        hints=[],
        parameters={},
    )
    db.add(ticket)
    db.flush()
    add_activity(db, week, "ticket", "support_ticket", ticket.id, 1)
    db.add(TicketSubmission(
        student_id=student.id,
        ticket_id=ticket.id,
        writeup="A server-graded response",
        xp_awarded=0,
        status="pending",
        final_score=7,
        graded_at=datetime.now(timezone.utc),
        ai_feedback={},
        collaborator_ids=[],
        methodology_steps_mentioned={},
    ))
    db.commit()

    detail = build_training_week(db, student, 1)
    assert detail["activities"][0]["complete"] is True
    assert detail["is_complete"] is True


def test_disabled_and_empty_weeks_do_not_block_final_completion(db, student):
    add_week(db, 1, active=False)
    add_week(db, 2, active=True, requires_previous=False)
    db.commit()

    overview = build_training_overview(db, student)
    assert len(overview["weeks"]) == 1
    assert overview["training_complete"] is True
    assert overview["next_activity"] is None


def test_broken_hidden_and_untracked_required_references_are_reported(db, student):
    week = add_week(db, 1, requires_previous=False)
    hidden_quiz = add_quiz(db, visible=False)
    add_activity(db, week, "missing-video", "video", 999, 1)
    add_activity(db, week, "hidden-quiz", "quiz", hidden_quiz.id, 2)
    add_activity(db, week, "required-terminal", "terminal_exercise", "terminal", 3)
    db.commit()

    validation = validate_training_curriculum(db)
    codes = {issue["code"] for issue in validation["issues"]}
    assert {"BROKEN_REFERENCE", "QUIZ_NOT_STUDENT_VISIBLE", "UNTRACKED_REQUIRED_ACTIVITY"}.issubset(codes)
    assert validation["valid"] is False


def test_progress_uses_one_required_activity_denominator(db, student):
    week = add_week(db, 1, requires_previous=False)
    first = add_video(db, 10)
    second = add_video(db, 11, title="Second Video")
    add_activity(db, week, "first", "video", first.id, 1)
    add_activity(db, week, "second", "video", second.id, 2)
    add_activity(db, week, "optional", "video", second.id, 3, required=False)
    db.add(VideoWatch(student_id=student.id, video_key=first.video_key))
    db.commit()

    progress = build_training_progress(db, student)
    assert progress["overall_training"]["completed"] == 1
    assert progress["overall_training"]["total"] == 2
    assert progress["overall_training"]["percent"] == 50
    assert progress["videos"]["watched"] == 1
    assert progress["videos"]["total"] == 2


def test_reviewed_mapping_covers_every_seed_video_once():
    assigned = [video_id for video_ids in VIDEO_WEEKS.values() for video_id in video_ids]
    assert len(assigned) == 137
    assert len(set(assigned)) == 137
    assert set(assigned) == set(VIDEO_QUIZ_MAPPINGS)
    assert all(mapping.quiz_id > 0 for mapping in VIDEO_QUIZ_MAPPINGS.values())
    confidence_counts = {
        confidence: sum(mapping.confidence == confidence for mapping in VIDEO_QUIZ_MAPPINGS.values())
        for confidence in {mapping.confidence for mapping in VIDEO_QUIZ_MAPPINGS.values()}
    }
    assert confidence_counts == {"Exact": 5, "Strong topical": 92, "Week-level fallback": 40}


def test_shared_quiz_updates_each_video_but_counts_once(db, student):
    week = add_week(db, 1, requires_previous=False)
    quiz = add_quiz(db)
    first = add_video(db, 10)
    second = add_video(db, 11, title="Related Video")
    metadata = {
        "quiz_id": quiz.id,
        "quiz_mapping_basis": "topic_group",
        "quiz_mapping_confidence": "Strong topical",
        "quiz_mapping_evidence": "Tested topic group.",
    }
    add_activity(db, week, "first", "video", first.id, 1, metadata=metadata)
    add_activity(db, week, "second", "video", second.id, 2, metadata=metadata)
    add_activity(db, week, "quiz", "quiz", quiz.id, 3)
    db.add(QuizAttempt(student_id=student.id, quiz_id=quiz.id, answers={}, results=[], score=2, best_score=2, first_attempt_xp=0, xp_awarded=0))
    db.commit()

    detail = build_training_week(db, student, 1)
    video_rows = [item for item in detail["activities"] if item["activity_type"] == "video"]
    assert {item["linked_quiz"]["action"] for item in video_rows} == {"review"}
    assert {item["linked_quiz"]["score_percent"] for item in video_rows} == {100}
    progress = build_training_progress(db, student)
    assert progress["quizzes"] == {
        "completed": 1,
        "total": 1,
        "percent": 100,
        "average_score_percent": 100,
        "best_score_percent": 100,
    }
    assert progress["overall_training"]["total"] == 3


def test_curriculum_health_rejects_invalid_mapping_and_hard_cycle(db, student):
    week = add_week(db, 1, requires_previous=False)
    video = add_video(db)
    first = add_activity(
        db,
        week,
        "first",
        "video",
        video.id,
        1,
        metadata={"quiz_id": 999, "quiz_mapping_basis": "topic_group"},
    )
    second = add_activity(db, week, "second", "review", "week-1", 2)
    first.prerequisite_activity_id = second.id
    first.prerequisite_mode = "hard"
    second.prerequisite_activity_id = first.id
    second.prerequisite_mode = "hard"
    db.commit()

    validation = validate_training_curriculum(db)
    codes = {issue["code"] for issue in validation["issues"]}
    assert "VIDEO_QUIZ_MAPPING_INVALID" in codes
    assert "PREREQUISITE_CYCLE" in codes
    assert validation["valid"] is False


def test_post_seed_curriculum_sync_is_idempotent(db, student):
    week = add_week(db, 11, requires_previous=False)
    video = add_video(db, 10)
    db.commit()

    first = sync_initial_training_activities(db)
    second = sync_initial_training_activities(db)

    rows = db.query(TrainingWeekActivity).filter(TrainingWeekActivity.training_week_id == week.id).all()
    assert first["created"] == 1
    assert second == {"created": 0, "skipped": True, "reason": "configuration_exists"}
    assert len(rows) == 1
    assert rows[0].content_ref == str(video.id)


def test_week_zero_reconciliation_keeps_only_orientation_and_checkpoint_required(db):
    week = add_week(db, 0, requires_previous=False)
    module = Module(code="MOD-000", title="Week 0", module_order=0)
    db.add(module)
    db.flush()
    orientation = Lesson(
        module_id=module.id,
        title="Welcome to Nexus: Your First Week",
        lesson_order=1,
        status="published",
    )
    retired = Lesson(module_id=module.id, title="Retired filler", lesson_order=2, status="draft")
    quiz = Quiz(
        title="Ticketing Systems Quiz",
        week_number=0,
        status=QUIZ_STATUS_PUBLISHED,
        is_required=True,
    )
    db.add_all([orientation, retired, quiz])
    db.flush()
    activities = [
        add_activity(db, week, "orientation", "lesson", orientation.id, 1, required=True),
        add_activity(db, week, "video-a", "video", 166, 2, required=True),
        add_activity(db, week, "video-b", "video", 168, 3, required=True),
        add_activity(db, week, "checkpoint", "quiz", quiz.id, 4, required=True),
        add_activity(db, week, "retired", "lesson", retired.id, 5, required=True),
    ]
    db.commit()

    first = reconcile_week_zero_requirements(db)
    second = reconcile_week_zero_requirements(db)

    assert first == {"updated": 3, "skipped": False}
    assert second == {"updated": 0, "skipped": False}
    assert [row.is_required for row in activities] == [True, False, False, True, False]
