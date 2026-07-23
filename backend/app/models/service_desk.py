"""Persistent, versioned Service Desk scenario foundation models.

These models deliberately do not alter legacy ``tickets`` or
``ticket_submissions``.  A Service Desk attempt is an immutable-versioned
simulation record with its own event history and deterministic result.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, event, func, inspect
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


SERVICE_DESK_SCENARIO_STATUSES = {"active", "disabled"}
SERVICE_DESK_VERSION_STATUSES = {"draft", "published", "disabled"}
SERVICE_DESK_ATTEMPT_MODES = {"learning", "simulation"}
SERVICE_DESK_ATTEMPT_STATUSES = {"in_progress", "completed", "failed"}


class ServiceDeskBetaEnrollment(Base):
    """An explicit, auditable allow-list entry for the private beta."""

    __tablename__ = "service_desk_beta_enrollments"
    __table_args__ = (UniqueConstraint("student_id", name="uq_service_desk_beta_enrollment_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    enrolled_by: Mapped[str] = mapped_column(String(120), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ServiceDeskAssignment(Base):
    __tablename__ = "service_desk_assignments"
    __table_args__ = (
        UniqueConstraint("student_id", "scenario_id", "mode", name="uq_service_desk_assignment_student_scenario_mode"),
        CheckConstraint("mode IN ('learning','simulation')", name="ck_service_desk_assignments_mode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("service_desk_scenarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="learning")
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    maximum_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_by: Mapped[str] = mapped_column(String(120), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServiceDeskKnowledgeArticle(Base):
    __tablename__ = "service_desk_knowledge_articles"
    __table_args__ = (UniqueConstraint("stable_id", name="uq_service_desk_knowledge_article_stable_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stable_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    skill_tags: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ServiceDeskAuditLog(Base):
    __tablename__ = "service_desk_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    details_json: Mapped[dict] = mapped_column("details", JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ServiceDeskScenario(Base):
    __tablename__ = "service_desk_scenarios"
    __table_args__ = (
        UniqueConstraint("stable_key", name="uq_service_desk_scenarios_stable_key"),
        CheckConstraint("status IN ('active','disabled')", name="ck_service_desk_scenarios_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stable_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="service_desk")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ServiceDeskScenarioVersion(Base):
    __tablename__ = "service_desk_scenario_versions"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version_number", name="uq_service_desk_scenario_version_number"),
        UniqueConstraint("scenario_id", "definition_hash", name="uq_service_desk_scenario_definition_hash"),
        CheckConstraint("status IN ('draft','published','disabled')", name="ck_service_desk_versions_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("service_desk_scenarios.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="valid")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceDeskAttempt(Base):
    __tablename__ = "service_desk_attempts"
    __table_args__ = (
        UniqueConstraint("student_id", "scenario_version_id", "attempt_number", name="uq_service_desk_attempt_number"),
        CheckConstraint("mode IN ('learning','simulation')", name="ck_service_desk_attempts_mode"),
        CheckConstraint("status IN ('in_progress','completed','failed')", name="ck_service_desk_attempts_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True)
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("service_desk_scenario_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress", index=True)
    current_state: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    current_state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # An administrator may release one terminal simulation attempt from the
    # three-attempt policy without deleting the historical attempt or events.
    admin_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_reset_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ServiceDeskAttemptEvent(Base):
    __tablename__ = "service_desk_attempt_events"
    __table_args__ = (
        UniqueConstraint("attempt_id", "sequence_number", name="uq_service_desk_event_sequence"),
        UniqueConstraint("attempt_id", "idempotency_key", name="uq_service_desk_event_idempotency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("service_desk_attempts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    tool: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict] = mapped_column(
        "payload", JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    previous_state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resulting_state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ServiceDeskAttemptGrade(Base):
    __tablename__ = "service_desk_attempt_grades"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_service_desk_grade_attempt"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("service_desk_attempts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("service_desk_scenario_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rubric_version: Mapped[str] = mapped_column(String(40), nullable=False)
    technical_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    critical_failure: Mapped[bool] = mapped_column(Boolean, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict] = mapped_column(
        "details", JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(ServiceDeskScenarioVersion, "before_update")
def _prevent_published_definition_mutation(_, __, target: ServiceDeskScenarioVersion) -> None:
    """Published definitions are immutable in application writes.

    Status may later move from published to disabled, but the scenario identity,
    version number, checksum, validation status, and definition are historical
    records once publication occurs.
    """
    state = inspect(target)
    was_published = state.attrs.status.history.deleted and state.attrs.status.history.deleted[0] == "published"
    is_published = target.status == "published"
    if not (was_published or is_published):
        return
    immutable_fields = ("scenario_id", "version_number", "definition_json", "definition_hash", "validation_status")
    if any(state.attrs[field].history.has_changes() for field in immutable_fields):
        raise ValueError("Published scenario versions are immutable; create a new draft version.")


@event.listens_for(ServiceDeskAttemptEvent, "before_update")
def _prevent_attempt_event_update(_, __, ___) -> None:
    raise ValueError("Service Desk attempt events are append-only.")


@event.listens_for(ServiceDeskAttemptEvent, "before_delete")
def _prevent_attempt_event_delete(_, __, ___) -> None:
    raise ValueError("Service Desk attempt events are append-only.")
