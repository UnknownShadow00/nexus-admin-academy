from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    submission_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    validated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by: Mapped[int | None] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True)

