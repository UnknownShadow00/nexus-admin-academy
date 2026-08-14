from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.command_reference import CommandReference
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson
from app.models.lesson_progress import StudentLessonProgress
from app.models.progression import Role, StudentRole
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.service_desk import ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.mastery_service import list_student_mastery
from app.services.progression_service import get_promotion_status
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.training_quiz_mapping import CONFIDENCE_BY_BASIS, EXACT, TOPIC_GROUP, WEEK_FALLBACK


PRACTICE_ACTIVITY_TYPES = {
    "guided_lab",
    "networking_lab",
    "command_exercise",
    "terminal_exercise",
    "capstone",
    "service_desk_scenario",
}
AT_RISK_INACTIVITY_HOURS = 72
UNTRACKED_ACTIVITY_TYPES = {"command_exercise", "terminal_exercise"}
ACTIVITY_LABELS = {
    "video": "Video",
    "quiz": "Quiz",
    "lesson": "Course Lesson",
    "guided_lab": "Guided Lab",
    "networking_lab": "Networking Lab",
    "command_exercise": "Command Exercise",
    "terminal_exercise": "Terminal Exercise",
    "review": "Weekly Review",
    "capstone": "Capstone",
    "service_desk_scenario": "Service Desk Scenario",
}


def _int_ref(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _duration_minutes(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parts = [int(part) for part in value.split(":")]
    except (TypeError, ValueError):
        return None
    if len(parts) == 2:
        return max(1, round(parts[0] + parts[1] / 60))
    if len(parts) == 3:
        return max(1, round(parts[0] * 60 + parts[1] + parts[2] / 60))
    return None


def _latest_by(rows, key):
    result = {}
    for row in rows:
        result.setdefault(key(row), row)
    return result


@dataclass
class _ResolvedContent:
    title: str
    description: str | None
    destination_route: str | None
    external_url: str | None = None
    estimated_minutes: int | None = None
    job_relevance: str | None = None
    linked_quiz: dict | None = None
    permission_locked: bool = False
    permission_reason: str | None = None


class _TrainingContext:
    def __init__(self, db: Session, student: Student, activities: list[TrainingWeekActivity]):
        self.db = db
        self.student = student
        self.activities = activities
        refs: dict[str, set[str]] = defaultdict(set)
        for activity in activities:
            refs[activity.activity_type].add(activity.content_ref)

        def integer_refs(activity_type):
            return {value for ref in refs[activity_type] if (value := _int_ref(ref)) is not None}

        mapped_quiz_ids = {
            quiz_id
            for activity in activities
            if activity.activity_type == "video"
            and (quiz_id := _int_ref((activity.metadata_json or {}).get("quiz_id"))) is not None
        }

        self.videos = {
            row.id: row
            for row in db.query(CurriculumVideo)
            .filter(CurriculumVideo.id.in_(integer_refs("video")), CurriculumVideo.active.is_(True))
            .all()
        } if refs["video"] else {}
        requested_quiz_ids = integer_refs("quiz") | mapped_quiz_ids
        self.quizzes = {
            row.id: row
            for row in db.query(Quiz)
            .options(selectinload(Quiz.questions))
            .filter(Quiz.id.in_(requested_quiz_ids), *student_visible_quiz_filters())
            .all()
        } if requested_quiz_ids else {}
        visible_quizzes = (
            db.query(Quiz)
            .options(selectinload(Quiz.questions))
            .filter(*student_visible_quiz_filters())
            .all()
        )
        self.visible_quizzes_by_title = {row.title: row for row in visible_quizzes}
        self.lessons = {
            row.id: row for row in db.query(Lesson).filter(Lesson.id.in_(integer_refs("lesson"))).all()
        } if refs["lesson"] else {}
        self.labs = {
            row.id: row
            for row in db.query(LabTemplate)
            .filter(LabTemplate.id.in_(integer_refs("guided_lab")), LabTemplate.is_published.is_(True))
            .all()
        } if refs["guided_lab"] else {}
        # Compatibility read only: migration 0043 removes all live references.
        # This preserves a coherent read of a pre-migration historical week
        # without ever seeding or creating new Support Ticket requirements.
        self.tickets = {
            row.id: row for row in db.query(Ticket).filter(Ticket.id.in_(integer_refs("support_ticket"))).all()
        } if refs["support_ticket"] else {}
        self.cli_labs = {
            row.id: row for row in db.query(CliLab).filter(CliLab.id.in_(refs["networking_lab"])).all()
        } if refs["networking_lab"] else {}
        self.commands = {
            row.id: row
            for row in db.query(CommandReference).filter(CommandReference.id.in_(integer_refs("command_exercise"))).all()
        } if refs["command_exercise"] else {}
        self.capstones = {
            row.id: row
            for row in db.query(CapstoneTemplate)
            .filter(CapstoneTemplate.id.in_(integer_refs("capstone")), CapstoneTemplate.is_published.is_(True))
            .all()
        } if refs["capstone"] else {}
        self.service_desk_scenarios = {
            row.stable_key: row
            for row in db.query(ServiceDeskScenario).filter(ServiceDeskScenario.stable_key.in_(refs["service_desk_scenario"])).all()
        } if refs["service_desk_scenario"] else {}
        service_version_ids = [
            row.id for row in db.query(ServiceDeskScenarioVersion.id)
            .join(ServiceDeskScenario, ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id)
            .filter(ServiceDeskScenario.stable_key.in_(set(self.service_desk_scenarios)), ServiceDeskScenarioVersion.status == "published")
            .all()
        ]
        service_attempts = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.student_id == student.id, ServiceDeskAttempt.scenario_version_id.in_(service_version_ids), ServiceDeskAttempt.passed.is_(True)).order_by(ServiceDeskAttempt.completed_at.desc()).all() if service_version_ids else []
        self.service_desk_completed_attempts = _latest_by(
            service_attempts, lambda row: row.scenario_version_id
        )

        video_keys = [row.video_key for row in self.videos.values()]
        self.watches = {
            row.video_key: row
            for row in db.query(VideoWatch)
            .filter(VideoWatch.student_id == student.id, VideoWatch.video_key.in_(video_keys))
            .all()
        } if video_keys else {}
        quiz_ids = set(self.quizzes) | {quiz.id for quiz in self.visible_quizzes_by_title.values()}
        attempts = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.student_id == student.id, QuizAttempt.quiz_id.in_(quiz_ids))
            .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
            .all()
        ) if quiz_ids else []
        self.attempts: dict[int, list[QuizAttempt]] = defaultdict(list)
        for attempt in attempts:
            self.attempts[attempt.quiz_id].append(attempt)
        self.lesson_progress = {
            row.lesson_id: row
            for row in db.query(StudentLessonProgress)
            .filter(
                StudentLessonProgress.student_id == student.id,
                StudentLessonProgress.lesson_id.in_(set(self.lessons)),
                StudentLessonProgress.completed_at.isnot(None),
            )
            .all()
        } if self.lessons else {}
        lab_runs = (
            db.query(LabRun)
            .filter(LabRun.student_id == student.id, LabRun.lab_template_id.in_(set(self.labs)))
            .order_by(LabRun.created_at.desc(), LabRun.id.desc())
            .all()
        ) if self.labs else []
        self.lab_runs = _latest_by(lab_runs, lambda row: row.lab_template_id)
        ticket_submissions = (
            db.query(TicketSubmission)
            .filter(TicketSubmission.student_id == student.id, TicketSubmission.ticket_id.in_(set(self.tickets)))
            .order_by(TicketSubmission.submitted_at.desc(), TicketSubmission.id.desc())
            .all()
        ) if self.tickets else []
        self.ticket_submissions = _latest_by(ticket_submissions, lambda row: row.ticket_id)
        cli_attempts = (
            db.query(CliLabAttempt)
            .filter(CliLabAttempt.student_id == student.id, CliLabAttempt.lab_id.in_(set(self.cli_labs)))
            .order_by(CliLabAttempt.completed_at.desc(), CliLabAttempt.id.desc())
            .all()
        ) if self.cli_labs else []
        self.cli_attempts = _latest_by(cli_attempts, lambda row: row.lab_id)
        capstone_runs = (
            db.query(CapstoneRun)
            .filter(CapstoneRun.student_id == student.id, CapstoneRun.capstone_template_id.in_(set(self.capstones)))
            .order_by(CapstoneRun.created_at.desc(), CapstoneRun.id.desc())
            .all()
        ) if self.capstones else []
        self.capstone_runs = _latest_by(capstone_runs, lambda row: row.capstone_template_id)
        self.student_rank = int(
            db.query(func.coalesce(func.max(Role.rank_order), 1))
            .select_from(StudentRole)
            .join(Role, StudentRole.role_id == Role.id)
            .filter(StudentRole.student_id == student.id)
            .scalar()
            or 1
        )
        self.roles = {row.id: row for row in db.query(Role).all()}

    def _quiz_progress(self, quiz: Quiz) -> dict:
        attempts = self.attempts.get(quiz.id, [])
        total = len(quiz.questions) or int(quiz.question_count or 0)
        best = max((max(int(row.score or 0), int(row.best_score or 0)) for row in attempts), default=0)
        percent = round(best / total * 100) if total else 0
        latest = attempts[0] if attempts else None
        return {
            "attempted": bool(attempts),
            "passed": bool(total and best * 100 >= total * 70),
            "score": best if attempts else None,
            "total": total,
            "score_percent": percent if attempts else None,
            "completed_at": latest.completed_at if latest else None,
        }

    def resolve(self, activity: TrainingWeekActivity) -> _ResolvedContent | None:
        ref = _int_ref(activity.content_ref)
        week_number = activity.week.week_number
        if activity.activity_type == "video":
            video = self.videos.get(ref)
            if not video:
                return None
            metadata = activity.metadata_json or {}
            mapped_quiz_id = _int_ref(metadata.get("quiz_id"))
            quiz = self.quizzes.get(mapped_quiz_id)
            # Compatibility only for pre-0033 databases while an operator is
            # applying the additive mapping migration. New mappings never rely
            # on mutable title matching.
            if quiz is None and mapped_quiz_id is None and video.quiz_title:
                quiz = self.visible_quizzes_by_title.get(video.quiz_title)
            linked_quiz = None
            if quiz:
                progress = self._quiz_progress(quiz)
                linked_quiz = {
                    "available": True,
                    "id": quiz.id,
                    "title": quiz.title,
                    "route": f"/quizzes/{quiz.id}",
                    "review_route": f"/quizzes/{quiz.id}/review" if progress["attempted"] else None,
                    "action": "review" if progress["attempted"] else "take",
                    "score": progress["score"],
                    "total": progress["total"],
                    "score_percent": progress["score_percent"],
                    "passed": progress["passed"],
                    "mapping_basis": metadata.get("quiz_mapping_basis"),
                    "mapping_confidence": metadata.get("quiz_mapping_confidence"),
                }
            return _ResolvedContent(
                title=video.title,
                description=video.section,
                destination_route=f"/training/week/{week_number}?activity={activity.stable_id}",
                external_url=video.url,
                estimated_minutes=_duration_minutes(video.duration),
                job_relevance=video.job_relevance,
                linked_quiz=linked_quiz,
            )
        if activity.activity_type == "quiz":
            quiz = self.quizzes.get(ref)
            if not quiz:
                return None
            quiz_progress = self._quiz_progress(quiz)
            return _ResolvedContent(
                title=quiz.title,
                description="Required assessment" if activity.is_required else "Optional knowledge check",
                destination_route=f"/quizzes/{quiz.id}/review" if quiz_progress["attempted"] else f"/quizzes/{quiz.id}",
                estimated_minutes=activity.estimated_minutes,
            )
        if activity.activity_type == "lesson":
            lesson = self.lessons.get(ref)
            if not lesson:
                return None
            return _ResolvedContent(
                title=lesson.title,
                description=lesson.summary,
                destination_route=f"/lessons/{lesson.id}",
                estimated_minutes=lesson.estimated_minutes,
            )
        if activity.activity_type == "guided_lab":
            lab = self.labs.get(ref)
            if not lab:
                return None
            return _ResolvedContent(
                title=lab.title,
                description=lab.description,
                destination_route=f"/labs/{lab.id}",
                estimated_minutes=lab.estimated_minutes,
            )
        if activity.activity_type == "networking_lab":
            lab = self.cli_labs.get(activity.content_ref)
            if not lab:
                return None
            return _ResolvedContent(
                title=lab.title,
                description=f"{lab.difficulty} networking practice",
                destination_route=f"/cli-labs/{lab.id}",
                estimated_minutes=lab.est_minutes,
            )
        if activity.activity_type == "support_ticket":
            ticket = self.tickets.get(ref)
            if not ticket:
                return None
            return _ResolvedContent(
                title=ticket.title,
                description="Archived Support Ticket history",
                destination_route=None,
                estimated_minutes=activity.estimated_minutes,
            )
        if activity.activity_type == "service_desk_scenario":
            scenario = self.service_desk_scenarios.get(activity.content_ref)
            if not scenario:
                return None
            return _ResolvedContent(title=scenario.title, description=scenario.description, destination_route="/service-desk", estimated_minutes=activity.estimated_minutes)
        if activity.activity_type == "capstone":
            capstone = self.capstones.get(ref)
            if not capstone:
                return None
            role = self.roles.get(capstone.role_level)
            permission_locked = bool(role and role.rank_order > self.student_rank and not self.student.is_mentor)
            return _ResolvedContent(
                title=capstone.title,
                description=capstone.description,
                destination_route=None if permission_locked else f"/capstones/{capstone.id}",
                estimated_minutes=(capstone.estimated_hours or 0) * 60 or activity.estimated_minutes,
                permission_locked=permission_locked,
                permission_reason=f"Requires {role.name}" if permission_locked and role else None,
            )
        if activity.activity_type == "command_exercise":
            command = self.commands.get(ref)
            if not command:
                return None
            return _ResolvedContent(
                title=command.command,
                description=command.description,
                destination_route="/commands",
                estimated_minutes=activity.estimated_minutes,
            )
        if activity.activity_type == "terminal_exercise":
            return _ResolvedContent(
                title=(activity.metadata_json or {}).get("title", "Terminal Practice"),
                description="Practice commands in the Nexus terminal.",
                destination_route="/terminal",
                estimated_minutes=activity.estimated_minutes,
            )
        if activity.activity_type == "review":
            return _ResolvedContent(
                title=(activity.metadata_json or {}).get("title", "Weekly Review"),
                description=(activity.metadata_json or {}).get("description", "Review this week's required work."),
                destination_route=f"/training/week/{week_number}",
                estimated_minutes=activity.estimated_minutes,
            )
        return None

    def progress(self, activity: TrainingWeekActivity) -> dict:
        ref = _int_ref(activity.content_ref)
        if activity.activity_type == "video":
            video = self.videos.get(ref)
            watch = self.watches.get(video.video_key) if video else None
            return {"complete": watch is not None, "in_progress": False, "completed_at": watch.watched_at if watch else None}
        if activity.activity_type == "quiz":
            quiz = self.quizzes.get(ref)
            if not quiz:
                return {"complete": False, "in_progress": False, "completed_at": None}
            quiz_progress = self._quiz_progress(quiz)
            complete = quiz_progress["passed"] if activity.is_required else quiz_progress["attempted"]
            return {"complete": complete, "in_progress": quiz_progress["attempted"] and not complete, **quiz_progress}
        if activity.activity_type == "lesson":
            progress = self.lesson_progress.get(ref)
            return {"complete": progress is not None, "in_progress": False, "completed_at": progress.completed_at if progress else None}
        if activity.activity_type == "guided_lab":
            run = self.lab_runs.get(ref)
            complete = bool(run and run.status in {"submitted", "verified"})
            return {
                "complete": complete,
                "in_progress": bool(run and not complete),
                "completed_at": (run.verified_at or run.submitted_at) if complete else None,
            }
        if activity.activity_type == "support_ticket":
            submission = self.ticket_submissions.get(ref)
            complete = bool(
                submission
                and submission.status in {"pending", "in_review", "passed"}
                and (submission.graded_at is not None or submission.status == "passed")
            )
            return {
                "complete": complete,
                "in_progress": bool(submission and not complete),
                "completed_at": (submission.verified_at or submission.submitted_at) if complete else None,
                "score": (submission.final_score if submission and submission.final_score is not None else submission.ai_score if submission else None),
            }
        if activity.activity_type == "service_desk_scenario":
            scenario = self.service_desk_scenarios.get(activity.content_ref)
            if not scenario:
                return {"complete": False, "in_progress": False, "completed_at": None}
            versions = self.db.query(ServiceDeskScenarioVersion.id).filter(ServiceDeskScenarioVersion.scenario_id == scenario.id, ServiceDeskScenarioVersion.status == "published").all()
            completed_attempt = next(
                (
                    self.service_desk_completed_attempts.get(version_id)
                    for (version_id,) in versions
                    if version_id in self.service_desk_completed_attempts
                ),
                None,
            )
            return {
                "complete": completed_attempt is not None,
                "in_progress": False,
                "completed_at": completed_attempt.completed_at if completed_attempt else None,
                "score": completed_attempt.score if completed_attempt else None,
            }
        if activity.activity_type == "networking_lab":
            attempt = self.cli_attempts.get(activity.content_ref)
            complete = bool(attempt and attempt.completed_at)
            return {"complete": complete, "in_progress": bool(attempt and not complete), "completed_at": attempt.completed_at if complete else None}
        if activity.activity_type == "capstone":
            run = self.capstone_runs.get(ref)
            complete = bool(run and (run.passed or run.status in {"submitted", "reviewed", "passed"}))
            return {
                "complete": complete,
                "in_progress": bool(run and not complete),
                "completed_at": (run.reviewed_at or run.submitted_at) if complete else None,
            }
        return {"complete": False, "in_progress": False, "completed_at": None}


