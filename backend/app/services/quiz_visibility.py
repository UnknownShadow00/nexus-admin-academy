"""Single source of truth for quiz visibility outside the editorial workspace."""

from sqlalchemy.sql.elements import ColumnElement

from app.models.quiz import (
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_STATUS_PUBLISHED,
    Quiz,
)


def student_visible_quiz_filters() -> tuple[ColumnElement[bool], ...]:
    """Return the non-negotiable filters for every student quiz query.

    Publishing a quiz is not an editorial approval.  A quiz is student-visible
    only after both its editorial review and answer-key validation are complete.
    Keeping these predicates together prevents a new student surface from
    accidentally bypassing that rule.
    """
    return (
        Quiz.status == QUIZ_STATUS_PUBLISHED,
        Quiz.is_active.is_(True),
        Quiz.editorial_status == EDITORIAL_STATUS_VALIDATED,
        Quiz.answer_keys_validated.is_(True),
    )
