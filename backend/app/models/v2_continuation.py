"""Durable permission to continue beginner learning; independent of mastery."""

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class V2BeginnerContinuationGrant(Base):
    __tablename__ = "v2_beginner_continuation_grants"
    __table_args__ = (
        UniqueConstraint("student_id", "certification_module_id", name="uq_v2_beginner_continuation_student_module"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    certification_module_id: Mapped[int] = mapped_column(ForeignKey("certification_modules.id", ondelete="RESTRICT"), nullable=False)
    granted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    grant_reason: Mapped[str] = mapped_column(String(32), nullable=False)
