from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CliLabCompleteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    command_log: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=500,
    )
    duration_ms: int | None = Field(
        default=None,
        ge=0,
        le=24 * 60 * 60 * 1000,
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_camel_case(cls, data):
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if "commandLog" in normalized and "command_log" not in normalized:
            normalized["command_log"] = normalized["commandLog"]
        if "durationMs" in normalized and "duration_ms" not in normalized:
            normalized["duration_ms"] = normalized["durationMs"]
        return normalized