def _active_weeks(db: Session) -> list[TrainingWeek]:
    return (
        db.query(TrainingWeek)
        .options(selectinload(TrainingWeek.activities))
        .filter(TrainingWeek.is_active.is_(True))
        .order_by(TrainingWeek.display_order.asc(), TrainingWeek.week_number.asc(), TrainingWeek.id.asc())
        .all()
    )


def _serialize_activity(context: _TrainingContext, activity: TrainingWeekActivity) -> dict:
    content = context.resolve(activity)
    progress = context.progress(activity)
    item = {
        "id": activity.id,
        "stable_id": activity.stable_id,
        "activity_type": activity.activity_type,
        "activity_label": ACTIVITY_LABELS.get(activity.activity_type, activity.activity_type.replace("_", " ").title()),
        "content_ref": activity.content_ref,
        "display_order": activity.display_order,
        "is_required": activity.is_required,
        "requirement_label": "Required" if activity.is_required else "Optional",
        "estimated_minutes": activity.estimated_minutes or (content.estimated_minutes if content else None),
        "title": content.title if content else "Content unavailable",
        "description": content.description if content else "This activity reference needs administrator attention.",
        "destination_route": content.destination_route if content else None,
        "external_url": content.external_url if content else None,
        "job_relevance": content.job_relevance if content else None,
        "linked_quiz": content.linked_quiz if content else None,
        "complete": bool(progress.get("complete")),
        "status": "complete" if progress.get("complete") else ("in_progress" if progress.get("in_progress") else "not_started"),
        "completed_at": progress.get("completed_at"),
        "score": progress.get("score"),
        "total": progress.get("total"),
        "score_percent": progress.get("score_percent"),
        "prerequisite_activity_id": activity.prerequisite_activity_id,
        "prerequisite_mode": activity.prerequisite_mode,
        "trackable": activity.activity_type not in UNTRACKED_ACTIVITY_TYPES,
        "broken_reference": content is None,
        "permission_locked": content.permission_locked if content else False,
        "permission_reason": content.permission_reason if content else None,
    }
    if item["permission_locked"]:
        item["status"] = "locked"
    return item


