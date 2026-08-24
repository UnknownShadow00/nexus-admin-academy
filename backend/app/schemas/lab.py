from pydantic import BaseModel, Field


class LabSubmitRequest(BaseModel):
    notes: str = Field(default="", max_length=10000)
    answers: dict[str, list[str]] | None = None


class LabVerifyRequest(BaseModel):
    answers: dict[str, list[str]]
    inspected_panel_ids: list[str] = Field(default_factory=list, max_length=100)
