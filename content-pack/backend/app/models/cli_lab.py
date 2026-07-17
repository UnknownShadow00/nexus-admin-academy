import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CliLab(Base):
    __tablename__ = "cli_lab"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    compartment_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    vendor_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False, default="Beginner")
    est_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    content: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempts = relationship("CliLabAttempt", back_populates="lab", cascade="all, delete-orphan")


class CliLabAttempt(Base):
    __tablename__ = "cli_lab_attempt"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    lab_id: Mapped[str] = mapped_column(ForeignKey("cli_lab.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    command_log: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)

    lab = relationship("CliLab", back_populates="attempts")
