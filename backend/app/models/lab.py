from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LabTemplate(Base):
    __tablename__ = "lab_templates"
    __table_args__ = (CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_lab_templates_difficulty"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lab_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    environment_requirements: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    setup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    break_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    required_evidence: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    hints: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    model_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LabRun(Base):
    __tablename__ = "lab_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lab_template_id: Mapped[int] = mapped_column(ForeignKey("lab_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="assigned")
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

