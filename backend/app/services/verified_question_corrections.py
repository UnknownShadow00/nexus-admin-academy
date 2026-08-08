"""Small, evidence-reviewed corrections keyed by complete question content."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models.quiz import Question


class QuestionCorrection(NamedTuple):
    correct_answer: str
    explanation: str


# Evidence:
# - Microsoft “System configuration tools in Windows” identifies Task Manager
#   as the per-application CPU, memory, disk, and network resource monitor.
# - Microsoft “Update drivers through Device Manager in Windows” places the
#   Roll Back Driver control in Device Manager's device Properties dialog.
CORRECTIONS = {
    "Which of the tools listed below can be used to identify resource-intensive applications that cause degraded performance in Microsoft Windows?": QuestionCorrection(
        "D",
        "Task Manager shows per-application CPU, memory, disk, and network use, which helps identify an application degrading performance. Event Viewer records system and application events but is not the primary live resource-usage view.",
    ),
    "A technician is troubleshooting a Windows system that powers off unexpectedly after a GPU driver update. Which Windows utility should the technician use to manually roll back the specific driver?": QuestionCorrection(
        "D",
        "Device Manager provides the Roll Back Driver control for a specific device. Windows Update installs updates, but it is not the utility used to manually restore one device's previous driver.",
    ),
}


def correction_for(question_text: str) -> QuestionCorrection | None:
    return CORRECTIONS.get(" ".join((question_text or "").split()))


def apply_verified_question_corrections(db: Session) -> int:
    updated = 0
    for question_text, correction in CORRECTIONS.items():
        rows = db.query(Question).filter(Question.question_text == question_text).all()
        for question in rows:
            question.correct_answer = correction.correct_answer
            question.correct_answers = None
            question.explanation = correction.explanation
            question.flagged_for_review = False
            question.flag_reason = None
            updated += 1
    db.flush()
    return updated
