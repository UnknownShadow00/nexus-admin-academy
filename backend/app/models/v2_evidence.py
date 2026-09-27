"""V2-only authored requirements and trusted interaction/apply evidence."""

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class V2EvidenceRequirement(Base):
    __tablename__ = "v2_evidence_requirements"
    __table_args__ = (
        UniqueConstraint("module_id", "evidence_type", "ref_key", name="uq_v2_evidence_requirement"),
        CheckConstraint("evidence_type IN ('interaction','apply')", name="ck_v2_evidence_requirement_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("certification_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_key: Mapped[str] = mapped_column(String(200), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class V2EvidenceRecord(Base):
    """Written by a trusted grader/engine integration, never by a student API."""

    __tablename__ = "v2_evidence_records"
    __table_args__ = (
        UniqueConstraint("student_id", "requirement_id", name="uq_v2_evidence_record"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("v2_evidence_requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    satisfied_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_ref: Mapped[str] = mapped_column(String(200), nullable=False)
