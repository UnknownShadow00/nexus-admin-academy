from sqlalchemy import CHAR, JSON, CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (CheckConstraint("correct_answer IN ('A','B','C','D')", name="ck_questions_correct_answer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint("student_id", "quiz_id", name="uq_student_quiz"),
        CheckConstraint("xp_awarded >= 0", name="ck_quiz_attempts_xp_awarded_non_negative"),
        CheckConstraint("best_score IS NULL OR best_score BETWEEN 0 AND 10", name="ck_quiz_attempts_best_score"),
        CheckConstraint("first_attempt_xp IS NULL OR first_attempt_xp >= 0", name="ck_quiz_attempts_first_attempt_xp_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    answers: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    best_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_attempt_xp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")