def _serialize_week(
    week: TrainingWeek,
    activities: list[dict],
    *,
    locked: bool,
    lock_reason: str | None,
    lock_requirements: list[str] | None = None,
) -> dict:
    required = [item for item in activities if item["is_required"]]
    optional = [item for item in activities if not item["is_required"]]
    required_complete = sum(1 for item in required if item["complete"])
    optional_complete = sum(1 for item in optional if item["complete"])
    is_complete = required_complete == len(required)
    percent = round(required_complete / len(required) * 100) if required else 100
    required_estimated_minutes = sum(int(item.get("estimated_minutes") or 0) for item in required)
    if locked:
        status = "locked"
    elif is_complete:
        status = "complete"
    elif required_complete or optional_complete or any(item["status"] == "in_progress" for item in activities):
        status = "in_progress"
    else:
        status = "not_started"
    return {
        "id": week.id,
        "week_number": week.week_number,
        "display_order": week.display_order,
        "title": week.title,
        "description": week.description,
        "learning_goals": week.learning_goals or [],
        "estimated_minutes": week.estimated_minutes,
        "required_estimated_minutes": required_estimated_minutes,
        "required_complete": required_complete,
        "required_total": len(required),
        "optional_complete": optional_complete,
        "optional_total": len(optional),
        "completed_activity_count": required_complete + optional_complete,
        "total_activity_count": len(activities),
        "completion_percent": percent,
        "status": status,
        "is_complete": is_complete,
        "locked": locked,
        "lock_reason": lock_reason,
        "lock_requirements": lock_requirements or [],
    }


