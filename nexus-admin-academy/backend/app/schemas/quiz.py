from pydantic import BaseModel, Field, HttpUrl, field_validator


class QuizGenerateRequest(BaseModel):
    source_urls: list[HttpUrl] = Field(min_length=1, max_length=5)
    week_number: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=200)
    question_count: int = Field(default=10, ge=5, le=20)
    domain_id: str = Field(default="1.0", max_length=10)
    lesson_id: int | None = Field(default=None, ge=1)


class QuizSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    answers: dict[str, str]

    @field_validator("answers")
    @classmethod
    def answers_must_be_abcde(cls, value: dict[str, str]) -> dict[str, str]:
        valid = {"A", "B", "C", "D", "E"}
        for answer in value.values():
            # Allow multi-select like "A,C" or "A,B,D"
            letters = [l.strip() for l in str(answer).split(",")]
            if not all(l in valid for l in letters if l):
                raise ValueError("Quiz answers must be A/B/C/D/E only")
        return value


class BulkTicketGenerateRequest(BaseModel):
    titles: list[str]
    week_number: int = Field(ge=1)
    difficulty: int = Field(ge=1, le=5)
