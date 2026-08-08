from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ServiceDeskEventCreate(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=80)
    tool: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    resulting_state: dict[str, Any]
    success: bool


class ServiceDeskActionCreate(BaseModel):
    """A client request; the server derives success and trusted evidence."""
    idempotency_key: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=80)
    tool: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    # Resume state is persisted for cross-device recovery only.  The action
    # transition and objective evaluator never read it as evidence.
    resulting_state: dict[str, Any] = Field(default_factory=dict)


class ServiceDeskSnapshotCreate(BaseModel):
    """An untrusted, versioned browser-resume snapshot.

    This is deliberately separate from ``ServiceDeskActionCreate``: a
    snapshot is not a simulation transition and must never be evaluated as
    grading evidence.
    """
    idempotency_key: str = Field(min_length=1, max_length=120)
    snapshot: dict[str, Any]


class ServiceDeskHintCreate(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=120)
    tool: str = Field(min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    resulting_state: dict[str, Any] | None = None


class ServiceDeskCompleteCreate(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=120)


class ServiceDeskFeedbackCreate(BaseModel):
    mentor_feedback: str = Field(min_length=1)


class ServiceDeskAssignmentCreate(BaseModel):
    student_id: int
    scenario_id: int
    mode: str
    is_required: bool = False
    due_at: datetime | None = None
    maximum_attempts: int | None = Field(default=None, ge=1)


class ServiceDeskScenarioVersionCreate(BaseModel):
    definition_json: dict[str, Any]


class ServiceDeskScenarioCreate(BaseModel):
    stable_key: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: str = Field(min_length=2, max_length=100)
    difficulty: int = Field(ge=1, le=3)
    definition_json: dict[str, Any]


class ServiceDeskScenarioDraftUpdate(BaseModel):
    stable_key: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    category: str = Field(min_length=2, max_length=100)
    difficulty: int = Field(ge=1, le=3)
    definition_json: dict[str, Any]