def _build_state(db: Session, student: Student):
    weeks = _active_weeks(db)
    activities = [activity for week in weeks for activity in sorted(week.activities, key=lambda item: (item.display_order, item.id))]
    context = _TrainingContext(db, student, activities)
    activity_states = {activity.id: _serialize_activity(context, activity) for activity in activities}

    for activity in activities:
        state = activity_states[activity.id]
        prerequisite = activity_states.get(activity.prerequisite_activity_id)
        if prerequisite and not prerequisite["complete"]:
            state["prerequisite_met"] = False
            state["prerequisite_title"] = prerequisite["title"]
            if activity.prerequisite_mode == "hard" and not state["complete"]:
                state["status"] = "locked"
                state["destination_route"] = None
        else:
            state["prerequisite_met"] = True
            state["prerequisite_title"] = prerequisite["title"] if prerequisite else None

    for week in weeks:
        week_items = [activity_states[item.id] for item in sorted(week.activities, key=lambda item: (item.display_order, item.id))]
        for item in week_items:
            if item["activity_type"] == "review":
                prior_required = [
                    candidate for candidate in week_items
                    if candidate["is_required"] and candidate["display_order"] < item["display_order"] and candidate["activity_type"] != "review"
                ]
                item["complete"] = all(candidate["complete"] for candidate in prior_required)
                item["status"] = "complete" if item["complete"] else "not_started"

    week_states = []
    prior_required_complete = True
    prior_title = None
    prior_missing_required: list[str] = []
    for week in weeks:
        items = [activity_states[item.id] for item in sorted(week.activities, key=lambda item: (item.display_order, item.id))]
        locked = bool(not student.is_mentor and week.requires_previous_week and not prior_required_complete)
        reason = None
        if locked and prior_title:
            remaining = len(prior_missing_required)
            first_missing = prior_missing_required[0] if prior_missing_required else None
            if first_missing and remaining > 1:
                reason = (
                    f"Complete {prior_title}: {first_missing} and "
                    f"{remaining - 1} more required item{'s' if remaining - 1 != 1 else ''}."
                )
            elif first_missing:
                reason = f"Complete {prior_title}: {first_missing}."
            else:
                reason = f"Complete {prior_title} first."
        state = _serialize_week(
            week,
            items,
            locked=locked,
            lock_reason=reason,
            lock_requirements=prior_missing_required if locked else [],
        )
        week_states.append((week, state, items))
        prior_required_complete = prior_required_complete and state["is_complete"]
        prior_title = f"Week {week.week_number} — {week.title}"
        prior_missing_required = [
            item["title"]
            for item in items
            if item["is_required"] and not item["complete"]
        ]
    return weeks, context, week_states


