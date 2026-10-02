from pydantic import BaseModel, Field


class GuidedPracticalNote(BaseModel):
    reported: str = Field(default="", max_length=2000)
    checked: str = Field(default="", max_length=2000)
    found: str = Field(default="", max_length=2000)
    verified_or_not_verified: str = Field(default="", max_length=2000)
    next_step: str = Field(default="", max_length=2000)


class LabSubmitRequest(BaseModel):
    notes: str = Field(default="", max_length=10000)
    guided_note: GuidedPracticalNote | None = None
    answers: dict[str, list[str]] | None = None


class LabVerifyRequest(BaseModel):
    answers: dict[str, list[str]]
    inspected_panel_ids: list[str] = Field(default_factory=list, max_length=100)
