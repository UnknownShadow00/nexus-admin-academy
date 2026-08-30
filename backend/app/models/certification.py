"""Nexus V2 certification hierarchy (additive foundation — Phase 1A).

Certification -> CertificationVersion -> CertificationDomain
                                     -> CertificationModule
                                     -> CertificationObjective

These tables are new and empty in production until the V2 objective loader is
run explicitly. Nothing here reads from, writes to, or gates the legacy
``training_weeks`` progression system. Certification versions are stored as
data; no progression code branches on a hardcoded exam-code constant.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Importance classification for a lesson or question (PRD §3 of the content
# standard). ``know_it`` is accepted as a legacy alias of ``working_knowledge``
# so the existing ``curriculum_videos.job_relevance`` vocabulary can converge
# here later without a data rewrite.
IMPORTANCE_JOB_CRITICAL = "job_critical"
IMPORTANCE_WORKING_KNOWLEDGE = "working_knowledge"
IMPORTANCE_AWARENESS = "awareness"
IMPORTANCE_VALUES = {
    IMPORTANCE_JOB_CRITICAL,
    IMPORTANCE_WORKING_KNOWLEDGE,
    IMPORTANCE_AWARENESS,
}
IMPORTANCE_ALIASES = {"know_it": IMPORTANCE_WORKING_KNOWLEDGE}


def normalize_importance(value: str | None) -> str | None:
    """Lower-case, apply the legacy alias, return None for blank input."""
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if not cleaned:
        return None
    return IMPORTANCE_ALIASES.get(cleaned, cleaned)


# Learning-relationship classification for a lesson (content standard §4).
LEARNING_RELATIONSHIP_NEW = "new"
LEARNING_RELATIONSHIP_REVIEW = "review"
LEARNING_RELATIONSHIP_DEEP_DIVE = "deep_dive"
LEARNING_RELATIONSHIP_VALUES = {
    LEARNING_RELATIONSHIP_NEW,
    LEARNING_RELATIONSHIP_REVIEW,
    LEARNING_RELATIONSHIP_DEEP_DIVE,
}

# Lesson-to-lesson relationship kinds. A lesson may relate to several earlier
# lessons, so this is a row per relationship, never a single FK column.
LESSON_RELATIONSHIP_BUILDS_ON = "builds_on"
LESSON_RELATIONSHIP_REVIEW_OF = "review_of"
LESSON_RELATIONSHIP_VALUES = {
    LESSON_RELATIONSHIP_BUILDS_ON,
    LESSON_RELATIONSHIP_REVIEW_OF,
}

# Content provenance / reuse permission (content standard §9). Only ``owned``
# and ``permitted`` content is publishable under the V2 rules; Phase 1A only
# records the value, it does not yet enforce a publish gate.
PERMISSION_OWNED = "owned"
PERMISSION_PERMITTED = "permitted"
PERMISSION_REQUESTED = "requested"
PERMISSION_UNKNOWN = "unknown"
PERMISSION_DENIED = "denied"
PERMISSION_STATUS_VALUES = {
    PERMISSION_OWNED,
    PERMISSION_PERMITTED,
    PERMISSION_REQUESTED,
    PERMISSION_UNKNOWN,
    PERMISSION_DENIED,
}
PUBLISHABLE_PERMISSION_STATUSES = {PERMISSION_OWNED, PERMISSION_PERMITTED}


def normalize_permission_status(value: str | None) -> str:
    """Blank -> ``unknown``. Does not validate; callers use is_valid_*."""
    if value is None:
        return PERMISSION_UNKNOWN
    cleaned = str(value).strip().lower()
    return cleaned or PERMISSION_UNKNOWN


def is_publishable_permission(value: str | None) -> bool:
    return normalize_permission_status(value) in PUBLISHABLE_PERMISSION_STATUSES


# Resource kinds (content standard §5). External-first; Nexus stays the tracker.
RESOURCE_TYPE_VIDEO = "video"
RESOURCE_TYPE_ARTICLE = "article"
RESOURCE_TYPE_DOCUMENTATION = "documentation"
RESOURCE_TYPE_EXTERNAL_PRACTICE = "external_practice"
RESOURCE_TYPE_REFERENCE = "reference"
RESOURCE_TYPE_VALUES = {
    RESOURCE_TYPE_VIDEO,
    RESOURCE_TYPE_ARTICLE,
    RESOURCE_TYPE_DOCUMENTATION,
    RESOURCE_TYPE_EXTERNAL_PRACTICE,
    RESOURCE_TYPE_REFERENCE,
}

# Module assessment roles (content standard §7). A module wires up only the
# roles it needs — none is mandatory.
ASSESSMENT_ROLE_QUICK_CHECK = "quick_check"
ASSESSMENT_ROLE_MODULE_QUIZ = "module_quiz"
ASSESSMENT_ROLE_PRACTICAL = "practical"
ASSESSMENT_ROLE_SERVICE_DESK = "service_desk"
ASSESSMENT_ROLE_EXPLAIN = "explain"
ASSESSMENT_ROLE_VALUES = {
    ASSESSMENT_ROLE_QUICK_CHECK,
    ASSESSMENT_ROLE_MODULE_QUIZ,
    ASSESSMENT_ROLE_PRACTICAL,
    ASSESSMENT_ROLE_SERVICE_DESK,
    ASSESSMENT_ROLE_EXPLAIN,
}

# V2 free-form question types (content standard §6.2). Phase 1B stores their
# grading metadata and grades them deterministically only; AI grading is
# Phase 1C. The MCQ types stay in question_validation.SUPPORTED_QUESTION_TYPES.
QUESTION_TYPE_SHORT_ANSWER = "short_answer"
QUESTION_TYPE_FREE_RESPONSE = "free_response"
V2_FREEFORM_QUESTION_TYPES = {QUESTION_TYPE_SHORT_ANSWER, QUESTION_TYPE_FREE_RESPONSE}

# Sentinel stored in the legacy NOT NULL ``questions.correct_answer`` /
# ``questions.option_a`` for a free-form question — real grading data lives in
# question_v2_meta. Chosen so it can never collide with an option letter.
FREEFORM_CORRECT_ANSWER_SENTINEL = "-"

# Deterministic grade outcomes. ``needs_review`` is the safe "hand to a human
# (or, later, AI) — do not guess" state.
GRADE_STATUS_GRADED = "graded"
GRADE_STATUS_NEEDS_REVIEW = "needs_review"


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = (UniqueConstraint("cert_key", name="uq_certifications_cert_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cert_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions = relationship(
        "CertificationVersion",
        back_populates="certification",
        cascade="all, delete-orphan",
    )


class CertificationVersion(Base):
    __tablename__ = "certification_versions"
    __table_args__ = (
        UniqueConstraint("version_key", name="uq_certification_versions_version_key"),
        UniqueConstraint(
            "certification_id", "version_key", name="uq_certification_versions_cert_version"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    # Exam codes are DATA, carried alongside the version — never a hardcoded
    # constant that progression logic branches on.
    exam_codes: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    effective_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    certification = relationship("Certification", back_populates="versions")
    domains = relationship(
        "CertificationDomain",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    modules = relationship(
        "CertificationModule",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    objectives = relationship(
        "CertificationObjective",
        back_populates="version",
        cascade="all, delete-orphan",
    )


class CertificationDomain(Base):
    __tablename__ = "certification_domains"
    __table_args__ = (
        UniqueConstraint(
            "certification_version_id", "domain_key", name="uq_certification_domains_version_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certification_version_id: Mapped[int] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    weight_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    version = relationship("CertificationVersion", back_populates="domains")


class CertificationModule(Base):
    __tablename__ = "certification_modules"
    __table_args__ = (
        UniqueConstraint("module_key", name="uq_certification_modules_module_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certification_version_id: Mapped[int] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    certification_domain_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_domains.id", ondelete="SET NULL"), nullable=True, index=True
    )
    module_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    skill_promise: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_hint: Mapped[str | None] = mapped_column(String(20), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Read-only migration bridges. They let a later phase map legacy evidence
    # to a V2 module; they never make this module participate in week gating.
    legacy_training_week_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_weeks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    legacy_module_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    version = relationship("CertificationVersion", back_populates="modules")


class CertificationObjective(Base):
    __tablename__ = "certification_objectives"
    __table_args__ = (
        UniqueConstraint(
            "certification_version_id",
            "objective_code",
            name="uq_certification_objectives_version_code",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    certification_version_id: Mapped[int] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain_key: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    objective_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    objective_text: Mapped[str] = mapped_column(Text, nullable=False)
    subtopics: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    version = relationship("CertificationVersion", back_populates="objectives")


class LessonV2Meta(Base):
    """The V2 lesson record — a companion to the legacy ``lessons`` table.

    Kept as a side table (never columns on ``lessons``) so the legacy schema
    stays untouched (owner decision, Phase 1B). A V2 lesson normally has NO
    legacy counterpart (``lesson_id`` is NULL); it is set only when a Markdown
    lesson is deliberately bound to an existing legacy lesson. Identity is
    ``lesson_key``. Body + metadata are synced from a Markdown file by
    ``app.services.v2_lesson_loader``.
    """

    __tablename__ = "lesson_v2_meta"
    __table_args__ = (UniqueConstraint("lesson_id", name="uq_lesson_v2_meta_lesson_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lesson_key: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True, index=True)
    certification_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    certification_module_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_modules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    domain_key: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    learning_relationship: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    content_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lesson = relationship("Lesson", back_populates="v2_meta")
    objective_links = relationship(
        "LessonObjective", cascade="all, delete-orphan", back_populates="lesson_meta"
    )


class QuestionV2Meta(Base):
    """Companion 1:1 extension of ``questions`` for V2 hierarchy + provenance.

    Kept as a side table (not columns on ``questions``) so Phase 1A leaves the
    legacy ``questions`` schema untouched — historical data-migrations that
    INSERT via the current ORM keep working. Absence of a row means the
    question has no V2 metadata yet (treated as ``permission_status='unknown'``).
    """

    __tablename__ = "question_v2_meta"
    __table_args__ = (UniqueConstraint("question_id", name="uq_question_v2_meta_question_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    certification: Mapped[str | None] = mapped_column(String(60), nullable=True)
    certification_version: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    certification_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    domain: Mapped[str | None] = mapped_column(String(40), nullable=True)
    module: Mapped[str | None] = mapped_column(String(120), nullable=True)
    objective_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PERMISSION_UNKNOWN, server_default=PERMISSION_UNKNOWN, index=True
    )
    # --- Phase 1B: free-form (short_answer / free_response) grading metadata.
    # Only populated for those question types; all deterministic, no AI. ---
    question_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    acceptable_answers: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list, server_default="[]"
    )
    answer_match_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normalized", server_default="normalized"
    )
    expected_concepts: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list, server_default="[]"
    )
    rubric: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict, server_default="{}"
    )
    rubric_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    min_concepts_for_pass: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partial_credit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    question = relationship("Question", back_populates="v2_meta")
    objective_links = relationship(
        "QuestionObjective",
        cascade="all, delete-orphan",
        back_populates="question_meta",
        order_by="QuestionObjective.position",
    )


class QuestionObjective(Base):
    """Ordered many-to-many objective mappings for one V2 question.

    ``QuestionV2Meta.objective_code`` remains the first/primary code for
    backwards compatibility. This table is authoritative for the complete
    ordered set when links exist.
    """

    __tablename__ = "question_objectives"
    __table_args__ = (
        UniqueConstraint(
            "question_v2_meta_id", "objective_id", name="uq_question_objectives_mapping"
        ),
        UniqueConstraint(
            "question_v2_meta_id", "position", name="uq_question_objectives_position"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_v2_meta_id: Mapped[int] = mapped_column(
        ForeignKey("question_v2_meta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    objective_id: Mapped[int] = mapped_column(
        ForeignKey("certification_objectives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question_meta = relationship("QuestionV2Meta", back_populates="objective_links")
    objective = relationship("CertificationObjective")


def question_objective_codes(meta: QuestionV2Meta) -> list[str]:
    """Return all ordered codes, falling back to the legacy primary field."""
    linked = [link.objective.objective_code for link in meta.objective_links if link.objective]
    return linked or ([meta.objective_code] if meta.objective_code else [])


def question_permission_status(question) -> str:
    """Effective permission status for a question — ``unknown`` if unmapped."""
    meta = getattr(question, "v2_meta", None)
    return normalize_permission_status(meta.permission_status if meta else None)


class LessonObjective(Base):
    """Many-to-many: a V2 lesson covers one or more official objectives."""

    __tablename__ = "lesson_objectives"

    lesson_v2_meta_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_v2_meta.id", ondelete="CASCADE"), primary_key=True
    )
    objective_id: Mapped[int] = mapped_column(
        ForeignKey("certification_objectives.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lesson_meta = relationship("LessonV2Meta", back_populates="objective_links")


class LessonRelationship(Base):
    """Directed V2 lesson-to-lesson relationship (``builds_on`` / ``review_of``).

    A lesson can relate to multiple earlier lessons, so this is a join table,
    not a single ``builds_on_lesson_id`` column.
    """

    __tablename__ = "lesson_relationships"
    __table_args__ = (
        UniqueConstraint(
            "from_lesson_meta_id",
            "to_lesson_meta_id",
            "relationship_type",
            name="uq_lesson_relationships_edge",
        ),
        CheckConstraint(
            "from_lesson_meta_id <> to_lesson_meta_id", name="ck_lesson_relationships_no_self_edge"
        ),
        CheckConstraint(
            "relationship_type IN ('builds_on','review_of')",
            name="ck_lesson_relationships_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_lesson_meta_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_v2_meta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_lesson_meta_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_v2_meta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearningResource(Base):
    """A learning resource (external-first): video / article / doc / practice /
    reference. URLs are DATA here, never hardcoded into application logic."""

    __tablename__ = "v2_resources"
    __table_args__ = (
        UniqueConstraint("resource_key", name="uq_v2_resources_resource_key"),
        CheckConstraint(
            "resource_type IN ('video','article','documentation','external_practice','reference')",
            name="ck_v2_resources_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(160), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    certification_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    duration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PERMISSION_UNKNOWN, server_default=PERMISSION_UNKNOWN, index=True
    )
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    links = relationship("LearningResourceLink", cascade="all, delete-orphan", back_populates="resource")


class LearningResourceLink(Base):
    """Attaches a resource to a V2 lesson and/or module, required or optional."""

    __tablename__ = "v2_resource_links"
    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "lesson_v2_meta_id",
            "certification_module_id",
            name="uq_v2_resource_links_target",
        ),
        CheckConstraint(
            "lesson_v2_meta_id IS NOT NULL OR certification_module_id IS NOT NULL",
            name="ck_v2_resource_links_has_target",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("v2_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_v2_meta_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson_v2_meta.id", ondelete="CASCADE"), nullable=True, index=True
    )
    certification_module_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_modules.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resource = relationship("LearningResource", back_populates="links")


class StudentResourceActivity(Base):
    """Per-student resource tracking. Covers Nexus-tracked completion AND
    externally-reported practice. A reported score is NEVER mastery — no gate
    evaluator reads this table."""

    __tablename__ = "v2_student_resource_activity"
    __table_args__ = (
        UniqueConstraint("student_id", "resource_id", name="uq_v2_student_resource_activity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("v2_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opened_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    student_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    confusing_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_for_mentor: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ModuleAssessment(Base):
    """Data-driven wiring from a V2 module to an assessment role. REFERENCES
    the existing Quiz / Lab / Service Desk engines — it never reimplements
    them. A module wires up only the roles it needs."""

    __tablename__ = "module_assessments"
    __table_args__ = (
        UniqueConstraint("assessment_key", name="uq_module_assessments_key"),
        CheckConstraint(
            "assessment_role IN ('quick_check','module_quiz','practical','service_desk','explain')",
            name="ck_module_assessments_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    assessment_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    certification_module_id: Mapped[int] = mapped_column(
        ForeignKey("certification_modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_v2_meta_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson_v2_meta.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assessment_role: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quiz_id: Mapped[int | None] = mapped_column(
        ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lab_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("lab_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_desk_scenario_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_desk_scenarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    displayed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=70, server_default="70")
    config: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict, server_default="{}"
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InterviewPrompt(Base):
    """A data-driven Explain / interview prompt. No AI evaluation in Phase 1B —
    only prompt + rubric storage."""

    __tablename__ = "interview_prompts"
    __table_args__ = (UniqueConstraint("prompt_key", name="uq_interview_prompts_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prompt_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    certification_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    certification_module_id: Mapped[int | None] = mapped_column(
        ForeignKey("certification_modules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    domain_key: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_concepts: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list, server_default="[]"
    )
    rubric: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict, server_default="{}"
    )
    rubric_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_answer_outline: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    objective_links = relationship(
        "InterviewPromptObjective", cascade="all, delete-orphan", back_populates="prompt"
    )


class InterviewPromptObjective(Base):
    __tablename__ = "interview_prompt_objectives"

    interview_prompt_id: Mapped[int] = mapped_column(
        ForeignKey("interview_prompts.id", ondelete="CASCADE"), primary_key=True
    )
    objective_id: Mapped[int] = mapped_column(
        ForeignKey("certification_objectives.id", ondelete="CASCADE"), primary_key=True
    )

    prompt = relationship("InterviewPrompt", back_populates="objective_links")