def build_training_overview(db: Session, student: Student) -> dict:
    _, _, week_states = _build_state(db, student)
    public_weeks = [state for _, state, _ in week_states]
    current_entry = next((entry for entry in week_states if not entry[1]["locked"] and not entry[1]["is_complete"]), None)
    training_complete = bool(week_states) and all(state["is_complete"] for _, state, _ in week_states)
    if current_entry is None and week_states and not training_complete:
        current_entry = next((entry for entry in week_states if not entry[1]["locked"]), week_states[0])
    if current_entry and current_entry[1]["status"] == "not_started":
        # The first available incomplete week is the student's active week even
        # before its first activity has been completed.
        current_entry[1]["status"] = "in_progress"
    next_activity = None
    if current_entry:
        next_activity = next(
            (
                item for item in current_entry[2]
                if item["is_required"] and not item["complete"] and item["status"] != "locked" and not item["broken_reference"]
            ),
            None,
        )
    current_week = current_entry[1] if current_entry else (public_weeks[-1] if public_weeks else None)
    recently_completed = sorted(
        [item for _, _, items in week_states for item in items if item["complete"] and item.get("completed_at")],
        key=lambda item: item["completed_at"] if isinstance(item["completed_at"], datetime) else datetime.min,
        reverse=True,
    )
    return {
        "current_week": current_week,
        "current_week_activities": current_entry[2] if current_entry else [],
        "weeks": public_weeks,
        "next_activity": next_activity,
        "recently_completed": recently_completed[0] if recently_completed else None,
        "training_complete": training_complete,
    }


def build_training_week(db: Session, student: Student, week_number: int) -> dict | None:
    _, _, week_states = _build_state(db, student)
    for _, state, items in week_states:
        if state["week_number"] != week_number:
            continue
        next_activity = next(
            (item for item in items if item["is_required"] and not item["complete"] and item["status"] != "locked" and not item["broken_reference"]),
            None,
        )
        return {**state, "activities": items, "next_activity": next_activity}
    return None


def _metric(states: list[dict], activity_types: set[str], *, complete_key="complete") -> dict:
    unique = {}
    for item in states:
        if item["activity_type"] in activity_types:
            unique[(item["activity_type"], item["content_ref"])] = item
    rows = list(unique.values())
    completed = sum(1 for item in rows if item.get(complete_key))
    return {"completed": completed, "total": len(rows), "percent": round(completed / len(rows) * 100) if rows else 0}


def _group_cohort_rows(rows, student_id):
    grouped = defaultdict(list)
    for row in rows:
        grouped[student_id(row)].append(row)
    return grouped


