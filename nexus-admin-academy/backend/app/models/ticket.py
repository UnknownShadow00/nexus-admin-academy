from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_tickets_difficulty"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, default="general")
    objective_ids: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    domain_id: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0", index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_checkpoints: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    required_evidence: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    scoring_anchors: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submissions = relationship("TicketSubmission", back_populates="ticket", cascade="all, delete-orphan")


class TicketSubmission(Base):
    __tablename__ = "ticket_submissions"
    __table_args__ = (
        CheckConstraint("ai_score IS NULL OR ai_score BETWEEN 0 AND 10", name="ck_ticket_submissions_ai_score"),
        CheckConstraint("override_score IS NULL OR override_score BETWEEN 0 AND 10", name="ck_ticket_submissions_override_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    writeup: Mapped[str] = mapped_column(Text, nullable=False)
    commands_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    structure_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    communication_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_feedback: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    submitted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    graded_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_score: Mapped[int] = mapped_column(Integer, nullable=True)
    evidence_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    before_screenshot_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_artifacts.id", ondelete="SET NULL"), nullable=True)
    after_screenshot_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_artifacts.id", ondelete="SET NULL"), nullable=True)
    collaborator_ids: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    methodology_steps_mentioned: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    methodology_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    admin_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    student = relationship("Student", back_populates="ticket_submissions")
    ticket = relationship("Ticket", back_populates="submissions")
