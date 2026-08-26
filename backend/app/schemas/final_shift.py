from pydantic import BaseModel, Field


class IncidentOpenRequest(BaseModel):
    """No body fields needed; the endpoint records server time and order."""


class IncidentActionRequest(BaseModel):
    inspected_panel_ids: list[str] = Field(default_factory=list, max_length=50)
    diagnosis_answer: str | None = Field(default=None, max_length=100)
    action_choice: str | None = Field(default=None, max_length=100)
    documentation: dict[str, str] = Field(default_factory=dict, max_length=10)


class FinalShiftHandoffRequest(BaseModel):
    resolved: str = Field(default="", max_length=4000)
    escalated: str = Field(default="", max_length=4000)
    watch_items: str = Field(default="", max_length=4000)
