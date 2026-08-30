"""Phase 1C AI-grading settings — all env-driven, read at call time.

Nothing here validates at import: the app must boot with AI grading
unconfigured, in which case ambiguous submissions simply queue for mentor
review. Naming follows the existing ``AI_*`` convention in
``app/services/ai_service.py``; the grading-specific vars layer on top and
fall back to the shared ones where sensible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.config import load_env


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or "").strip()


def _flag(name: str, default: bool) -> bool:
    raw = _get(name).lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class GradingConfig:
    enabled: bool
    base_url: str          # OpenAI-compatible base, e.g. http://gpu-host:8000/v1
    model: str
    api_key: str           # blank for local servers
    endpoint_label: str    # audit label only, never shown to students
    timeout_seconds: float
    max_retries: int
    confidence_threshold: float
    backoff_base_seconds: float
    backoff_max_seconds: float

    @property
    def is_local(self) -> bool:
        return bool(self.base_url) and "openrouter.ai" not in self.base_url

    @property
    def configured(self) -> bool:
        """Usable when enabled, a model is set, and (hosted only) a key exists."""
        if not self.enabled or not self.base_url or not self.model:
            return False
        if not self.is_local and not self.api_key:
            return False
        return True

    def chat_completions_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"


def load_grading_config() -> GradingConfig:
    load_env()
    return GradingConfig(
        enabled=_flag("AI_GRADING_ENABLED", default=False),
        base_url=_get("AI_GRADING_URL") or _get("AI_BASE_URL"),
        model=_get("AI_GRADING_MODEL") or _get("AI_MODEL"),
        api_key=_get("AI_GRADING_API_KEY") or _get("AI_API_KEY"),
        endpoint_label=_get("AI_GRADING_ENDPOINT_LABEL") or "local-ai",
        timeout_seconds=float(_get("AI_GRADING_TIMEOUT") or _get("AI_TIMEOUT_SECONDS") or "45"),
        max_retries=int(_get("AI_GRADING_MAX_RETRIES") or "5"),
        confidence_threshold=float(_get("AI_GRADING_CONFIDENCE_THRESHOLD") or "0.7"),
        backoff_base_seconds=float(_get("AI_GRADING_BACKOFF_BASE_SECONDS") or "60"),
        backoff_max_seconds=float(_get("AI_GRADING_BACKOFF_MAX_SECONDS") or "3600"),
    )


def next_retry_delay_seconds(retry_count: int, cfg: GradingConfig) -> float:
    """Exponential backoff with a hard ceiling. retry_count is the number of
    attempts already made (0 -> first retry waits backoff_base)."""
    delay = cfg.backoff_base_seconds * (2 ** max(0, retry_count))
    return float(min(delay, cfg.backoff_max_seconds))
