"""Editorial decisions for legacy quizzes not already in the weekly curriculum."""

from app.models.quiz import Quiz


# These six banks have complete explanations and a clear optional/remediation
# home. They remain outside the required checklist and therefore never block a
# week or compete with Today's next required action.
SAFE_OPTIONAL_QUIZ_MAPPINGS = {
    28: (5, "practice"),       # mobile accessories, after device foundations
    32: (7, "practice"),       # social engineering
    33: (7, "practice"),       # threats and vulnerabilities
    56: (11, "remediation"),   # TCP/UDP ports
    59: (8, "remediation"),    # network configuration concepts
    63: (9, "remediation"),    # network types
}


def apply_safe_optional_quiz_mappings(db) -> int:
    updated = 0
    for quiz_id, (week, purpose) in SAFE_OPTIONAL_QUIZ_MAPPINGS.items():
        quiz = db.get(Quiz, quiz_id)
        if not quiz:
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
