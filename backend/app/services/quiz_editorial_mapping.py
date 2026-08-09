"""Editorial decisions for legacy quizzes not already in the weekly curriculum."""

from app.models.quiz import EDITORIAL_STATUS_VALIDATED, Quiz, Question


# These six banks have complete explanations and a clear optional/remediation
# home. They remain outside the required checklist and therefore never block a
# week or compete with Today's next required action.
SAFE_OPTIONAL_QUIZ_MAPPINGS = {
    45: (17, "practice"),     # backup methods, immediately after the backup lesson
    28: (5, "practice"),       # mobile accessories, after device foundations
    32: (7, "practice"),       # social engineering
    33: (7, "practice"),       # threats and vulnerabilities
    56: (11, "remediation"),   # TCP/UDP ports
    59: (8, "remediation"),    # network configuration concepts
    63: (9, "remediation"),    # network types
}

EXPECTED_QUIZ_TITLES = {
    45: "Backup & Recovery Methods Quiz",
    28: "Mobile Device Accessories Quiz",
    32: "Social Engineering Quiz",
    33: "Threats & Vulnerabilities Quiz",
    56: "TCP & UDP Ports Quiz",
    59: "Network Configuration Concepts Quiz",
    63: "Network Types Quiz",
}


REVIEWED_LEGACY_QUIZ_APPROVALS = {
    45: "Backup & Recovery Methods Quiz",
}


def apply_safe_optional_quiz_mappings(db) -> int:
    updated = 0
    for quiz_id, (week, purpose) in SAFE_OPTIONAL_QUIZ_MAPPINGS.items():
        quiz = db.get(Quiz, quiz_id)
        if not quiz or quiz.title != EXPECTED_QUIZ_TITLES[quiz_id]:
            continue
        quiz.week_number = week
        quiz.recommended_week = week
        quiz.prerequisite_week = max(0, week - 1)
        quiz.quiz_purpose = purpose
        quiz.is_required = False
        quiz.show_in_weekly_checklist = False
        quiz.show_in_practice_library = True
        updated += 1
    db.flush()
    return updated


def apply_reviewed_legacy_quiz_approvals(db) -> int:
    """Approve only legacy banks whose reviewed questions are complete.

    This intentionally does not infer approval from a mapping. A bank needs
    explanations for every question and no open editorial flags before it can
    pass the same centralized student-visibility gate as authored content.
    """
    updated = 0
    for quiz_id, expected_title in REVIEWED_LEGACY_QUIZ_APPROVALS.items():
        quiz = db.get(Quiz, quiz_id)
        if not quiz or quiz.title != expected_title:
            continue
        questions = db.query(Question).filter(Question.quiz_id == quiz.id).all()
        if not questions or any(not (q.explanation or "").strip() or q.flagged_for_review for q in questions):
            continue
        quiz.editorial_status = EDITORIAL_STATUS_VALIDATED
        quiz.answer_keys_validated = True
        quiz.explanations_complete = True
        quiz.is_active = True
        updated += 1
    db.flush()
    return updated
