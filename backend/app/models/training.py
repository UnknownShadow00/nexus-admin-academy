from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


TRAINING_ACTIVITY_TYPES = {
    "video",
    "quiz",
    "lesson",
    "guided_lab",
    "networking_lab",
    "support_ticket",
    "command_exercise",
    "terminal_exercise",
    "review",
    "capstone",
    "service_desk_scenario",
}


class TrainingWeek(Base):
    __tablename__ = "training_weeks"
    __table_args__ = (
        UniqueConstraint("week_number", name="uq_training_weeks_number"),
        CheckConstraint("week_number >= 0", name="ck_training_weeks_number_non_negative"),
        CheckConstraint("display_order >= 0", name="ck_training_weeks_order_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_goals: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    requires_previous_week: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    activities = relationship(
        "TrainingWeekActivity",
        back_populates="week",
        cascade="all, delete-orphan",
        foreign_keys="TrainingWeekActivity.training_week_id",
    )


class TrainingWeekActivity(Base):
    __tablename__ = "training_week_activities"
    __table_args__ = (
        UniqueConstraint("stable_id", name="uq_training_week_activities_stable_id"),
        UniqueConstraint("training_week_id", "display_order", name="uq_training_week_activity_order"),
        CheckConstraint("display_order >= 0", name="ck_training_activities_order_non_negative"),
        CheckConstraint("estimated_minutes IS NULL OR estimated_minutes >= 0", name="ck_training_activities_minutes_non_negative"),
        CheckConstraint(
            "activity_type IN ('video','quiz','lesson','guided_lab','networking_lab','support_ticket','command_exercise','terminal_exercise','review','capstone','service_desk_scenario')",
            name="ck_training_activities_type",
        ),
        CheckConstraint("prerequisite_mode IN ('soft','hard')", name="ck_training_activities_prerequisite_mode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stable_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    training_week_id: Mapped[int] = mapped_column(
        ForeignKey("training_weeks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prerequisite_activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_week_activities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prerequisite_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="soft", server_default="soft")
    metadata_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    week = relationship("TrainingWeek", back_populates="activities", foreign_keys=[training_week_id])
    prerequisite_activity = relationship(
        "TrainingWeekActivity", remote_side=[id], foreign_keys=[prerequisite_activity_id]
    )
