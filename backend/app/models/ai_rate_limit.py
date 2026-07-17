from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIRateLimit(Base):
    __tablename__ = "ai_rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    window_start: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
