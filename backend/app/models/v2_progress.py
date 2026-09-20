"""Nexus V2 per-student module activity (Phase 2A).

One row per (student, activity_type, ref_key). This is a **development-flow**
progress record for the first end-to-end V2 module — it deliberately does NOT
feed any legacy progression gate, XP ledger, mastery calculation, or the 40%
A+ TrainingWeek gate. No legacy table is touched.

``activity_type`` values:

    lesson         a V2 Markdown lesson was completed        (ref_key = lesson_key)
    resource       a learning resource was completed         (ref_key = resource_key)
    quick_check    a formative per-lesson quick check         (ref_key = assessment_key)
    module_quiz    the scored V2 module quiz                  (ref_key = assessment_key)
    practical      the guided practical lab                   (ref_key = assessment_key)
    service_desk   the mapped Service Desk scenario           (ref_key = assessment_key)
    explain        an Explain / interview prompt              (ref_key = prompt_key)

``detail`` is free-form JSON the caller owns: e.g. missed question ids for a
quiz, matched/missing concepts for an Explain answer, the deterministic grader
method, or a pointer to a ``pending_grades`` row.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from app.database import Base

V2_ACTIVITY_LESSON = "lesson"
V2_ACTIVITY_RESOURCE = "resource"
V2_ACTIVITY_QUICK_CHECK = "quick_check"
V2_ACTIVITY_MODULE_QUIZ = "module_quiz"
V2_ACTIVITY_PRACTICAL = "practical"
V2_ACTIVITY_SERVICE_DESK = "service_desk"
V2_ACTIVITY_EXPLAIN = "explain"
V2_ACTIVITY_TYPES = {
    V2_ACTIVITY_LESSON,
    V2_ACTIVITY_RESOURCE,
    V2_ACTIVITY_QUICK_CHECK,
    V2_ACTIVITY_MODULE_QUIZ,
    V2_ACTIVITY_PRACTICAL,
    V2_ACTIVITY_SERVICE_DESK,
    V2_ACTIVITY_EXPLAIN,
}

V2_STATUS_NOT_STARTED = "not_started"
V2_STATUS_IN_PROGRESS = "in_progress"
V2_STATUS_COMPLETED = "completed"
V2_STATUS_PASSED = "passed"
V2_STATUS_FAILED = "failed"
V2_STATUS_NEEDS_REVIEW = "needs_review"
V2_STATUS_VALUES = {
    V2_STATUS_NOT_STARTED,
    V2_STATUS_IN_PROGRESS,
    V2_STATUS_COMPLETED,
    V2_STATUS_PASSED,
    V2_STATUS_FAILED,
    V2_STATUS_NEEDS_REVIEW,
}

_ACTIVITY_TYPE_SQL = "('lesson','resource','quick_check','module_quiz','practical','service_desk','explain')"


class V2ModuleActivity(Base):
    """Development-flow progress record for a Nexus V2 module. Not authoritative
    for any gate — no legacy progression system reads this table."""

    __tablename__ = "v2_module_activity"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "activity_type", "ref_key", name="uq_v2_module_activity"
        ),
        CheckConstraint(
            f"activity_type IN {_ACTIVITY_TYPE_SQL}", name="ck_v2_module_activity_type"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    ref_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=V2_STATUS_IN_PROGRESS,
        server_default=V2_STATUS_IN_PROGRESS,
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    detail: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict,
        server_default="{}",
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class V2ExplainSubmission(Base):
    """Immutable student answer saved before the grading pipeline is called.

    Grading state remains in ``pending_grades`` / ``ai_grades``; this row is
    only the durable original submission required by the Phase 1C contract.
    """

    __tablename__ = "v2_explain_submissions"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "prompt_id", "attempt_number",
            name="uq_v2_explain_submission_attempt",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("interview_prompts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submitted_answer: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class V2AssessmentAttempt(Base):
    """Durable server-owned V2 knowledge-check attempt.

    The selected questions live in ordered child rows and are never selected
    again after this row is created. ``V2ModuleActivity`` remains only the
    monotonic best-completion roll-up.
    """

    __tablename__ = "v2_assessment_attempts"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "assessment_id", "attempt_number",
            name="uq_v2_assessment_attempt_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("module_assessments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    module_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    assessment_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=V2_STATUS_IN_PROGRESS,
        server_default=V2_STATUS_IN_PROGRESS, index=True,
    )
    grading_state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="unsubmitted", server_default="unsubmitted"
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    started_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    questions = relationship(
        "V2AssessmentAttemptQuestion", back_populates="attempt",
        cascade="all, delete-orphan", order_by="V2AssessmentAttemptQuestion.position",
    )


class V2AssessmentAttemptQuestion(Base):
    """Ordered question selection and result for one durable V2 attempt."""

    __tablename__ = "v2_assessment_attempt_questions"
    __table_args__ = (
        UniqueConstraint("attempt_id", "position", name="uq_v2_attempt_question_position"),
        UniqueConstraint("attempt_id", "question_id", name="uq_v2_attempt_question_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("v2_assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question_snapshot: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    submitted_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    grading_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="unsubmitted", server_default="unsubmitted"
    )
    score: Mapped[float | None] = mapped_column(nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pending_grade_id: Mapped[int | None] = mapped_column(
        ForeignKey("pending_grades.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    attempt = relationship("V2AssessmentAttempt", back_populates="questions")


@event.listens_for(V2AssessmentAttemptQuestion, "before_update")
def _prevent_attempt_selection_update(_, __, target) -> None:
    """The server-selected question set becomes immutable once persisted."""
    state = inspect(target)
    protected = ("attempt_id", "question_id", "position", "question_snapshot")
    if any(state.attrs[name].history.has_changes() for name in protected):
        raise ValueError("V2 assessment question selection is immutable.")
