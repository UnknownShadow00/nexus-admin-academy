from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    rank_order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromotionGate(Base):
    __tablename__ = "promotion_gates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    requirement_config: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    effective_from: Mapped[Date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)


class StudentRole(Base):
    __tablename__ = "student_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    promoted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    promoted_by: Mapped[int | None] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    promotion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MethodologyFramework(Base):
    __tablename__ = "methodology_frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    required_for_role: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentMethodologyProgress(Base):
    __tablename__ = "student_methodology_progress"
    __table_args__ = (UniqueConstraint("student_id", "framework_id", name="uq_student_framework"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("methodology_frameworks.id", ondelete="CASCADE"), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiz_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practice_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
