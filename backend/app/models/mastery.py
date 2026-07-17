from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudentDomainMastery(Base):
    __tablename__ = "student_domain_mastery"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    domain_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quiz_score_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quiz_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ticket_score_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    ticket_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mastery_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
