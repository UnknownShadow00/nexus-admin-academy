import logging
import os

import httpx
from sqlalchemy.orm import Session

from app.models.student import Student

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
MILESTONES = {
    100: "reached 100 XP!",
    500: "hit 500 XP milestone!",
    1000: "achieved 1000 XP!",
    2000: "reached 2000 XP!",
}


def post_milestone(student_name: str, milestone: str, xp: int | None = None) -> None:
    if not DISCORD_WEBHOOK_URL:
        return

    message = f"{student_name} {milestone}"
    if xp is not None:
        message += f" (+{xp} XP)"

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(
                DISCORD_WEBHOOK_URL,
                json={"content": message, "username": "Nexus Admin Academy"},
            )
    except Exception as exc:
        logger.warning("discord_webhook_failed error=%s", exc)


def check_and_post_milestones(db: Session, student_id: int, delta_xp: int) -> None:
    if delta_xp <= 0:
        return

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return

    previous_xp = student.total_xp - delta_xp
    for threshold, message in MILESTONES.items():
        if previous_xp < threshold <= student.total_xp:
            post_milestone(student.name, message, delta_xp)