def build_cohort_summary(db: Session, students: list[Student]) -> list[dict]:
    """Build fixed-query training summaries for an administrator's cohort.

    Deliberately does not call build_training_progress/_build_state per
    student: _TrainingContext issues per-student queries, which would make
    this endpoint's query count scale with cohort size. Instead this
    re-derives the same completion rules (quiz pass threshold, ticket/lab/
    capstone/service-desk status checks, week-locking) against bulk,
    cohort-wide query results. Any change to those rules must be mirrored
    here — test_admin_students.py::test_cohort_summary_matches_authoritative_per_student_progress
    pins the two paths together so a rule change to one without the other
    fails a test instead of silently diverging.
    """
    if not students:
        return []

    cohort_ids = [student.id for student in students]
    weeks = _active_weeks(db)
    ordered_activities = {
        week.id: sorted(week.activities, key=lambda item: (item.display_order, item.id))
        for week in weeks
    }

    video_rows = (
        db.query(VideoWatch, CurriculumVideo.id)
        .join(CurriculumVideo, CurriculumVideo.video_key == VideoWatch.video_key)
        .filter(VideoWatch.student_id.in_(cohort_ids))
        .all()
    )
    question_counts = (
        db.query(Question.quiz_id.label("quiz_id"), func.count(Question.id).label("total"))
        .group_by(Question.quiz_id)
        .subquery()
    )
    quiz_rows = (
        db.query(
            QuizAttempt,
            func.coalesce(question_counts.c.total, Quiz.question_count).label("question_total"),
        )
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .outerjoin(question_counts, question_counts.c.quiz_id == Quiz.id)
        .filter(QuizAttempt.student_id.in_(cohort_ids))
        .order_by(QuizAttempt.completed_at.desc(), QuizAttempt.id.desc())
        .all()
    )
    lesson_progress_rows = db.query(StudentLessonProgress).filter(
        StudentLessonProgress.student_id.in_(cohort_ids), StudentLessonProgress.completed_at.isnot(None)
    ).all()
    lab_rows = (
        db.query(LabRun)
        .filter(LabRun.student_id.in_(cohort_ids))
        .order_by(LabRun.created_at.desc(), LabRun.id.desc())
        .all()
    )
    cli_rows = (
        db.query(CliLabAttempt)
        .filter(CliLabAttempt.student_id.in_(cohort_ids))
        .order_by(CliLabAttempt.completed_at.desc(), CliLabAttempt.id.desc())
        .all()
    )
    capstone_rows = (
        db.query(CapstoneRun)
        .filter(CapstoneRun.student_id.in_(cohort_ids))
        .order_by(CapstoneRun.created_at.desc(), CapstoneRun.id.desc())
        .all()
    )
    service_desk_rows = (
        db.query(ServiceDeskAttempt, ServiceDeskScenario.stable_key)
        .join(
            ServiceDeskScenarioVersion,
            ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id,
        )
        .join(ServiceDeskScenario, ServiceDeskScenario.id == ServiceDeskScenarioVersion.scenario_id)
        .filter(
            ServiceDeskAttempt.student_id.in_(cohort_ids),
            ServiceDeskScenarioVersion.status == "published",
        )
        .order_by(ServiceDeskAttempt.completed_at.desc(), ServiceDeskAttempt.id.desc())
        .all()
    )

    videos_by_student = _group_cohort_rows(video_rows, lambda row: row[0].student_id)
    quizzes_by_student = _group_cohort_rows(quiz_rows, lambda row: row[0].student_id)
    lesson_progress_by_student = _group_cohort_rows(lesson_progress_rows, lambda row: row.student_id)
    labs_by_student = _group_cohort_rows(lab_rows, lambda row: row.student_id)
    cli_by_student = _group_cohort_rows(cli_rows, lambda row: row.student_id)
    capstones_by_student = _group_cohort_rows(capstone_rows, lambda row: row.student_id)
    service_desk_by_student = _group_cohort_rows(
        service_desk_rows, lambda row: row[0].student_id
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=AT_RISK_INACTIVITY_HOURS)
    summaries = []
    for student in students:
        watched_video_ids = {str(content_id) for _, content_id in videos_by_student[student.id]}
        quiz_attempts = defaultdict(list)
        for attempt, total in quizzes_by_student[student.id]:
            quiz_attempts[str(attempt.quiz_id)].append((attempt, int(total or 0)))
        lesson_ids = {str(progress.lesson_id) for progress in lesson_progress_by_student[student.id]}
        lab_runs = _latest_by(labs_by_student[student.id], lambda row: str(row.lab_template_id))
        cli_attempts = _latest_by(cli_by_student[student.id], lambda row: row.lab_id)
        capstone_runs = _latest_by(
            capstones_by_student[student.id], lambda row: str(row.capstone_template_id)
        )
        passed_service_desk = {
            stable_key
            for attempt, stable_key in service_desk_by_student[student.id]
            if attempt.passed is True
        }

        def progress_for(activity: TrainingWeekActivity) -> tuple[bool, bool]:
            content_ref = activity.content_ref
            if activity.activity_type == "video":
                complete = content_ref in watched_video_ids
                return complete, False
            if activity.activity_type == "quiz":
                attempts = quiz_attempts[content_ref]
                attempted = bool(attempts)
                best = max(
                    (max(int(attempt.score or 0), int(attempt.best_score or 0)) for attempt, _ in attempts),
                    default=0,
                )
                total = max((total for _, total in attempts), default=0)
                complete = bool(
                    attempted
                    and (
                        bool(total and best * 100 >= total * 70)
                        if activity.is_required
                        else True
                    )
                )
                return complete, attempted and not complete
            if activity.activity_type == "lesson":
                return content_ref in lesson_ids, False
            if activity.activity_type == "guided_lab":
                run = lab_runs.get(content_ref)
                complete = bool(run and run.status in {"submitted", "verified"})
                return complete, bool(run and not complete)
            if activity.activity_type == "networking_lab":
                attempt = cli_attempts.get(content_ref)
                complete = bool(attempt and attempt.completed_at)
                return complete, bool(attempt and not complete)
            if activity.activity_type == "capstone":
                run = capstone_runs.get(content_ref)
                complete = bool(
                    run and (run.passed or run.status in {"submitted", "reviewed", "passed"})
                )
                return complete, bool(run and not complete)
            if activity.activity_type == "service_desk_scenario":
                return content_ref in passed_service_desk, False
            return False, False

        week_states = []
        prior_required_complete = True
        prior_title = None
        all_activity_states = []
        for week in weeks:
            activity_states = []
            for activity in ordered_activities[week.id]:
                complete, in_progress = progress_for(activity)
                activity_states.append(
                    {
                        "activity_type": activity.activity_type,
                        "content_ref": activity.content_ref,
                        "display_order": activity.display_order,
                        "is_required": activity.is_required,
                        "estimated_minutes": activity.estimated_minutes,
                        "complete": complete,
                        "status": "complete"
                        if complete
                        else ("in_progress" if in_progress else "not_started"),
                    }
                )
            for item in activity_states:
                if item["activity_type"] != "review":
                    continue
                prior_required = [
                    candidate
                    for candidate in activity_states
                    if candidate["is_required"]
                    and candidate["display_order"] < item["display_order"]
                    and candidate["activity_type"] != "review"
                ]
                item["complete"] = all(candidate["complete"] for candidate in prior_required)
                item["status"] = "complete" if item["complete"] else "not_started"

            locked = bool(
                not student.is_mentor and week.requires_previous_week and not prior_required_complete
            )
            lock_reason = f"Complete {prior_title} first." if locked and prior_title else None
            week_state = _serialize_week(
                week, activity_states, locked=locked, lock_reason=lock_reason
            )
            week_states.append(week_state)
            all_activity_states.extend(activity_states)
            prior_required_complete = prior_required_complete and week_state["is_complete"]
            prior_title = f"Week {week.week_number} — {week.title}"

        training_complete = bool(week_states) and all(
            week_state["is_complete"] for week_state in week_states
        )
        current_week = next(
            (
                week_state
                for week_state in week_states
                if not week_state["locked"] and not week_state["is_complete"]
            ),
            None,
        )
        if current_week is None and week_states and not training_complete:
            current_week = next(
                (week_state for week_state in week_states if not week_state["locked"]),
                week_states[0],
            )
        if current_week and current_week["status"] == "not_started":
            current_week["status"] = "in_progress"
        if current_week is None and week_states:
            current_week = week_states[-1]

        required = [item for item in all_activity_states if item["is_required"]]
        required_complete = sum(1 for item in required if item["complete"])
        last_active = student.last_active_at
        comparable_last_active = last_active
        if comparable_last_active and comparable_last_active.tzinfo is None:
            comparable_last_active = comparable_last_active.replace(tzinfo=timezone.utc)
        summaries.append(
            {
                "student_id": student.id,
                "name": student.name,
                "current_week": (
                    {
                        "week_number": current_week["week_number"],
                        "status": current_week["status"],
                    }
                    if current_week
                    else None
                ),
                "overall_percent": (
                    round(required_complete / len(required) * 100) if required else 100
                ),
                "last_active_at": last_active,
                "is_at_risk": (
                    comparable_last_active is None or comparable_last_active < cutoff
                ),
            }
        )
    return summaries


