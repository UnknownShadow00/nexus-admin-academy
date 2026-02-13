from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    difficulty: int = Field(ge=1, le=5)
    week_number: int = Field(ge=1)


class TicketCreateResponse(BaseModel):
    ticket_id: int
    title: str


class TicketListItem(BaseModel):
    id: int
    title: str
    difficulty: int
    week_number: int


class TicketListResponse(BaseModel):
    tickets: list[TicketListItem]


class TicketDetailResponse(BaseModel):
    id: int
    title: str
    description: str
    difficulty: int
    week_number: int


class TicketSubmitRequest(BaseModel):
    student_id: int = Field(ge=1)
    writeup: str = Field(min_length=10, max_length=5000)


class TicketFeedback(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    feedback: str


class TicketSubmitResponse(BaseModel):
    submission_id: int
    ai_score: int
    xp_awarded: int
    feedback: TicketFeedback


class SubmissionListItem(BaseModel):
    id: int
    student_name: str
    ticket_title: str
    ai_score: int
    submitted_at: datetime


class SubmissionListResponse(BaseModel):
    submissions: list[SubmissionListItem]


class SubmissionDetailResponse(BaseModel):
    id: int
    student_name: str
    ticket_title: str
    writeup: str
    ai_score: int
    ai_feedback: TicketFeedback
    xp_awarded: int


class OverrideRequest(BaseModel):
    new_score: int = Field(ge=0, le=10)


class OverrideResponse(BaseModel):
    submission_id: int
    old_score: int
    new_score: int
    xp_difference: int
    student_new_total_xp: int
