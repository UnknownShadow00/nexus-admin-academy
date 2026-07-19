from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.models.quiz import EDITORIAL_STATUSES, QUIZ_PURPOSES, SOURCE_TYPES


ALLOWED_QUIZ_STATUSES = {"draft", "published"}


class QuizGenerateRequest(BaseModel):
    source_urls: list[HttpUrl] = Field(min_length=1, max_length=5)
    week_number: int = Field(ge=0, le=24)
    title: str = Field(min_length=3, max_length=200)
    question_count: int = Field(default=10, ge=5, le=20)
    domain_id: str = Field(default="1.0", max_length=10)
    lesson_id: int | None = Field(default=None, ge=1)


class QuizUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    week_number: int | None = Field(default=None, ge=0, le=24)
    domain_id: str | None = Field(default=None, max_length=10)
    status: str | None = None
    quiz_purpose: str | None = None
    is_required: bool | None = None
    show_in_weekly_checklist: bool | None = None
    show_in_practice_library: bool | None = None
    editorial_status: str | None = None
    recommended_week: int | None = Field(default=None, ge=0, le=24)
    prerequisite_week: int | None = Field(default=None, ge=0, le=24)
    quality_score: int | None = Field(default=None, ge=0, le=100)
    source_type: str | None = None
    answer_keys_validated: bool | None = None
    explanations_complete: bool | None = None
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Quiz title cannot be blank")
        return stripped

    @field_validator("domain_id")
    @classmethod
    def domain_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Quiz domain_id cannot be blank")
        return stripped

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in ALLOWED_QUIZ_STATUSES:
            raise ValueError("Quiz status must be draft or published")
        return normalized

    @field_validator("quiz_purpose")
    @classmethod
    def purpose_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in QUIZ_PURPOSES:
            raise ValueError(f"Quiz purpose must be one of: {', '.join(sorted(QUIZ_PURPOSES))}")
        return normalized

    @field_validator("editorial_status")
    @classmethod
    def editorial_status_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in EDITORIAL_STATUSES:
            raise ValueError(f"Editorial status must be one of: {', '.join(sorted(EDITORIAL_STATUSES))}")
        return normalized

    @field_validator("source_type")
    @classmethod
    def source_type_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in SOURCE_TYPES:
            raise ValueError(f"Source type must be one of: {', '.join(sorted(SOURCE_TYPES))}")
        return normalized

    @model_validator(mode="after")
    def checklist_requires_required(self):
        if self.show_in_weekly_checklist is True and self.is_required is False:
            raise ValueError("A weekly checklist quiz must be required")
        return self


class QuizSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    answers: dict[str, str]
    time_per_question: dict[str, int] | None = Field(default=None)

    @field_validator("answers")
    @classmethod
    def answers_must_be_valid_option_letters(cls, value: dict[str, str]) -> dict[str, str]:
        valid = {"A", "B", "C", "D", "E", "F", "G", "H"}
        normalized: dict[str, str] = {}
        for key, answer in value.items():
            # Allow multi-select like "A,C" or "a, c" — normalize to uppercase.
            letters = [l.strip().upper() for l in str(answer).split(",")]
            if not all(l in valid for l in letters if l):
                raise ValueError("Quiz answers must use option letters A through H only")
            normalized[key] = ",".join(l for l in letters if l)
        return normalized


class BulkTicketGenerateRequest(BaseModel):
    titles: list[str]
    week_number: int = Field(ge=1, le=24)
    difficulty: int = Field(ge=1, le=5)