def build_training_progress(db: Session, student: Student) -> dict:
    """Build course metrics using required-activity completion and best quiz attempts.

    Overall percent is completed required activities divided by all required
    activities. Quiz average is the mean of each attempted quiz's best score
    percent; quiz best is the highest of those per-quiz best percentages.
    """
    _, _, week_states = _build_state(db, student)
    states = [item for _, _, items in week_states for item in items]
    required = [item for item in states if item["is_required"]]
    required_complete = sum(1 for item in required if item["complete"])
    video_metric = _metric(states, {"video"})
    quiz_metric = _metric(states, {"quiz"})
    practice_metric = _metric([item for item in required if item["activity_type"] in PRACTICE_ACTIVITY_TYPES], PRACTICE_ACTIVITY_TYPES)
    quiz_scores = [item["score_percent"] for item in states if item["activity_type"] == "quiz" and item.get("score_percent") is not None]
    overview = build_training_overview(db, student)
    promotion = get_promotion_status(student.id, db)
    accessible_capstones = [item for item in states if item["activity_type"] == "capstone" and not item["permission_locked"]]
    return {
        "current_week": overview["current_week"],
        "weeks_completed": sum(1 for _, state, _ in week_states if state["is_complete"]),
        "total_weeks": len(week_states),
        "weekly_roadmap": overview["weeks"],
        "overall_training": {
            "completed": required_complete,
            "total": len(required),
            "percent": round(required_complete / len(required) * 100) if required else 100,
        },
        "videos": {"completed": video_metric["completed"], "watched": video_metric["completed"], "total": video_metric["total"], "percent": video_metric["percent"]},
        "quizzes": {
            **quiz_metric,
            "average_score_percent": round(sum(quiz_scores) / len(quiz_scores)) if quiz_scores else 0,
            "best_score_percent": max(quiz_scores) if quiz_scores else 0,
        },
        "practice": practice_metric,
        "guided_labs": _metric(states, {"guided_lab"}),
        "networking_labs": _metric(states, {"networking_lab"}),
        "service_desk": _metric(states, {"service_desk_scenario"}),
        "capstones": _metric(states, {"capstone"}),
        "rank_progress": promotion,
        "skills": list_student_mastery(db, student.id),
        "capstone_readiness": {
            "available": len(accessible_capstones),
            "total": len([item for item in states if item["activity_type"] == "capstone"]),
        },
    }


def validate_training_activity_reference(db: Session, activity: TrainingWeekActivity) -> dict | None:
    ref = _int_ref(activity.content_ref)
    model_filters = {
        "video": (CurriculumVideo, CurriculumVideo.id == ref, CurriculumVideo.active.is_(True)),
        "lesson": (Lesson, Lesson.id == ref, None),
        "guided_lab": (LabTemplate, LabTemplate.id == ref, LabTemplate.is_published.is_(True)),
        "command_exercise": (CommandReference, CommandReference.id == ref, None),
        "capstone": (CapstoneTemplate, CapstoneTemplate.id == ref, CapstoneTemplate.is_published.is_(True)),
    }
    if activity.activity_type == "service_desk_scenario":
        scenario = db.query(ServiceDeskScenario).filter(ServiceDeskScenario.stable_key == activity.content_ref, ServiceDeskScenario.status == "active").first()
        if not scenario or not db.query(ServiceDeskScenarioVersion.id).filter(ServiceDeskScenarioVersion.scenario_id == scenario.id, ServiceDeskScenarioVersion.status == "published", ServiceDeskScenarioVersion.validation_status == "valid").first():
            return {"code": "BROKEN_REFERENCE", "severity": "error", "message": "Referenced published Service Desk scenario does not exist."}
        return None
    if activity.activity_type == "quiz":
        quiz = db.query(Quiz).filter(Quiz.id == ref).first()
        if quiz and not db.query(Quiz.id).filter(Quiz.id == ref, *student_visible_quiz_filters()).first():
            return {"code": "QUIZ_NOT_STUDENT_VISIBLE", "severity": "error", "message": "Quiz is not approved for students."}
        if not quiz:
            return {"code": "BROKEN_REFERENCE", "severity": "error", "message": "Referenced quiz does not exist."}
        return None
    if activity.activity_type == "networking_lab":
        exists = db.query(CliLab.id).filter(CliLab.id == activity.content_ref).first()
        if not exists:
            return {"code": "BROKEN_REFERENCE", "severity": "error", "message": "Referenced networking lab does not exist."}
        return None
    if activity.activity_type in {"terminal_exercise", "review"}:
        return None
    spec = model_filters.get(activity.activity_type)
    if not spec:
        return {"code": "INVALID_ACTIVITY_TYPE", "severity": "error", "message": "Unsupported activity type."}
    model, id_filter, state_filter = spec
    if ref is None:
        return {"code": "BROKEN_REFERENCE", "severity": "error", "message": "Content reference must be numeric."}
    query = db.query(model).filter(id_filter)
    if state_filter is not None:
        query = query.filter(state_filter)
    if not query.first():
        return {"code": "BROKEN_REFERENCE", "severity": "error", "message": "Referenced content does not exist or is disabled."}
    return None


def validate_video_quiz_mapping(db: Session, activity: TrainingWeekActivity) -> dict | None:
    metadata = activity.metadata_json or {}
    quiz_id = _int_ref(metadata.get("quiz_id"))
    if quiz_id is None:
        return {
            "code": "VIDEO_QUIZ_MAPPING_MISSING",
            "severity": "error",
            "message": "Video does not have an explicit quiz mapping.",
        }
    quiz = db.query(Quiz.id).filter(Quiz.id == quiz_id, *student_visible_quiz_filters()).first()
    if not quiz:
        return {
            "code": "VIDEO_QUIZ_MAPPING_INVALID",
            "severity": "error",
            "message": "Mapped quiz does not exist or is not approved for students.",
        }
    basis = metadata.get("quiz_mapping_basis")
    if basis not in {EXACT, TOPIC_GROUP, WEEK_FALLBACK}:
        return {
            "code": "VIDEO_QUIZ_MAPPING_BASIS_INVALID",
            "severity": "error",
            "message": "Video quiz mapping must record exact, topic-group, or week-level basis.",
        }
    if metadata.get("quiz_mapping_confidence") != CONFIDENCE_BY_BASIS[basis]:
        return {
            "code": "VIDEO_QUIZ_MAPPING_CONFIDENCE_INVALID",
            "severity": "error",
            "message": "Video quiz mapping confidence does not match its reviewed basis.",
        }
    if not str(metadata.get("quiz_mapping_evidence", "")).strip():
        return {
            "code": "VIDEO_QUIZ_MAPPING_EVIDENCE_MISSING",
            "severity": "error",
            "message": "Video quiz mapping must record review evidence.",
        }
    return None


