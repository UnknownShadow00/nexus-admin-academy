from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RootCause(Base):
    __tablename__ = "root_causes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cause_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    break_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (CheckConstraint("severity BETWEEN 1 AND 5", name="ck_incidents_severity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    impacted_services: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    root_cause_id: Mapped[int | None] = mapped_column(ForeignKey("root_causes.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rca_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidentTicket(Base):
    __tablename__ = "incident_tickets"
    __table_args__ = (UniqueConstraint("incident_id", "ticket_id", name="uq_incident_ticket"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    symptom_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dependency_order: Mapped[int | None] = mapped_column(Integer, nullable=True)


class IncidentParticipant(Base):
    __tablename__ = "incident_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)


class RCASubmission(Base):
    __tablename__ = "rca_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    timeline: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    root_cause_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    prevention_recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_awarded: Mapped[int | None] = mapped_column(Integer, nullable=True)
