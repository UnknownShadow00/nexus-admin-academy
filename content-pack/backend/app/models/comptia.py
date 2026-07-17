from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ComptiaObjective(Base):
    __tablename__ = "comptia_objectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    objective_number: Mapped[str] = mapped_column(String(10), nullable=False)
    objective_text: Mapped[str] = mapped_column(Text, nullable=False)
    subtopics_json: Mapped[str | None] = mapped_column("subtopics", Text, nullable=True)


class StudentObjectiveProgress(Base):
    __tablename__ = "student_objective_progress"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("comptia_objectives.id", ondelete="CASCADE"), primary_key=True)
    mastery_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_practiced: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
