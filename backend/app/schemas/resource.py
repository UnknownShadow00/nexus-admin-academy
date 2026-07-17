from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ResourceCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    url: HttpUrl
    resource_type: str = Field(min_length=3, max_length=50)
    week_number: int = Field(ge=1)
    category: str | None = Field(default=None, max_length=100)


class ResourceOut(BaseModel):
    id: int
    title: str
    url: str
    resource_type: str
    week_number: int
    category: str | None
    created_at: datetime
