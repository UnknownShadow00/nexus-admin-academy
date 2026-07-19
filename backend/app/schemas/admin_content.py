from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class AdminSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NonEmptyUpdate(AdminSchema):
    @model_validator(mode="after")
    def require_an_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ModuleCreate(AdminSchema):
    code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    target_role: str | None = Field(default=None, max_length=50)
    difficulty_band: int | None = Field(default=None, ge=1, le=5)
    estimated_hours: int | None = Field(default=None, ge=0, le=1000)
    prerequisite_module_id: int | None = Field(default=None, ge=1)
    unlock_threshold: int = Field(default=70, ge=0, le=100)
    module_order: int | None = Field(default=None, ge=0, le=1000)
    active: bool = True


class ModuleUpdate(NonEmptyUpdate):
    code: str | None = Field(default=None, min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    target_role: str | None = Field(default=None, max_length=50)
    difficulty_band: int | None = Field(default=None, ge=1, le=5)
    estimated_hours: int | None = Field(default=None, ge=0, le=1000)
    prerequisite_module_id: int | None = Field(default=None, ge=1)
    unlock_threshold: int | None = Field(default=None, ge=0, le=100)
    module_order: int | None = Field(default=None, ge=0, le=1000)
    active: bool | None = None


class LessonCreate(AdminSchema):
    module_id: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=200)
    video_url: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=20000)
    lesson_order: int = Field(ge=1, le=1000)
    outcomes: list[str] = Field(default_factory=list, max_length=100)
    estimated_minutes: int | None = Field(default=None, ge=0, le=10000)
    required_notes_template: str | None = Field(default=None, max_length=20000)
    status: Literal["draft", "published"] = "draft"


class LessonUpdate(NonEmptyUpdate):
    module_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=3, max_length=200)
    video_url: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=20000)
    lesson_order: int | None = Field(default=None, ge=1, le=1000)
    outcomes: list[str] | None = Field(default=None, max_length=100)
    estimated_minutes: int | None = Field(default=None, ge=0, le=10000)
    required_notes_template: str | None = Field(default=None, max_length=20000)
    status: Literal["draft", "published"] | None = None


class TicketAnswerKeyUpdate(NonEmptyUpdate):
    root_cause: str | None = Field(default=None, max_length=10000)
    root_cause_type: str | None = Field(default=None, max_length=50)
    required_checkpoints: dict[str, Any] | None = None
    required_evidence: dict[str, Any] | None = None
    scoring_anchors: dict[str, Any] | None = None
    model_answer: str | None = Field(default=None, max_length=20000)
    lesson_id: int | None = Field(default=None, ge=1)
    domain_id: str | None = Field(default=None, min_length=1, max_length=10)


class EvidenceReview(NonEmptyUpdate):
    validation_status: Literal["pending", "valid", "suspicious", "rejected"] | None = None
    validation_notes: str | None = Field(default=None, max_length=4000)
    validated_by: int | None = Field(default=None, ge=1)


class LabTemplateBase(AdminSchema):
    lesson_id: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    lab_type: str | None = Field(default=None, max_length=50)
    difficulty: int = Field(default=1, ge=1, le=5)
    week_number: int = Field(default=1, ge=1, le=24)
    estimated_minutes: int | None = Field(default=None, ge=0, le=10000)
    is_published: bool = True
    proxmox_template_vmid: int | None = Field(default=None, ge=1)
    environment_requirements: dict[str, Any] = Field(default_factory=dict)
    setup_instructions: str | None = Field(default=None, max_length=30000)
    break_script: str | None = Field(default=None, max_length=50000)
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    required_evidence: dict[str, Any] = Field(default_factory=dict)
    hints: dict[str, Any] = Field(default_factory=dict)
    model_solution: str | None = Field(default=None, max_length=30000)


class LabTemplateCreate(LabTemplateBase):
    pass


class LabTemplateUpdate(NonEmptyUpdate):
    lesson_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    lab_type: str | None = Field(default=None, max_length=50)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    week_number: int | None = Field(default=None, ge=1, le=24)
    estimated_minutes: int | None = Field(default=None, ge=0, le=10000)
    is_published: bool | None = None
    proxmox_template_vmid: int | None = Field(default=None, ge=1)
    environment_requirements: dict[str, Any] | None = None
    setup_instructions: str | None = Field(default=None, max_length=30000)
    break_script: str | None = Field(default=None, max_length=50000)
    success_criteria: dict[str, Any] | None = None
    required_evidence: dict[str, Any] | None = None
    hints: dict[str, Any] | None = None
    model_solution: str | None = Field(default=None, max_length=30000)


class RootCauseInput(AdminSchema):
    service_area: str | None = Field(default=None, max_length=100)
    cause_type: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=10000)
    break_method: str | None = Field(default=None, max_length=10000)
    fix_method: str | None = Field(default=None, max_length=10000)
    validation_steps: str | None = Field(default=None, max_length=10000)


