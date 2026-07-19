"""Idempotent organization metadata for the 25 curriculum seed quizzes."""

import hashlib

from app.models.quiz import (
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_PURPOSE_CUMULATIVE,
    QUIZ_PURPOSE_GATE,
    QUIZ_PURPOSE_PRACTICE,
    QUIZ_PURPOSE_REQUIRED,
    SOURCE_TYPE_SEED,
    Quiz,
    Question,
)


SEED_QUIZ_ORGANIZATION = {
    "Ticket Writing Fundamentals": (1, QUIZ_PURPOSE_REQUIRED, True, 96),
    "Windows Accounts and Permissions": (3, QUIZ_PURPOSE_REQUIRED, True, 94),
    "The Investigator's Toolkit": (3, QUIZ_PURPOSE_PRACTICE, False, 92),
    "Windows Command-Line Diagnostics": (3, QUIZ_PURPOSE_PRACTICE, False, 96),
    "Help-Desk Operations": (4, QUIZ_PURPOSE_GATE, True, 96),
    "Windows Deep Troubleshooting": (5, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Accounts and Permissions in Practice": (6, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Endpoint Security and Remote Support": (7, QUIZ_PURPOSE_REQUIRED, True, 96),
    "Client Network Triage": (8, QUIZ_PURPOSE_GATE, True, 96),
    "IPv4 Addressing and Subnetting": (9, QUIZ_PURPOSE_REQUIRED, True, 92),
    "Packet Flow, ARP, and MAC Learning": (9, QUIZ_PURPOSE_PRACTICE, False, 95),
    "Cisco CLI, VLANs, and Interfaces": (10, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Trunks, Routing, and Network Services": (11, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Network Troubleshooting and Secure Admin": (12, QUIZ_PURPOSE_GATE, True, 96),
    "Active Directory Foundations": (13, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Domain Joins and File Access": (14, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Group Policy Troubleshooting": (15, QUIZ_PURPOSE_REQUIRED, True, 88),
    "Server DNS/DHCP and PowerShell": (16, QUIZ_PURPOSE_CUMULATIVE, True, 91),
    "Server Operations, Backup, and Remoting": (17, QUIZ_PURPOSE_GATE, True, 95),
    "Linux Fundamentals: Files, Permissions, SSH": (18, QUIZ_PURPOSE_REQUIRED, True, 94),
    "Services, Logs, and Linux Networking": (19, QUIZ_PURPOSE_REQUIRED, True, 93),
    "Linux in Production and Monitoring": (20, QUIZ_PURPOSE_CUMULATIVE, True, 93),
    "Cloud Concepts and Entra ID": (21, QUIZ_PURPOSE_REQUIRED, True, 95),
    "Azure VMs, NSGs, and Storage": (22, QUIZ_PURPOSE_REQUIRED, True, 94),
    "Integrated Operations Readiness": (24, QUIZ_PURPOSE_GATE, True, 95),
}


def seed_quiz_organization(db) -> int:
    updated = 0
    for title, (week, purpose, required, score) in SEED_QUIZ_ORGANIZATION.items():
        quiz = db.query(Quiz).filter(Quiz.title == title, Quiz.source_url.is_(None)).first()
        if not quiz:
            continue
        quiz.week_number = week
        quiz.recommended_week = week
        quiz.prerequisite_week = max(0, week - 1)
        quiz.quiz_purpose = purpose
        quiz.is_required = required
        quiz.show_in_weekly_checklist = required
        quiz.show_in_practice_library = not required
        quiz.editorial_status = EDITORIAL_STATUS_VALIDATED
        quiz.quality_score = score
        quiz.source_type = SOURCE_TYPE_SEED
        quiz.answer_keys_validated = True
        quiz.explanations_complete = True
        quiz.is_active = True
        updated += 1
    db.flush()
    return updated


def rebalance_seed_answer_positions(db) -> int:
    """Deterministically spread single-answer seed keys without changing meaning.

    The target position is derived from question text, so repeated runs are
    stable. Multi-select questions are intentionally left untouched.
    """
    changed = 0
    questions = (
        db.query(Question)
        .join(Quiz, Quiz.id == Question.quiz_id)
        .filter(Quiz.source_type == SOURCE_TYPE_SEED)
        .order_by(Quiz.id, Question.id)
        .all()
    )
    for question in questions:
        if question.is_multi_select:
            continue
        available = [letter for letter in "ABCDEFGH" if getattr(question, f"option_{letter.lower()}")]
        if question.correct_answer not in available or len(available) < 2:
            continue
        digest = hashlib.sha256(question.question_text.strip().encode("utf-8")).digest()
        target = available[int.from_bytes(digest[:4], "big") % len(available)]
        current = question.correct_answer
        if target == current:
            continue
        current_field = f"option_{current.lower()}"
        target_field = f"option_{target.lower()}"
        correct_text = getattr(question, current_field)
        setattr(question, current_field, getattr(question, target_field))
        setattr(question, target_field, correct_text)
        question.correct_answer = target
        changed += 1
    db.flush()
    return changed
