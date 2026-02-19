from pydantic import BaseModel, Field


class TicketCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    difficulty: int = Field(ge=1, le=5)
    week_number: int = Field(ge=1)
    category: str | None = Field(default="general", max_length=100)
    domain_id: str = Field(default="1.0", max_length=10)
    lesson_id: int | None = Field(default=None, ge=1)
    root_cause: str | None = None
    root_cause_type: str | None = Field(default=None, max_length=50)
    required_checkpoints: dict | None = None
    required_evidence: dict | None = None
    scoring_anchors: dict | None = None
    model_answer: str | None = None


class TicketSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    symptom: str = Field(min_length=3, max_length=2000)
    root_cause: str = Field(min_length=3, max_length=2000)
    resolution: str = Field(min_length=3, max_length=3000)
    verification: str = Field(min_length=3, max_length=2000)
    writeup: str | None = Field(default=None, max_length=5000)
    commands_used: str | None = Field(default=None, max_length=4000)
    collaborator_ids: list[int] = Field(default_factory=list)
    before_screenshot_id: int | None = Field(default=None, ge=1)
    after_screenshot_id: int | None = Field(default=None, ge=1)
    grade_now: bool = True
    duration_minutes: int | None = Field(default=None, ge=0, le=1440)


class OverrideRequest(BaseModel):
    new_score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=4000)


class ManualReviewRequest(BaseModel):
    new_score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=4000)
