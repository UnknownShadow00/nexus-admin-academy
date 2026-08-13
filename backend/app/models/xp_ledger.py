from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class XPLedger(Base):
    __tablename__ = "xp_ledger"
    __table_args__ = (
        Index(
            "uq_xp_ledger_service_desk_mastery",
            "student_id",
            "source_type",
            "source_id",
            unique=True,
            sqlite_where=text("source_type = 'service_desk_mastery'"),
            postgresql_where=text("source_type = 'service_desk_mastery'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    student = relationship("Student", back_populates="xp_entries")
