from pydantic import BaseModel


class CapstoneSubmitRequest(BaseModel):
    notes: str = ""
