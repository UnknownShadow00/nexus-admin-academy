"""Authoritative ownership map and transactional cleanup for student deletion.

The supported administrator endpoint is the only caller of this module.  It
uses explicit deletes even for rows that also have database cascades: account
deletion must not depend on the state of a particular SQLite connection's
``foreign_keys`` pragma.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_rate_limit import AIRateLimit
from app.models.capstone import CapstoneRun
from app.models.cli_lab import CliLabAttempt
from app.models.evidence import EvidenceArtifact
from app.models.flashcard import FlashcardReview
from app.models.incident import IncidentParticipant, RCASubmission
from app.models.lab import LabRun
from app.models.lesson_notes import StudentLessonNote
from app.models.lesson_progress import StudentLessonProgress
from app.models.login_streak import LoginStreak
from app.models.mastery import StudentDomainMastery
from app.models.onboarding import StudentOnboardingPractice
from app.models.progression import StudentMethodologyProgress, StudentRole
from app.models.quiz import QuizAssignment, QuizAttempt
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskAttemptEvent,
    ServiceDeskAttemptGrade,
    ServiceDeskBetaEnrollment,
)
from app.models.squad_activity import SquadActivity
from app.models.student import Student
from app.models.ticket import TicketSubmission
from app.models.video_watch import VideoWatch
from app.models.vm_assignment import VmAssignment
from app.models.weekly_lead import WeeklyDomainLead
from app.models.comptia import StudentObjectiveProgress
from app.models.xp_ledger import XPLedger


# Each tuple is (database table name, ORM model, ownership column).  Keep this
# list aligned with docs/STUDENT_DELETION_DATA_OWNERSHIP_AUDIT.md.  It is also
# the reusable diagnostic used by tests and release smoke validation.
STUDENT_OWNED_MODELS: tuple[tuple[str, type, str], ...] = (
    ("ai_rate_limits", AIRateLimit, "user_id"),
    ("capstone_runs", CapstoneRun, "student_id"),
    ("cli_lab_attempt", CliLabAttempt, "student_id"),
    ("evidence_artifacts", EvidenceArtifact, "student_id"),
    ("flashcard_reviews", FlashcardReview, "student_id"),
    ("incident_participants", IncidentParticipant, "student_id"),
    ("lab_runs", LabRun, "student_id"),
    ("login_streaks", LoginStreak, "student_id"),
    ("quiz_assignments", QuizAssignment, "student_id"),
    ("quiz_attempts", QuizAttempt, "student_id"),
    ("rca_submissions", RCASubmission, "student_id"),
    ("service_desk_assignments", ServiceDeskAssignment, "student_id"),
    ("service_desk_attempts", ServiceDeskAttempt, "student_id"),
    ("service_desk_beta_enrollments", ServiceDeskBetaEnrollment, "student_id"),
    ("squad_activity", SquadActivity, "student_id"),
    ("student_domain_mastery", StudentDomainMastery, "student_id"),
    ("student_lesson_notes", StudentLessonNote, "student_id"),
    ("student_lesson_progress", StudentLessonProgress, "student_id"),
    ("student_methodology_progress", StudentMethodologyProgress, "student_id"),
    ("student_objective_progress", StudentObjectiveProgress, "student_id"),
    ("student_onboarding_practice", StudentOnboardingPractice, "student_id"),
    ("student_roles", StudentRole, "student_id"),
    ("ticket_submissions", TicketSubmission, "student_id"),
    ("video_watches", VideoWatch, "student_id"),
    ("vm_assignments", VmAssignment, "student_id"),
    ("weekly_domain_leads", WeeklyDomainLead, "student_id"),
    ("xp_ledger", XPLedger, "student_id"),
)


def student_owned_row_counts(db: Session, student_id: int) -> dict[str, int]:
    """Return a complete, read-only count map for a student's owned rows.

    A missing table in a historic disposable database is represented as zero
    by the caller's schema, not silently skipped here.  The explicit map is
    intentional: it makes a newly introduced student-owned table a review
    decision rather than an accidental cleanup gap.
    """

    counts = {"students": db.query(Student).filter(Student.id == student_id).count()}
    for table, model, column_name in STUDENT_OWNED_MODELS:
        column = getattr(model, column_name)
        counts[table] = db.query(func.count()).select_from(model).filter(column == student_id).scalar() or 0

    attempt_ids = [
        attempt_id
        for (attempt_id,) in db.query(ServiceDeskAttempt.id)
        .filter(ServiceDeskAttempt.student_id == student_id)
        .all()
    ]
    counts["service_desk_attempt_events"] = (
        db.query(ServiceDeskAttemptEvent)
        .filter(ServiceDeskAttemptEvent.attempt_id.in_(attempt_ids))
        .count()
        if attempt_ids
        else 0
    )
    counts["service_desk_attempt_grades"] = (
        db.query(ServiceDeskAttemptGrade)
        .filter(ServiceDeskAttemptGrade.attempt_id.in_(attempt_ids))
        .count()
        if attempt_ids
        else 0
    )
    return counts


def remaining_student_owned_rows(db: Session, student_id: int) -> dict[str, int]:
    """Return only non-zero ownership counts for release-smoke assertions."""

    return {
        table: count
        for table, count in student_owned_row_counts(db, student_id).items()
        if count
    }


def global_student_ownership_orphans(db: Session) -> dict[str, int]:
    """Return orphaned indirect Service Desk records, if any.

    Event and grade rows intentionally identify an attempt, not a student. Once
    an attempt has been deleted there is no safe per-student join left, so this
    companion check proves those indirect student-owned records have no orphan
    root anywhere in the database.
    """

    return {
        "service_desk_attempt_events": (
            db.query(ServiceDeskAttemptEvent)
            .outerjoin(ServiceDeskAttempt, ServiceDeskAttempt.id == ServiceDeskAttemptEvent.attempt_id)
            .filter(ServiceDeskAttempt.id.is_(None))
            .count()
        ),
        "service_desk_attempt_grades": (
            db.query(ServiceDeskAttemptGrade)
            .outerjoin(ServiceDeskAttempt, ServiceDeskAttempt.id == ServiceDeskAttemptGrade.attempt_id)
            .filter(ServiceDeskAttempt.id.is_(None))
            .count()
        ),
    }


def _delete_rows(db: Session, models: Iterable[tuple[type, str]], student_id: int) -> None:
    for model, column_name in models:
        db.query(model).filter(getattr(model, column_name) == student_id).delete(
            synchronize_session=False
        )


def delete_student_owned_data(db: Session, student_id: int) -> None:
    """Delete all exclusively student-owned database data in dependency order.

    This function deliberately does not commit.  Its caller owns the account
    deletion and commits or rolls back the one surrounding transaction.
    Shared curriculum, scenarios, scenario versions, quizzes, questions, and
    administrator/instructor records are never selected here.
    """

    attempt_ids = [
        attempt_id
        for (attempt_id,) in db.query(ServiceDeskAttempt.id)
        .filter(ServiceDeskAttempt.student_id == student_id)
        .all()
    ]
    if attempt_ids:
        db.query(ServiceDeskAttemptGrade).filter(
            ServiceDeskAttemptGrade.attempt_id.in_(attempt_ids)
        ).delete(synchronize_session=False)
        db.query(ServiceDeskAttemptEvent).filter(
            ServiceDeskAttemptEvent.attempt_id.in_(attempt_ids)
        ).delete(synchronize_session=False)

    # Children whose foreign keys are RESTRICT must be removed before their
    # direct owner; VM assignments must be removed before the lab run.
    _delete_rows(
        db,
        (
            (VmAssignment, "student_id"),
            (ServiceDeskAttempt, "student_id"),
            (ServiceDeskAssignment, "student_id"),
            (ServiceDeskBetaEnrollment, "student_id"),
        ),
        student_id,
    )

    # Delete every other direct ownership row explicitly.  Several have
    # CASCADE constraints as defense in depth; explicit cleanup remains the
    # supported deletion contract and works even if a legacy SQLite connection
    # was opened with foreign-key enforcement disabled.
    _delete_rows(
        db,
        tuple(
            (model, column_name)
            for table, model, column_name in STUDENT_OWNED_MODELS
            if table
            not in {
                "service_desk_assignments",
                "service_desk_attempts",
                "service_desk_beta_enrollments",
                "vm_assignments",
            }
        ),
        student_id,
    )
