from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VmAssignment(Base):
    __tablename__ = "vm_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vmid: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    lab_run_id: Mapped[int] = mapped_column(
        ForeignKey("lab_runs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="provisioning")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    guac_conn_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guac_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provisioning_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provisioning_started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    destroyed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
