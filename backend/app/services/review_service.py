"""Deterministic learner-facing review guidance.

This module deliberately uses stored misses and due dates. It does not infer
weakness from reading speed, lesson completion, or a predictive model.
"""

from sqlalchemy.orm import Session

from app.models.learning import Lesson
from app.models.quiz import Quiz
from app.models.training import TrainingWeekActivity


CONCEPT_KEYWORDS = (
    (("dhcp", "169.254", "apipa"), "DHCP and APIPA"),
    (("dns",), "DNS name resolution"),
    (("printer", "print queue", "spooler"), "Printer troubleshooting"),
    (("ticket", "requester", "escalation"), "Support ticket workflow"),
    (("identity", "mfa", "sign-in", "password"), "Identity and access"),
    (("command", "terminal", "ipconfig"), "Command-line inspection"),
    (("hardware", "memory", "ram", "storage"), "PC hardware evidence"),
    (("windows", "sfc", "dism"), "Windows troubleshooting"),
)


def learner_concept_name(question_text: str, quiz_title: str) -> str:
    combined = f"{question_text} {quiz_title}".casefold()
    for keywords, label in CONCEPT_KEYWORDS:
        if any(keyword in combined for keyword in keywords):
            return label
    title = quiz_title.removesuffix(" Quiz").strip()
    return title if title else "Course concept"


def lesson_review(db: Session, quiz: Quiz) -> dict | None:
    lesson_id = quiz.lesson_id
    if not lesson_id:
        activity = (
            db.query(TrainingWeekActivity)
            .filter_by(activity_type="quiz", content_ref=str(quiz.id))
            .order_by(TrainingWeekActivity.is_required.desc(), TrainingWeekActivity.id)
            .first()
        )
        if activity:
            prerequisite = activity.prerequisite_activity
            if prerequisite and prerequisite.activity_type == "lesson":
                lesson_id = int(prerequisite.content_ref)
            else:
                previous_lesson = (
                    db.query(TrainingWeekActivity)
                    .filter(
                        TrainingWeekActivity.training_week_id
                        == activity.training_week_id,
                        TrainingWeekActivity.activity_type == "lesson",
                        TrainingWeekActivity.display_order < activity.display_order,
                    )
                    .order_by(TrainingWeekActivity.display_order.desc())
                    .first()
                )
                if previous_lesson:
                    lesson_id = int(previous_lesson.content_ref)
    lesson = db.get(Lesson, lesson_id) if lesson_id else None
    if not lesson:
        return None
    return {
        "lesson_id": lesson.id,
        "title": lesson.title,
        "url": f"/lessons/{lesson.id}#worked-example",
        "label": f"{lesson.title} → Worked example",
    }


def related_practice(db: Session, quiz: Quiz) -> dict | None:
    practice = (
        db.query(Quiz)
        .filter(
            Quiz.week_number == quiz.week_number,
            Quiz.id != quiz.id,
            Quiz.is_required.is_(False),
            Quiz.show_in_practice_library.is_(True),
            Quiz.is_active.is_(True),
        )
        .order_by(Quiz.id)
        .first()
    )
    if not practice:
        return None
    return {
        "quiz_id": practice.id,
        "title": practice.title,
        "url": f"/quizzes/{practice.id}",
        "label": f"Practice {practice.title}",
    }
