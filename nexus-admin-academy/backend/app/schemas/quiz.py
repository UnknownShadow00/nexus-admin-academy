from pydantic import BaseModel, Field, HttpUrl, field_validator


class QuizGenerateRequest(BaseModel):
    source_url: HttpUrl
    week_number: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=200)


class QuizSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    answers: dict[str, str]

    @field_validator("answers")
    @classmethod
    def answers_must_be_abcd(cls, value: dict[str, str]) -> dict[str, str]:
        valid = {"A", "B", "C", "D"}
        for answer in value.values():
            if answer not in valid:
                raise ValueError("Quiz answers must be A/B/C/D only")
        return value


class BulkTicketGenerateRequest(BaseModel):
    titles: list[str]
    week_number: int = Field(ge=1)
    difficulty: int = Field(ge=1, le=5)
