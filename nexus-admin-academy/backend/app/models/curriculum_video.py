from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CurriculumVideo(Base):
    __tablename__ = "curriculum_videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    section: Mapped[str] = mapped_column(String(200), nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    duration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    quiz_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    video_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
