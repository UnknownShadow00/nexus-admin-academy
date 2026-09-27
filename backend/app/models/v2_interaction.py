"""Versioned V2 formative interactions and immutable submitted attempts."""

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


INTERACTION_TYPES = frozenset({
    "matching", "image_identification", "ordering", "command_output",
    "typed_answer", "safe_action",
})


class V2InteractionDefinition(Base):
    __tablename__ = "v2_interaction_definitions"
    __table_args__ = (
        UniqueConstraint("interaction_key", "version", name="uq_v2_interaction_version"),
        CheckConstraint("version > 0", name="ck_v2_interaction_version_positive"),
        CheckConstraint("pass_percent BETWEEN 1 AND 100", name="ck_v2_interaction_pass_percent"),
        CheckConstraint("interaction_type IN ('matching','image_identification','ordering','command_output','typed_answer','safe_action')", name="ck_v2_interaction_type"),
        CheckConstraint("status IN ('draft','published','retired')", name="ck_v2_interaction_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interaction_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    module_id: Mapped[int] = mapped_column(ForeignKey("certification_modules.id", ondelete="RESTRICT"), nullable=False, index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_v2_meta.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pass_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class V2InteractionAttempt(Base):
    __tablename__ = "v2_interaction_attempts"
    __table_args__ = (
        UniqueConstraint("student_id", "interaction_key", "attempt_number", name="uq_v2_interaction_attempt_number"),
        CheckConstraint("attempt_number > 0", name="ck_v2_interaction_attempt_positive"),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_v2_interaction_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("v2_interaction_definitions.id", ondelete="RESTRICT"), nullable=False, index=True)
    interaction_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    response_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    result_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class V2InteractionRequirementChange(Base):
    """Track loader ownership so a 0075 rollback preserves existing 0074 evidence."""

    __tablename__ = "v2_interaction_requirement_changes"

    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("v2_evidence_requirements.id", ondelete="CASCADE"), primary_key=True,
    )
    created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    previous_is_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    previous_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
