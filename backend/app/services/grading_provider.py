"""AI grading provider abstraction (Phase 1C).

Nexus talks to ONE internal interface, ``GradingProvider``. The default
implementation, ``HttpGradingProvider``, speaks the OpenAI-compatible
``/chat/completions`` protocol, so any of vLLM, Ollama, LM Studio, or a hosted
gateway can serve it without a Nexus code change.

This layer never raises ``HTTPException`` and never touches the database — it
is safe to call from the background worker. Every failure is mapped to a small,
safe taxonomy the queue understands.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.services.ai_service import extract_json_payload
from app.services.grading_config import GradingConfig, load_grading_config
from app.services.grading_prompt import (
    GRADING_PROMPT_VERSION,
    build_system_prompt,
    build_user_prompt,
)
from app.services.grading_schema import (
    GRADING_SCHEMA_VERSION,
    RESPONSE_JSON_SCHEMA,
    AIGradeResponse,
    SchemaRejection,
    parse_ai_grade,
)

PROVIDER_HTTP = "http_openai_compatible"
PROVIDER_DISABLED = "disabled"

# outcome values
OUTCOME_OK = "ok"
OUTCOME_RETRYABLE = "retryable"
OUTCOME_TERMINAL = "terminal"

_RAW_PREVIEW_CHARS = 4000


@dataclass
class GradingRequest:
    question_text: str
    student_answer: str
    expected_concepts: list | None = None
    rubric: dict | None = None
    rubric_version: str | None = None
    pass_threshold: float | None = None
    deterministic_findings: dict | None = None


@dataclass
class ProviderResult:
    outcome: str                       # ok | retryable | terminal
    provider: str
    model: str | None = None
    endpoint_label: str | None = None
    prompt_version: str = GRADING_PROMPT_VERSION
    schema_version: str = GRADING_SCHEMA_VERSION
    parsed: AIGradeResponse | None = None
    raw_json: dict | None = None
    error_category: str | None = None
    error_message: str | None = None   # always safe: no URLs, keys, stack traces
    latency_ms: int | None = None
    extra: dict = field(default_factory=dict)


class GradingProvider(Protocol):
    def grade(self, request: GradingRequest) -> ProviderResult: ...


class DisabledGradingProvider:
    """Used when AI grading is turned off or unconfigured. Always terminal —
    the queue routes the job to mentor review instead of retrying forever."""

    provider = PROVIDER_DISABLED

    def grade(self, request: GradingRequest) -> ProviderResult:  # noqa: ARG002
        return ProviderResult(
            outcome=OUTCOME_TERMINAL,
            provider=PROVIDER_DISABLED,
            error_category="disabled",
            error_message="AI grading is disabled; routed to mentor review.",
        )


class HttpGradingProvider:
    provider = PROVIDER_HTTP

    def __init__(self, cfg: GradingConfig):
        self._cfg = cfg

    def grade(self, request: GradingRequest) -> ProviderResult:
        cfg = self._cfg
        body = {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {
                    "role": "user",
                    "content": build_user_prompt(
                        question_text=request.question_text,
                        student_answer=request.student_answer,
                        expected_concepts=request.expected_concepts,
                        rubric=request.rubric,
                        rubric_version=request.rubric_version,
                        pass_threshold=request.pass_threshold,
                        deterministic_findings=request.deterministic_findings,
                    ),
                },
            ],
            "temperature": 0.0,
            "max_tokens": 700,
            # Prefer strict JSON-schema decoding; fall back to json_object.
            "response_format": {"type": "json_schema", "json_schema": RESPONSE_JSON_SCHEMA},
        }
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"

        started = time.monotonic()
        try:
            with httpx.Client(timeout=cfg.timeout_seconds) as client:
                resp = client.post(cfg.chat_completions_url(), headers=headers, json=body)
        except httpx.TimeoutException:
            return self._fail(OUTCOME_RETRYABLE, "timeout", "AI request timed out.", started)
        except httpx.RequestError:
            return self._fail(OUTCOME_RETRYABLE, "connection", "Could not reach the AI service.", started)

        latency_ms = int((time.monotonic() - started) * 1000)

        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            return self._fail(
                OUTCOME_RETRYABLE, "provider_http_5xx",
                f"AI service returned HTTP {resp.status_code}.", started, latency_ms,
            )
        if resp.status_code >= 400:
            return self._fail(
                OUTCOME_TERMINAL, "provider_http_4xx",
                f"AI service rejected the request (HTTP {resp.status_code}).", started, latency_ms,
            )

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            return self._fail(
                OUTCOME_RETRYABLE, "malformed_envelope",
                "AI service response envelope was malformed.", started, latency_ms,
            )

        try:
            decoded = json.loads(extract_json_payload(content))
        except (ValueError, TypeError):
            return self._fail(
                OUTCOME_RETRYABLE, "invalid_json",
                "AI response body was not valid JSON.", started, latency_ms,
                raw={"content_preview": str(content)[:_RAW_PREVIEW_CHARS]},
            )

        try:
            parsed = parse_ai_grade(decoded)
        except SchemaRejection as rej:
            return self._fail(
                OUTCOME_RETRYABLE, "invalid_response",
                f"AI response failed schema validation: {rej.reason}", started, latency_ms,
                raw=decoded if isinstance(decoded, dict) else None,
            )

        return ProviderResult(
            outcome=OUTCOME_OK,
            provider=self.provider,
            model=cfg.model,
            endpoint_label=cfg.endpoint_label,
            parsed=parsed,
            raw_json=parsed.model_dump(),
            latency_ms=latency_ms,
        )

    def _fail(
        self,
        outcome: str,
        category: str,
        message: str,
        started: float,
        latency_ms: int | None = None,
        raw: dict | None = None,
    ) -> ProviderResult:
        return ProviderResult(
            outcome=outcome,
            provider=self.provider,
            model=self._cfg.model,
            endpoint_label=self._cfg.endpoint_label,
            error_category=category,
            error_message=message,
            latency_ms=latency_ms if latency_ms is not None else int((time.monotonic() - started) * 1000),
            raw_json=raw,
        )


def get_grading_provider(cfg: GradingConfig | None = None) -> GradingProvider:
    cfg = cfg or load_grading_config()
    if not cfg.configured:
        return DisabledGradingProvider()
    return HttpGradingProvider(cfg)