def _hard_prerequisite_cycles(activities: list[TrainingWeekActivity]) -> set[int]:
    by_id = {activity.id: activity for activity in activities}
    cycles = set()
    for activity in activities:
        seen = set()
        current = activity
        while current and current.prerequisite_mode == "hard" and current.prerequisite_activity_id:
            if current.id in seen:
                cycles.update(seen)
                break
            seen.add(current.id)
            current = by_id.get(current.prerequisite_activity_id)
    return cycles


def _workload_row(db: Session, week: TrainingWeek) -> dict:
    required = [activity for activity in week.activities if activity.is_required]
    by_type: dict[str, int] = defaultdict(int)
    for activity in required:
        by_type[activity.activity_type] += 1
    video_ids = [_int_ref(activity.content_ref) for activity in required if activity.activity_type == "video"]
    video_minutes = sum(
        _duration_minutes(row.duration) or 0
        for row in db.query(CurriculumVideo).filter(CurriculumVideo.id.in_(video_ids)).all()
    ) if video_ids else 0
    non_video_minutes = sum(
        int(activity.estimated_minutes or 0)
        for activity in required
        if activity.activity_type != "video"
    )
    return {
        "week_number": week.week_number,
        "topic": week.title,
        "required_items": len(required),
        "required_videos": by_type["video"],
        "required_video_minutes": video_minutes,
        "required_lessons": by_type["lesson"],
        "required_quizzes": by_type["quiz"],
        "required_guided_labs": by_type["guided_lab"],
        "required_networking_labs": by_type["networking_lab"],
        "required_service_desk_scenarios": by_type["service_desk_scenario"],
        "required_capstones": by_type["capstone"],
        "estimated_minutes": video_minutes + non_video_minutes,
        "optional_items": sum(1 for activity in week.activities if not activity.is_required),
    }


def validate_training_curriculum(db: Session) -> dict:
    weeks = (
        db.query(TrainingWeek)
        .options(selectinload(TrainingWeek.activities))
        .order_by(TrainingWeek.display_order, TrainingWeek.week_number)
        .all()
    )
    issues = []
    activities = [activity for week in weeks for activity in week.activities]
    active_weeks = [week for week in weeks if week.is_active]
    active_activities = [activity for week in active_weeks for activity in week.activities]
    cycle_ids = _hard_prerequisite_cycles(activities)
    activity_by_id = {activity.id: activity for activity in activities}
    mapping_counts = defaultdict(int)
    if active_weeks and active_weeks[0].requires_previous_week:
        issues.append({"code": "FIRST_WEEK_LOCKED", "severity": "error", "week_number": active_weeks[0].week_number, "message": "The first active week cannot require a previous week."})
    for week in weeks:
        if week.is_active and not week.activities:
            issues.append({"code": "EMPTY_WEEK", "severity": "error", "week_number": week.week_number, "message": "Active week has no activities and no completion path."})
        if week.is_active and week.activities and not any(item.is_required for item in week.activities):
            issues.append({"code": "NO_REQUIRED_PATH", "severity": "error", "week_number": week.week_number, "message": "Active week has no required activity to define a completion path."})
        seen_orders = set()
        seen_required_refs = set()
        for activity in week.activities:
            if activity.display_order in seen_orders:
                issues.append({"code": "DUPLICATE_ACTIVITY_ORDER", "severity": "warning", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "Two activities share a display order."})
            seen_orders.add(activity.display_order)
            issue = validate_training_activity_reference(db, activity)
            if issue:
                issues.append({**issue, "week_number": week.week_number, "stable_id": activity.stable_id})
            if activity.activity_type == "video" and week.is_active:
                mapping_issue = validate_video_quiz_mapping(db, activity)
                if mapping_issue:
                    issues.append({**mapping_issue, "week_number": week.week_number, "stable_id": activity.stable_id})
                else:
                    mapping_counts[(activity.metadata_json or {}).get("quiz_mapping_confidence")] += 1
            if activity.activity_type in UNTRACKED_ACTIVITY_TYPES and activity.is_required:
                issues.append({"code": "UNTRACKED_REQUIRED_ACTIVITY", "severity": "error", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "This activity type has no trustworthy completion record and must remain optional."})
            if activity.is_required:
                canonical_ref = (activity.activity_type, activity.content_ref)
                if canonical_ref in seen_required_refs:
                    issues.append({"code": "DUPLICATE_REQUIRED_ACTIVITY", "severity": "error", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "The same required content is counted more than once in this week."})
                seen_required_refs.add(canonical_ref)
                prerequisite = activity_by_id.get(activity.prerequisite_activity_id)
                if activity.prerequisite_mode == "hard" and prerequisite and not prerequisite.is_required:
                    issues.append({"code": "REQUIRED_DEPENDS_ON_OPTIONAL", "severity": "error", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "A required activity cannot hard-require optional work."})
            if activity.id in cycle_ids:
                issues.append({"code": "PREREQUISITE_CYCLE", "severity": "error", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "Hard prerequisites contain a cycle."})

    active_video_counts: dict[int | None, int] = defaultdict(int)
    for activity in active_activities:
        if activity.activity_type == "video":
            active_video_counts[_int_ref(activity.content_ref)] += 1
    active_video_ids = set(active_video_counts)
    enabled_video_ids = {row.id for row in db.query(CurriculumVideo.id).filter(CurriculumVideo.active.is_(True)).all()}
    for video_id, count in active_video_counts.items():
        if video_id is not None and count > 1:
            issues.append({"code": "ACTIVE_VIDEO_ASSIGNED_MULTIPLE_TIMES", "severity": "error", "week_number": None, "message": f"Active video {video_id} is assigned to {count} enabled activities."})
    for video_id in sorted(enabled_video_ids - active_video_ids):
        issues.append({"code": "ACTIVE_VIDEO_UNASSIGNED", "severity": "error", "week_number": None, "message": f"Active video {video_id} is not assigned to an enabled training week."})
    return {
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "week_count": len(weeks),
        "activity_count": sum(len(week.activities) for week in weeks),
        "enabled_video_count": len(enabled_video_ids),
        "mapped_video_count": sum(mapping_counts.values()),
        "mapping_summary": dict(mapping_counts),
        "workload": [_workload_row(db, week) for week in active_weeks],
        "issues": issues,
    }
