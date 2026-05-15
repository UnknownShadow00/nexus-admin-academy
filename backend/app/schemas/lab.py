from pydantic import BaseModel, Field


class LabSubmitRequest(BaseModel):
    notes: str = Field(default="", max_length=10000)