class IncidentCreate(AdminSchema):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    incident_type: str | None = Field(default=None, max_length=50)
    impacted_services: list[str] = Field(default_factory=list, max_length=100)
    root_cause_id: int | None = Field(default=None, ge=1)
    root_cause: RootCauseInput | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    rca_required: bool = True
    severity: int | None = Field(default=None, ge=1, le=5)


class IncidentTicketCreate(AdminSchema):
    ticket_id: int = Field(ge=1)
    symptom_role: str | None = Field(default=None, max_length=50)
    dependency_order: int | None = Field(default=None, ge=0, le=1000)


class CapstoneTemplateBase(AdminSchema):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    role_level: int | None = Field(default=None, ge=1)
    week_number: int | None = Field(default=None, ge=1, le=24)
    is_published: bool = False
    requirements: dict[str, Any] = Field(default_factory=dict)
    deliverables: dict[str, Any] = Field(default_factory=dict)
    estimated_hours: int | None = Field(default=None, ge=0, le=1000)
    rubric: dict[str, Any] = Field(default_factory=dict)


class CapstoneTemplateCreate(CapstoneTemplateBase):
    pass


class CapstoneTemplateUpdate(NonEmptyUpdate):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    role_level: int | None = Field(default=None, ge=1)
    week_number: int | None = Field(default=None, ge=1, le=24)
    is_published: bool | None = None
    requirements: dict[str, Any] | None = None
    deliverables: dict[str, Any] | None = None
    estimated_hours: int | None = Field(default=None, ge=0, le=1000)
    rubric: dict[str, Any] | None = None


class CommandCreate(AdminSchema):
    command: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=3, max_length=10000)
    syntax: str | None = Field(default=None, max_length=5000)
    example: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=50)
    os: str = Field(default="windows", min_length=1, max_length=20)


class CommandUpdate(NonEmptyUpdate):
    command: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=3, max_length=10000)
    syntax: str | None = Field(default=None, max_length=5000)
    example: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=50)
    os: str | None = Field(default=None, min_length=1, max_length=20)


class ScrapePreviewRequest(AdminSchema):
    url: HttpUrl


class ImportedQuestion(AdminSchema):
    question_text: str = Field(min_length=1, max_length=10000)
    option_a: str = Field(min_length=1, max_length=5000)
    option_b: str = Field(default="", max_length=5000)
    option_c: str = Field(default="", max_length=5000)
    option_d: str = Field(default="", max_length=5000)
    option_e: str | None = Field(default=None, max_length=5000)
    option_f: str | None = Field(default=None, max_length=5000)
    option_g: str | None = Field(default=None, max_length=5000)
    option_h: str | None = Field(default=None, max_length=5000)
    correct_answer: Literal["A", "B", "C", "D", "E", "F", "G", "H"] = "A"
    all_correct_answers: list[Literal["A", "B", "C", "D", "E", "F", "G", "H"]] = Field(default_factory=list, max_length=8)
    explanation: str = Field(default="", max_length=20000)

    @field_validator("correct_answer", mode="before")
    @classmethod
    def normalize_correct_answer(cls, value):
        return str(value or "A").strip().upper()

    @field_validator("all_correct_answers", mode="before")
    @classmethod
    def normalize_all_correct_answers(cls, value):
        if isinstance(value, str):
            value = value.split(",")
        return [str(item).strip().upper() for item in (value or []) if str(item).strip()]


class QuizImportRequest(AdminSchema):
    title: str = Field(default="Imported Quiz", min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    week_number: int = Field(default=1, ge=1, le=24)
    lesson_id: int | None = Field(default=None, ge=1)
    domain_id: str = Field(default="1.0", min_length=1, max_length=10)
    questions: list[ImportedQuestion] = Field(min_length=1, max_length=500)


class QuestionUpdate(NonEmptyUpdate):
    correct_answer: Literal["A", "B", "C", "D", "E", "F", "G", "H"] | None = None
    correct_answers: str | None = Field(default=None, max_length=31, pattern=r"^$|^[A-H](,[A-H])*$")
    explanation: str | None = Field(default=None, max_length=20000)
    question_text: str | None = Field(default=None, min_length=1, max_length=10000)
    option_a: str | None = Field(default=None, min_length=1, max_length=5000)
    option_b: str | None = Field(default=None, max_length=5000)
    option_c: str | None = Field(default=None, max_length=5000)
    option_d: str | None = Field(default=None, max_length=5000)
    option_e: str | None = Field(default=None, max_length=5000)
    option_f: str | None = Field(default=None, max_length=5000)
    option_g: str | None = Field(default=None, max_length=5000)
    option_h: str | None = Field(default=None, max_length=5000)

    @field_validator("correct_answer", mode="before")
    @classmethod
    def normalize_correct_answer(cls, value):
        return str(value).strip().upper() if value is not None else None

    @field_validator("correct_answers", mode="before")
    @classmethod
    def normalize_correct_answers(cls, value):
        if value is None:
            return None
        return ",".join(part.strip().upper() for part in str(value).split(",") if part.strip())
