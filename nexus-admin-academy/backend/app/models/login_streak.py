from sqlalchemy import Date, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LoginStreak(Base):
    __tablename__ = "login_streaks"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login: Mapped[Date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
