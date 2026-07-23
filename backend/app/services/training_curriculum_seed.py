"""Idempotently populate weekly references after normal content seeding.

Production upgrades receive these rows in migration 0032. A brand-new database
runs migrations before the ordinary seed scripts have created content, so
``seed_curriculum.py`` calls this synchronizer after its final commit. Existing
weekly configuration is never overwritten.
"""

from collections import defaultdict

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.capstone import CapstoneTemplate
from app.models.cli_lab import CliLab
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabTemplate
from app.models.learning import Lesson, Module
from app.models.quiz import Quiz
from app.models.ticket import Ticket
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.training_quiz_mapping import OPTIONAL_LESSON_IDS, mapping_metadata, video_is_required


VIDEO_WEEKS = {
    0: [182, 166, 168],
    1: [167, 176, 177],
    2: list(range(19, 21)) + list(range(30, 45)),
    3: list(range(108, 121)) + [131],
    4: list(range(1, 6)) + list(range(45, 53)) + [62, 169, 175, 180, 181],
    5: list(range(57, 61)) + list(range(125, 128)) + list(range(162, 166)),
    6: [139],
    7: [133, 134, 137, 138, 143, 144, 156, 157, 158],
    8: [6, 7, 8, 16, 17, 18, 61, 121, 122, 123, 124],
    9: [14, 15],
    10: [12, 13] + list(range(21, 30)),
    11: [9, 10, 11],
    12: [141, 142, 160],
    13: [140],
    15: [135, 136],
    16: [178, 179],
    17: [170],
    18: [128, 129, 130],
    20: list(range(145, 156)) + [159, 161],
    21: list(range(53, 57)) + [132],
    23: [174],
    24: [171, 172, 173],
}

CLI_WEEKS = {
    "meet-cli-001": 1,
    "dev-nf-encap-001": 9,
    "dev-nf-checkpoint-001": 9,
    "dev-sw-act-01": 10,
    "dev-sw-act-04": 10,
    "dev-sw-act-09": 10,
    "dev-sw-act-14": 10,
    "dev-sw-act-18": 10,
    "dev-sw-act-23": 11,
    "exam-first-switch": 11,
    "exam-ssh": 12,
}


def sync_initial_training_activities(db: Session) -> dict:
    """Populate references only when the migrated curriculum is still empty."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeek.__tablename__):
        return {"created": 0, "skipped": True, "reason": "migration_not_applied"}
    if db.query(TrainingWeekActivity.id).first():
        return {"created": 0, "skipped": True, "reason": "configuration_exists"}

    weeks = {row.week_number: row for row in db.query(TrainingWeek).all()}
    if not weeks:
        return {"created": 0, "skipped": True, "reason": "weeks_missing"}

    rows_by_week: dict[int, list[TrainingWeekActivity]] = defaultdict(list)

    def add(week_number, activity_type, content_ref, required, minutes=None, metadata=None):
        week = weeks.get(week_number)
        if week is None:
            return
        row = TrainingWeekActivity(
            training_week_id=week.id,
            stable_id=f"week-{week_number}-{activity_type}-{content_ref}",
            activity_type=activity_type,
            content_ref=str(content_ref),
            display_order=len(rows_by_week[week_number]) + 1,
            is_required=required,
            estimated_minutes=minutes,
            prerequisite_mode="soft",
            metadata_json=metadata or {},
        )
        rows_by_week[week_number].append(row)
        db.add(row)

    lessons = (
        db.query(Lesson, Module.module_order)
        .join(Module, Module.id == Lesson.module_id)
        .filter(
            Lesson.status == "published",
            (Module.module_order == 0) | Module.module_order.between(2, 25),
        )
        .order_by(Module.module_order, Lesson.lesson_order)
        .all()
    )
    for lesson, module_order in lessons:
        add(
            0 if module_order == 0 else module_order - 1,
            "lesson",
            lesson.id,
            lesson.id not in OPTIONAL_LESSON_IDS,
            lesson.estimated_minutes,
        )

    videos = {row.id: row for row in db.query(CurriculumVideo).filter(CurriculumVideo.active.is_(True)).all()}
    for week_number, video_ids in VIDEO_WEEKS.items():
        for video_id in video_ids:
            video = videos.get(video_id)
            if video:
                add(
                    week_number,
                    "video",
                    video.id,
                    video_is_required(week_number, video.id, video.job_relevance),
                    metadata=mapping_metadata(video.id),
                )

    quizzes = (
        db.query(Quiz)
        .filter(*student_visible_quiz_filters(), Quiz.week_number.between(0, 24))
        .order_by(Quiz.week_number, Quiz.id)
        .all()
    )
    for quiz in quizzes:
        add(quiz.week_number, "quiz", quiz.id, bool(quiz.is_required), 15)

    labs = (
        db.query(LabTemplate)
        .filter(LabTemplate.is_published.is_(True), LabTemplate.week_number.between(0, 24))
        .order_by(LabTemplate.week_number, LabTemplate.id)
        .all()
    )
    for lab in labs:
        add(lab.week_number, "guided_lab", lab.id, True, lab.estimated_minutes)

    first_ticket_week = set()
    tickets = db.query(Ticket).filter(Ticket.week_number.between(0, 24)).order_by(Ticket.week_number, Ticket.id).all()
    for ticket in tickets:
        required = ticket.week_number not in first_ticket_week
        add(ticket.week_number, "support_ticket", ticket.id, required, 30)
        first_ticket_week.add(ticket.week_number)

    cli_labs = {row.id: row for row in db.query(CliLab).filter(CliLab.id.in_(set(CLI_WEEKS))).all()}
    for lab_id, week_number in CLI_WEEKS.items():
        lab = cli_labs.get(lab_id)
        if lab:
            add(week_number, "networking_lab", lab.id, False, lab.est_minutes)

    capstones = (
        db.query(CapstoneTemplate)
        .filter(CapstoneTemplate.is_published.is_(True), CapstoneTemplate.week_number.between(0, 24))
        .order_by(CapstoneTemplate.week_number, CapstoneTemplate.id)
        .all()
    )
    for capstone in capstones:
        add(capstone.week_number, "capstone", capstone.id, False, (capstone.estimated_hours or 2) * 60)

    # Place a quiz after its exact title-linked video. Similar titles are never
    # treated as evidence of a relationship.
    quizzes_by_title = {quiz.title: quiz for quiz in quizzes}
    for week_number, rows in rows_by_week.items():
        for video in videos.values():
            quiz = quizzes_by_title.get(video.quiz_title)
            if quiz is None:
                continue
            video_row = next((row for row in rows if row.activity_type == "video" and row.content_ref == str(video.id)), None)
            quiz_row = next((row for row in rows if row.activity_type == "quiz" and row.content_ref == str(quiz.id)), None)
            if video_row and quiz_row:
                rows.remove(quiz_row)
                rows.insert(rows.index(video_row) + 1, quiz_row)
        for display_order, row in enumerate(rows, start=1):
            row.display_order = display_order

    db.commit()
    return {"created": sum(len(rows) for rows in rows_by_week.values()), "skipped": False}
