"""Nexus V2 Phase 1C — AI grading infrastructure (additive).

Three tables back a submission-first grading pipeline:

* ``pending_grades``        — one durable job per student submission that the
  deterministic grader could not confidently resolve. Mutable *state* row.
* ``ai_grades``             — append-only log of every AI grading attempt for a
  pending grade (timeouts and rejected responses included).
* ``mentor_grade_overrides`` — append-only log of mentor/admin overrides.

No legacy grading/progress table is touched. Phase 1C produces *grades*; wiring
those grades into XP / progression is deliberately deferred (Phase 2), so this
layer can never double-award or complete an activity twice.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

_JSON = JSON().with_variant(JSONB, "postgresql")

# ---- pending_grades.status ------------------------------------------------- #
GRADE_JOB_PENDING = "pending"
GRADE_JOB_PROCESSING = "processing"
GRADE_JOB_GRADED = "graded"
GRADE_JOB_NEEDS_REVIEW = "needs_review"
GRADE_JOB_FAILED_RETRYABLE = "failed_retryable"
GRADE_JOB_FAILED_TERMINAL = "failed_terminal"
GRADE_JOB_STATUSES = {
    GRADE_JOB_PENDING,
    GRADE_JOB_PROCESSING,
    GRADE_JOB_GRADED,
    GRADE_JOB_NEEDS_REVIEW,
    GRADE_JOB_FAILED_RETRYABLE,
    GRADE_JOB_FAILED_TERMINAL,
}
# Statuses a worker is allowed to (re)claim.
GRADE_JOB_CLAIMABLE = {GRADE_JOB_PENDING, GRADE_JOB_FAILED_RETRYABLE}
# Terminal-for-automation statuses (a mentor can still act).
GRADE_JOB_RESOLVED = {GRADE_JOB_GRADED, GRADE_JOB_NEEDS_REVIEW, GRADE_JOB_FAILED_TERMINAL}

# ---- resolved_grade_source ---------------------------------------------------#
GRADE_SOURCE_DETERMINISTIC = "deterministic"
GRADE_SOURCE_AI = "ai"
GRADE_SOURCE_MENTOR = "mentor"

# ---- ai_grades.outcome ------------------------------------------------------ #
AI_OUTCOME_ACCEPTED = "accepted"
AI_OUTCOME_REJECTED_INVALID = "rejected_invalid"
AI_OUTCOME_ERROR_RETRYABLE = "error_retryable"
AI_OUTCOME_ERROR_TERMINAL = "error_terminal"


class PendingGrade(Base):
    __tablename__ = "pending_grades"
    __table_args__ = (
        UniqueConstraint("source_type", "submission_ref", name="uq_pending_grades_submission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # What kind of thing is being graded, and stable identifiers for it.
    source_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    source_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Stable identifier of THIS student submission (caller-supplied). Together
    # with source_type this is the idempotency key.
    submission_ref: Mapped[str] = mapped_column(String(200), nullable=False)

    # Self-contained snapshots so grading + audit never need the origin row.
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_answer: Mapped[str] = mapped_column(Text, nullable=False)
    rubric_json: Mapped[dict | None] = mapped_column(_JSON, nullable=True)
    rubric_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_concepts_json: Mapped[list | None] = mapped_column(_JSON, nullable=True)
    deterministic_result_json: Mapped[dict | None] = mapped_column(_JSON, nullable=True)
    pass_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=GRADE_JOB_PENDING, server_default=GRADE_JOB_PENDING, index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_error_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Safe one-line summary only — never a raw stack trace or infra detail.
    last_error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # The effective/resolved grade (mentor override > accepted AI grade >
    # deterministic). Recomputed by grading_queue.resolve_pending.
    resolved_grade_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ai_grades = relationship(
        "AIGrade", back_populates="pending_grade", cascade="all, delete-orphan",
        order_by="AIGrade.id",
    )
    overrides = relationship(
        "MentorGradeOverride", back_populates="pending_grade", cascade="all, delete-orphan",
        order_by="MentorGradeOverride.id",
    )


class AIGrade(Base):
    """One AI grading attempt. APPEND-ONLY (see listeners below)."""

    __tablename__ = "ai_grades"
    __table_args__ = (
        UniqueConstraint("pending_grade_id", "attempt_number", name="uq_ai_grade_attempt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pending_grade_id: Mapped[int] = mapped_column(
        ForeignKey("pending_grades.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Operator-set label (e.g. "local-vllm"). Never a URL, host, or secret.
    endpoint_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rubric_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(40), nullable=True)

    outcome: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_concepts_json: Mapped[list | None] = mapped_column(_JSON, nullable=True)
    missing_concepts_json: Mapped[list | None] = mapped_column(_JSON, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_recommended: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw_response_json: Mapped[dict | None] = mapped_column(_JSON, nullable=True)

    error_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pending_grade = relationship("PendingGrade", back_populates="ai_grades")


class MentorGradeOverride(Base):
    """A mentor/admin override of the resolved grade. APPEND-ONLY."""

    __tablename__ = "mentor_grade_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pending_grade_id: Mapped[int] = mapped_column(
        ForeignKey("pending_grades.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The override this one supersedes (chain), if any. Nothing is ever deleted.
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("mentor_grade_overrides.id", ondelete="SET NULL"), nullable=True
    )
    mentor_label: Mapped[str] = mapped_column(
        String(120), nullable=False, default="mentor", server_default="mentor"
    )
    override_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    override_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pending_grade = relationship("PendingGrade", back_populates="overrides")


# --------------------------------------------------------------------------- #
# Append-only enforcement — mirrors the Service Desk event pattern
# (service_desk.py: _prevent_attempt_event_update / _delete).
# --------------------------------------------------------------------------- #

@event.listens_for(AIGrade, "before_update")
def _prevent_ai_grade_update(_, __, ___) -> None:  # pragma: no cover - defensive
    raise ValueError("ai_grades rows are append-only; record a new attempt instead.")


@event.listens_for(AIGrade, "before_delete")
def _prevent_ai_grade_delete(_, __, ___) -> None:  # pragma: no cover - defensive
    raise ValueError("ai_grades rows are append-only.")


@event.listens_for(MentorGradeOverride, "before_update")
def _prevent_override_update(_, __, ___) -> None:  # pragma: no cover - defensive
    raise ValueError("mentor_grade_overrides rows are append-only; add a superseding override.")


@event.listens_for(MentorGradeOverride, "before_delete")
def _prevent_override_delete(_, __, ___) -> None:  # pragma: no cover - defensive
    raise ValueError("mentor_grade_overrides rows are append-only.")
