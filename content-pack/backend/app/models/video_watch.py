from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VideoWatch(Base):
    __tablename__ = "video_watches"
    __table_args__ = (UniqueConstraint("student_id", "video_key", name="uq_video_watches"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    video_key: Mapped[str] = mapped_column(String(200), nullable=False)
    watched_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
