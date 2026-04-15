from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CapstoneTemplate(Base):
    __tablename__ = "capstone_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_level: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    requirements: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    deliverables: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    estimated_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rubric: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CapstoneRun(Base):
    __tablename__ = "capstone_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    capstone_template_id: Mapped[int] = mapped_column(ForeignKey("capstone_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="assigned")
    github_repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    documentation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presentation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool] = mapped_column("pass", Boolean, nullable=False, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

