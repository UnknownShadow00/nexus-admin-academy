"""Strict contract for an AI grading response (Phase 1C).

The model server returns JSON. We do NOT trust it: every field is validated by
Pydantic v2 with explicit bounds. Anything malformed, out of range, wrong type,
or on an unknown ``schema_version`` is rejected and the job stays retryable
(within limits) — a bad AI response never becomes a student's grade.

We use native Pydantic here rather than a wrapper library (see the Phase 1C
note, "libraries rejected"): we control the server, want hard rejection rather
than silent re-prompting, and already have a durable retry queue.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# Bump when the response contract changes. Stored on every ai_grades row.
GRADING_SCHEMA_VERSION = "grading.v1"

# Score is normalised 0..1 on the wire; callers scale to their own point range.
_SCORE_MIN, _SCORE_MAX = 0.0, 1.0


class AIGradeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    score: float = Field(..., ge=_SCORE_MIN, le=_SCORE_MAX)
    passed: bool | None
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_concepts: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    feedback: str = Field(..., max_length=4000)
    review_recommended: bool

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != GRADING_SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version {value!r}")
        return value

    @field_validator("matched_concepts", "missing_concepts", mode="before")
    @classmethod
    def _coerce_concept_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("concept lists must be arrays of strings")
        return [str(item)[:200] for item in value]

    @field_validator("feedback", mode="before")
    @classmethod
    def _coerce_feedback(cls, value):
        if value is None:
            return ""
        return str(value)


class SchemaRejection(Exception):
    """Raised when an AI payload cannot be coerced into AIGradeResponse."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def parse_ai_grade(payload: object) -> AIGradeResponse:
    """Validate an already-JSON-decoded payload. Raises SchemaRejection."""
    if not isinstance(payload, dict):
        raise SchemaRejection("response was not a JSON object")
    try:
        return AIGradeResponse.model_validate(payload)
    except ValidationError as exc:
        # Compact, safe summary — first error only, no payload echo.
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", ())) or "?"
        raise SchemaRejection(f"invalid field '{loc}': {first.get('msg', 'validation error')}") from exc


# JSON Schema handed to servers that support response_format=json_schema
# (vLLM guided decoding, recent Ollama). Advisory — we re-validate regardless.
RESPONSE_JSON_SCHEMA = {
    "name": "nexus_ai_grade",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version", "score", "passed", "confidence",
            "matched_concepts", "missing_concepts", "feedback", "review_recommended",
        ],
        "properties": {
            "schema_version": {"type": "string", "const": GRADING_SCHEMA_VERSION},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "passed": {"type": ["boolean", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "matched_concepts": {"type": "array", "items": {"type": "string"}},
            "missing_concepts": {"type": "array", "items": {"type": "string"}},
            "feedback": {"type": "string"},
            "review_recommended": {"type": "boolean"},
        },
    },
}
