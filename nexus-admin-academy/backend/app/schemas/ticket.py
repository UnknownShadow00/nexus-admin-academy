from pydantic import BaseModel, Field


class TicketCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    difficulty: int = Field(ge=1, le=5)
    week_number: int = Field(ge=1)
    category: str | None = Field(default="general", max_length=100)


class TicketSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    writeup: str = Field(min_length=10, max_length=5000)
    collaborator_ids: list[int] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    grade_now: bool = True
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)


class OverrideRequest(BaseModel):
    new_score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=4000)


class ManualReviewRequest(BaseModel):
    new_score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=4000)
