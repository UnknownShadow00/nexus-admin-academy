from sqlalchemy import Boolean, CHAR, JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

QUIZ_STATUS_DRAFT = "draft"
QUIZ_STATUS_PUBLISHED = "published"

QUIZ_PURPOSE_REQUIRED = "required"
QUIZ_PURPOSE_PRACTICE = "practice"
QUIZ_PURPOSE_REMEDIATION = "remediation"
QUIZ_PURPOSE_CUMULATIVE = "cumulative"
QUIZ_PURPOSE_GATE = "gate"
QUIZ_PURPOSE_CERTIFICATION = "certification"
QUIZ_PURPOSES = {
    QUIZ_PURPOSE_REQUIRED,
    QUIZ_PURPOSE_PRACTICE,
    QUIZ_PURPOSE_REMEDIATION,
    QUIZ_PURPOSE_CUMULATIVE,
    QUIZ_PURPOSE_GATE,
    QUIZ_PURPOSE_CERTIFICATION,
}

EDITORIAL_STATUS_UNREVIEWED = "unreviewed"
EDITORIAL_STATUS_NEEDS_EDIT = "needs_edit"
EDITORIAL_STATUS_VALIDATED = "validated"
EDITORIAL_STATUS_ARCHIVED = "archived"
EDITORIAL_STATUSES = {
    EDITORIAL_STATUS_UNREVIEWED,
    EDITORIAL_STATUS_NEEDS_EDIT,
    EDITORIAL_STATUS_VALIDATED,
    EDITORIAL_STATUS_ARCHIVED,
}

SOURCE_TYPE_SEED = "seed"
SOURCE_TYPE_EXAMCOMPASS = "examcompass"
SOURCE_TYPE_AI_GENERATED = "ai_generated"
SOURCE_TYPE_MANUAL = "manual"
SOURCE_TYPE_SCRAPED = "scraped"
SOURCE_TYPE_UNKNOWN = "unknown"
SOURCE_TYPES = {
    SOURCE_TYPE_SEED,
    SOURCE_TYPE_EXAMCOMPASS,
    SOURCE_TYPE_AI_GENERATED,
    SOURCE_TYPE_MANUAL,
    SOURCE_TYPE_SCRAPED,
    SOURCE_TYPE_UNKNOWN,
}


class Quiz(Base):
    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint("quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)", name="ck_quizzes_quality_score"),
        CheckConstraint("recommended_week IS NULL OR (recommended_week >= 0 AND recommended_week <= 24)", name="ck_quizzes_recommended_week"),
        CheckConstraint("prerequisite_week IS NULL OR (prerequisite_week >= 0 AND prerequisite_week <= 24)", name="ck_quizzes_prerequisite_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_urls: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    domain_id: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0", index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft", default="draft")
    quiz_purpose: Mapped[str] = mapped_column(String(24), nullable=False, server_default=QUIZ_PURPOSE_PRACTICE, default=QUIZ_PURPOSE_PRACTICE, index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", default=False, index=True)
    show_in_weekly_checklist: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", default=False)
    show_in_practice_library: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1", default=True)
    editorial_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=EDITORIAL_STATUS_UNREVIEWED, default=EDITORIAL_STATUS_UNREVIEWED, index=True)
    recommended_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prerequisite_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False, server_default=SOURCE_TYPE_UNKNOWN, default=SOURCE_TYPE_UNKNOWN, index=True)
    answer_keys_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", default=False, index=True)
    explanations_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1", default=True, index=True)

    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")
    assignments = relationship("QuizAssignment", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = ()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Only option_a is structurally required; the validator enforces "at
    # least 2 non-blank options" at the application layer, so a true/false
    # or 3-option question is not forced to fabricate a 4th one.
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_c: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_d: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_e: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_f: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_g: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_h: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    correct_answers: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    imported_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    import_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", default=False, index=True)
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")

    @property
    def all_correct_answers(self) -> list[str]:
        """Return all correct letters for this question."""
        if self.correct_answers:
            return [item.strip() for item in self.correct_answers.split(",") if item.strip()]
        return [self.correct_answer]

    @property
    def is_multi_select(self) -> bool:
        return bool(self.correct_answers and "," in self.correct_answers)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        # uq_student_quiz removed (TB-06, migration c2d3e4f5a6b7): every attempt
        # is now its own row so retakes never overwrite history.
        CheckConstraint("xp_awarded >= 0", name="ck_quiz_attempts_xp_awarded_non_negative"),
        # best_score/first_attempt_xp are NOT NULL DEFAULT 0 in the real schema
        # (migration 0002) — 0 means "none", never NULL. Model matches the DB.
        CheckConstraint("best_score >= 0", name="ck_quiz_attempts_best_score"),
        CheckConstraint("first_attempt_xp >= 0", name="ck_quiz_attempts_first_attempt_xp_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    answers: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    results: Mapped[list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    best_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    first_attempt_xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    time_per_question: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    student = relationship("Student", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")


class QuizAssignment(Base):
    __tablename__ = "quiz_assignments"
    __table_args__ = (UniqueConstraint("student_id", "quiz_id", name="uq_quiz_assignment_student_quiz"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(80), nullable=False, server_default="mentor_assignment", default="mentor_assignment")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1", default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quiz = relationship("Quiz", back_populates="assignments")
