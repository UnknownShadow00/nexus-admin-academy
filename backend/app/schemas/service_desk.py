"""Typed, non-executable scenario definitions and Service Desk API payloads."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScenarioMode(str, Enum):
    LEARNING = "learning"
    SIMULATION = "simulation"


class ScenarioActionKey(str, Enum):
    OPEN_TICKET = "open_ticket"
    INSPECT_REQUESTER = "inspect_requester"
    VERIFY_IDENTITY = "verify_identity"
    SEARCH_ACCOUNT = "search_account"
    INSPECT_ACCOUNT = "inspect_account"
    UNLOCK_ACCOUNT = "unlock_account"
    ADD_RESOLUTION_NOTE = "add_resolution_note"
    RESOLVE_TICKET = "resolve_ticket"
    REQUEST_HINT = "request_hint"


class StateCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    equals: str | bool | int | None


class StateMutation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    value: str | bool | int | None


class ActionBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_payload: dict[str, str | bool | int | None] = Field(default_factory=dict)
    preconditions: list[StateCondition] = Field(default_factory=list)
    mutations: list[StateMutation] = Field(default_factory=list)
    score_key: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,79}$")
    critical_failure: bool = False
    student_feedback: str = Field(min_length=1, max_length=500)


class ActionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: ScenarioActionKey
    tool: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]{0,79}$")
    required_payload_fields: list[str] = Field(default_factory=list)
    preconditions: list[StateCondition] = Field(default_factory=list)
    branches: list[ActionBranch] = Field(min_length=1)
    critical_on_precondition_failure: bool = False
    learning_precondition_feedback: str | None = Field(default=None, max_length=500)
    simulation_precondition_feedback: str = Field(default="This action cannot proceed yet.", min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_branch_matches(self):
        matches = [tuple(sorted(branch.match_payload.items())) for branch in self.branches]
        if len(set(matches)) != len(matches):
            raise ValueError(f"Action {self.key.value} has duplicate branch payload matches")
        if not any(not branch.match_payload for branch in self.branches):
            raise ValueError(f"Action {self.key.value} requires one default branch")
        return self


class ScenarioScoring(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric_version: str = Field(min_length=1, max_length=40)
    passing_score: int = Field(ge=80, le=100)
    point_values: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_total(self):
        if not self.point_values or sum(self.point_values.values()) != 100:
            raise ValueError("Scoring point values must total exactly 100")
        if any(value < 0 or value > 100 for value in self.point_values.values()):
            raise ValueError("Scoring point values must be between 0 and 100")
        return self


class ScenarioFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: str = Field(min_length=1, max_length=1000)
    failed: str = Field(min_length=1, max_length=1000)
    critical_failure: str = Field(min_length=1, max_length=1000)


class ScenarioHealthStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ScenarioActionKey
    payload: dict[str, str | bool | int | None] = Field(default_factory=dict)


class ScenarioDefinition(BaseModel):
    """A declarative, strictly validated scenario definition.

    ``hidden_facts`` are deliberately stored in the immutable version but are
    never included in student projections.
    """

    model_config = ConfigDict(extra="forbid")

    stable_key: str = Field(pattern=r"^[a-z][a-z0-9-]{2,119}$")
    version: int = Field(ge=1)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    category: str = Field(min_length=1, max_length=100)
    difficulty: int = Field(ge=1, le=5)
    supported_modes: set[ScenarioMode] = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1, max_length=20)
    skill_tags: list[str] = Field(min_length=1, max_length=20)
    student_facts: dict[str, Any] = Field(default_factory=dict)
    hidden_facts: dict[str, Any] = Field(default_factory=dict)
    state_schema: dict[str, list[str | bool | int | None]] = Field(min_length=1)
    initial_state: dict[str, str | bool | int | None] = Field(min_length=1)
    student_visible_state_fields: list[str] = Field(min_length=1)
    actions: list[ActionDefinition] = Field(min_length=1)
    success_conditions: list[StateCondition] = Field(min_length=1)
    scoring: ScenarioScoring
    feedback: ScenarioFeedback
    learning_hint: str | None = Field(default=None, max_length=1000)
    health_path: list[ScenarioHealthStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references_and_paths(self):
        state_fields = set(self.state_schema)
        if not set(self.initial_state).issubset(state_fields):
            raise ValueError("Initial state references an unknown state field")
        if not set(self.student_visible_state_fields).issubset(state_fields):
            raise ValueError("Student-visible state references an unknown state field")
        for field, value in self.initial_state.items():
            if value not in self.state_schema[field]:
                raise ValueError(f"Initial state value for {field} is not allowed")

        seen_actions: set[ScenarioActionKey] = set()
        action_score_keys: set[str] = set()
        mutation_fields: set[str] = set()
        for action in self.actions:
            if action.key in seen_actions:
                raise ValueError(f"Duplicate action {action.key.value}")
            seen_actions.add(action.key)
            if len(set(action.required_payload_fields)) != len(action.required_payload_fields):
                raise ValueError(f"Action {action.key.value} repeats a payload field")
            for condition in action.preconditions:
                self._validate_condition(condition, state_fields)
            for branch in action.branches:
                for condition in branch.preconditions:
                    self._validate_condition(condition, state_fields)
                for mutation in branch.mutations:
                    if mutation.field not in state_fields:
                        raise ValueError(f"Action {action.key.value} mutates unknown field {mutation.field}")
                    if mutation.value not in self.state_schema[mutation.field]:
                        raise ValueError(f"Action {action.key.value} sets invalid value for {mutation.field}")
                    mutation_fields.add(mutation.field)
                if branch.score_key:
                    action_score_keys.add(branch.score_key)
        for condition in self.success_conditions:
            self._validate_condition(condition, state_fields)
        if not set(self.scoring.point_values).issubset(action_score_keys):
            raise ValueError("Scoring includes a key not awarded by an action")
        if not {condition.field for condition in self.success_conditions}.issubset(mutation_fields | set(self.initial_state)):
            raise ValueError("Success conditions are unreachable from declared transitions")
        if all(self.initial_state.get(condition.field) == condition.equals for condition in self.success_conditions):
            raise ValueError("Success conditions cannot already be true in the initial state")
        health_actions = {step.action for step in self.health_path}
        if ScenarioActionKey.RESOLVE_TICKET not in health_actions:
            raise ValueError("Scenario health path must include ticket resolution")
        if not health_actions.issubset(seen_actions):
            raise ValueError("Scenario health path references an unknown action")
        return self

    def _validate_condition(self, condition: StateCondition, state_fields: set[str]) -> None:
        if condition.field not in state_fields:
            raise ValueError(f"Condition references unknown state field {condition.field}")
        if condition.equals not in self.state_schema[condition.field]:
            raise ValueError(f"Condition has invalid value for {condition.field}")


class StartAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ScenarioMode


class AttemptActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ScenarioActionKey
    idempotency_key: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    expected_state_version: int = Field(ge=0)
    payload: dict[str, str | bool | int | None] = Field(default_factory=dict)


class ValidateScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    definition: ScenarioDefinition
