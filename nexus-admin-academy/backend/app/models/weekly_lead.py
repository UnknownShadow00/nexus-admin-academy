from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeeklyDomainLead(Base):
    __tablename__ = "weekly_domain_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    week_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    domain_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    xp_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    badge_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
