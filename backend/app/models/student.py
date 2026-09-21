from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        # Usernames are case-insensitively unique: "Shak" and "shak" are the
        # same account (mirrored by migration b7c8d9e0f1a2 for existing DBs).
        Index("uq_students_username_lower", text("lower(username)"), unique=True),
    )

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
    auth_state: Mapped[Optional["StudentAuthState"]] = relationship(
        "StudentAuthState",
        back_populates="student",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def _ensure_auth_state(self) -> "StudentAuthState":
        if self.auth_state is None:
            self.auth_state = StudentAuthState()
        return self.auth_state

    @property
    def must_change_password(self) -> bool:
        return bool(self.auth_state and self.auth_state.must_change_password)

    @must_change_password.setter
    def must_change_password(self, value: bool) -> None:
        self._ensure_auth_state().must_change_password = bool(value)

    @property
    def auth_version(self) -> int:
        return int(self.auth_state.auth_version or 0) if self.auth_state else 0

    @auth_version.setter
    def auth_version(self, value: int) -> None:
        self._ensure_auth_state().auth_version = int(value)


class StudentAuthState(Base):
    __tablename__ = "student_auth_states"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        primary_key=True,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default="0",
    )
    auth_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        server_default="0",
    )

    student: Mapped[Student] = relationship("Student", back_populates="auth_state")
