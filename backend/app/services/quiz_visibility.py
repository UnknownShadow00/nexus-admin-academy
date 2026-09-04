"""Single source of truth for quiz visibility outside the editorial workspace."""

from sqlalchemy import inspect, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.certification import ModuleAssessment
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


def v2_owned_quiz_ids():
    """Subquery of every quiz the V2 curriculum owns.

    ``module_assessments`` is a V2-only table, so a quiz it points at is a V2
    bank by definition — no flag, column, or naming convention needed.
    """
    return select(ModuleAssessment.quiz_id).where(ModuleAssessment.quiz_id.is_not(None))


def v1_student_visible_quiz_filters() -> tuple[ColumnElement[bool], ...]:
    """Student visibility for the *legacy* quiz surfaces.

    Quizzes and questions are shared tables: loading V2 content creates and
    publishes V2 module banks in the same ``quizzes`` table the V1 quiz list
    reads. Because the V1 list is not scoped to the V1 curriculum, every
    published V2 bank would otherwise appear in the legacy Quizzes page and
    Daily Review of students who are not in the V2 pilot at all — an exposure
    caused by loading content, independent of the V2 feature flag.

    V2 students reach these banks through the V2 assessment endpoints, which
    apply the same visibility contract; the legacy surfaces simply stop
    listing content that does not belong to them.
    """
    return student_visible_quiz_filters() + (Quiz.id.not_in(v2_owned_quiz_ids()),)


def v1_student_visible_quiz_filters_for(db) -> tuple[ColumnElement[bool], ...]:
    """``v1_student_visible_quiz_filters`` for code that also runs mid-migration.

    The curriculum seed is replayed against historical Alembic revisions in
    tests and upgrade rehearsals, and ``module_assessments`` does not exist
    before the V2 foundation migration. At those revisions there is no V2
    content to exclude, so the base contract is already correct.
    """
    if not inspect(db.get_bind()).has_table(ModuleAssessment.__tablename__):
        return student_visible_quiz_filters()
    return v1_student_visible_quiz_filters()
