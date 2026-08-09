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
    "A system admin performs a backup that copies every file on a workstation each night, even if no files were modified. Which backup type is being used?": QuestionCorrection(
        "B",
        "A full backup copies every selected file, whether or not it changed since the previous backup. That makes recovery straightforward, but it takes more time and storage than incremental or differential backups.",
    ),
    "A workstation backup strategy uses a full backup on Sunday and small daily backups that capture only the files changed since the last backup. What type of backup is being performed?": QuestionCorrection(
        "D",
        "An incremental backup copies changes made since the most recent backup of any type. To restore, you need the last full backup and each later incremental backup.",
    ),
    "Which backup type copies all data changed since the last full backup?": QuestionCorrection(
        "D",
        "A differential backup includes every change made since the last full backup. Unlike an incremental, it does not reset after each daily backup.",
    ),
    "A backup strategy uses a weekly full backup and daily incrementals, then creates a new full backup copy by combining existing backup data instead of pulling data from the workstation. What type of backup is generated?": QuestionCorrection(
        "B",
        "A synthetic full backup is assembled from an earlier full backup and later backup data. It creates a new full backup set without rereading every file from the workstation.",
    ),
    "Which of the tools listed below can be used to identify resource-intensive applications that cause degraded performance in Microsoft Windows?": QuestionCorrection(
        "D",
        "Task Manager shows per-application CPU, memory, disk, and network use, which helps identify an application degrading performance. Event Viewer records system and application events but is not the primary live resource-usage view.",
    ),
    "A technician is troubleshooting a Windows system that powers off unexpectedly after a GPU driver update. Which Windows utility should the technician use to manually roll back the specific driver?": QuestionCorrection(
        "D",
        "Device Manager provides the Roll Back Driver control for a specific device. Windows Update installs updates, but it is not the utility used to manually restore one device's previous driver.",
    ),
}

# This wording is deliberately held, rather than "fixed" by choosing a key.
# Firmware can have a setup/supervisor password (choices A, B, C, and E) and a
# power-on password (choice D). Calling either one a "BIOS password" makes the
# current single-answer prompt objectively ambiguous for a beginner.
EDITORIAL_HOLDS = {
    "Which of the following statements does not apply to a BIOS password?": (
        "Ambiguous: 'BIOS password' can mean a setup/supervisor password or a "
        "power-on password. The options mix both concepts, so no single answer "
        "is objectively correct. Keep hidden until rewritten with one password type."
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
    for question_text, reason in EDITORIAL_HOLDS.items():
        rows = db.query(Question).filter(Question.question_text == question_text).all()
        for question in rows:
            question.flagged_for_review = True
            question.flag_reason = reason
            updated += 1
    db.flush()
    return updated
