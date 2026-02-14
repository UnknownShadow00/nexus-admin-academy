from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    ticket_submissions = relationship("TicketSubmission", back_populates="student", cascade="all, delete-orphan")
    xp_entries = relationship("XPLedger", back_populates="student", cascade="all, delete-orphan")
