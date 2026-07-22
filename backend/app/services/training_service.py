from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.cli_lab import CliLab, CliLabAttempt
from app.models.command_reference import CommandReference
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson
from app.models.lesson_notes import StudentLessonNote
from app.models.progression import Role, StudentRole
from app.models.quiz import Quiz, QuizAttempt
from app.models.student import Student
from app.models.ticket import Ticket, TicketSubmission
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.models.video_watch import VideoWatch
from app.services.mastery_service import list_student_mastery
from app.services.progression_service import get_promotion_status
from app.services.quiz_visibility import student_visible_quiz_filters


PRACTICE_ACTIVITY_TYPES = {
    "guided_lab",
    "networking_lab",
    "support_ticket",
    "command_exercise",
    "terminal_exercise",
    "capstone",
}
UNTRACKED_ACTIVITY_TYPES = {"command_exercise", "terminal_exercise"}
ACTIVITY_LABELS = {
    "video": "Video",
    "quiz": "Quiz",
    "lesson": "Course Lesson",
    "guided_lab": "Guided Lab",
    "networking_lab": "Networking Lab",
    "support_ticket": "Support Ticket",
    "command_exercise": "Command Exercise",
    "terminal_exercise": "Terminal Exercise",
    "review": "Weekly Review",
    "capstone": "Capstone",
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

        self.videos = {
            row.id: row
            for row in db.query(CurriculumVideo)
            .filter(CurriculumVideo.id.in_(integer_refs("video")), CurriculumVideo.active.is_(True))
            .all()
        } if refs["video"] else {}
        self.quizzes = {
            row.id: row
            for row in db.query(Quiz)
            .options(selectinload(Quiz.questions))
            .filter(Quiz.id.in_(integer_refs("quiz")), *student_visible_quiz_filters())
            .all()
        } if refs["quiz"] else {}
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
        self.lesson_notes = {
            row.lesson_id: row
            for row in db.query(StudentLessonNote)
            .filter(StudentLessonNote.student_id == student.id, StudentLessonNote.lesson_id.in_(set(self.lessons)))
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
            linked_quiz = None
            if video.quiz_title:
                quiz = self.visible_quizzes_by_title.get(video.quiz_title)
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
                    }
                else:
                    linked_quiz = {"available": False, "label": "Quiz unavailable"}
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
                destination_route=f"/learning-path?lesson={lesson.id}",
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
                description=f"{ticket.category or 'IT support'} practice",
                destination_route=f"/tickets/{ticket.id}",
                estimated_minutes=activity.estimated_minutes,
            )
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
            note = self.lesson_notes.get(ref)
            return {"complete": note is not None, "in_progress": False, "completed_at": note.updated_at if note else None}
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
            complete = bool(submission and submission.status == "passed")
            return {
                "complete": complete,
                "in_progress": bool(submission and not complete),
                "completed_at": (submission.verified_at or submission.submitted_at) if complete else None,
                "score": (submission.final_score if submission and submission.final_score is not None else submission.ai_score if submission else None),
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


def _serialize_week(week: TrainingWeek, activities: list[dict], *, locked: bool, lock_reason: str | None) -> dict:
    required = [item for item in activities if item["is_required"]]
    optional = [item for item in activities if not item["is_required"]]
    required_complete = sum(1 for item in required if item["complete"])
    optional_complete = sum(1 for item in optional if item["complete"])
    is_complete = required_complete == len(required)
    percent = round(required_complete / len(required) * 100) if required else 100
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
    for week in weeks:
        items = [activity_states[item.id] for item in sorted(week.activities, key=lambda item: (item.display_order, item.id))]
        locked = bool(not student.is_mentor and week.requires_previous_week and not prior_required_complete)
        reason = f"Complete {prior_title} first." if locked and prior_title else None
        state = _serialize_week(week, items, locked=locked, lock_reason=reason)
        week_states.append((week, state, items))
        prior_required_complete = prior_required_complete and state["is_complete"]
        prior_title = f"Week {week.week_number} — {week.title}"
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


def build_training_progress(db: Session, student: Student) -> dict:
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
        "quizzes": {**quiz_metric, "average_score_percent": round(sum(quiz_scores) / len(quiz_scores)) if quiz_scores else 0},
        "practice": practice_metric,
        "guided_labs": _metric(states, {"guided_lab"}),
        "networking_labs": _metric(states, {"networking_lab"}),
        "tickets": _metric(states, {"support_ticket"}),
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
        "support_ticket": (Ticket, Ticket.id == ref, None),
        "command_exercise": (CommandReference, CommandReference.id == ref, None),
        "capstone": (CapstoneTemplate, CapstoneTemplate.id == ref, CapstoneTemplate.is_published.is_(True)),
    }
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


def validate_training_curriculum(db: Session) -> dict:
    weeks = (
        db.query(TrainingWeek)
        .options(selectinload(TrainingWeek.activities))
        .order_by(TrainingWeek.display_order, TrainingWeek.week_number)
        .all()
    )
    issues = []
    for week in weeks:
        if week.is_active and not week.activities:
            issues.append({"code": "EMPTY_WEEK", "severity": "warning", "week_number": week.week_number, "message": "Active week has no activities."})
        seen_orders = set()
        for activity in week.activities:
            if activity.display_order in seen_orders:
                issues.append({"code": "DUPLICATE_ACTIVITY_ORDER", "severity": "warning", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "Two activities share a display order."})
            seen_orders.add(activity.display_order)
            issue = validate_training_activity_reference(db, activity)
            if issue:
                issues.append({**issue, "week_number": week.week_number, "stable_id": activity.stable_id})
            if activity.activity_type in UNTRACKED_ACTIVITY_TYPES and activity.is_required:
                issues.append({"code": "UNTRACKED_REQUIRED_ACTIVITY", "severity": "error", "week_number": week.week_number, "stable_id": activity.stable_id, "message": "This activity type has no trustworthy completion record and must remain optional."})
    return {
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "week_count": len(weeks),
        "activity_count": sum(len(week.activities) for week in weeks),
        "issues": issues,
    }
