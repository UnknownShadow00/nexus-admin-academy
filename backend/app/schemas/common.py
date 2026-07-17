from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: str


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
