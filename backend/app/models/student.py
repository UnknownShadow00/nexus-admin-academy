from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_mentor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default='0')
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    role_since: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    ticket_submissions = relationship("TicketSubmission", back_populates="student", cascade="all, delete-orphan")
    xp_entries = relationship("XPLedger", back_populates="student", cascade="all, delete-orphan")
