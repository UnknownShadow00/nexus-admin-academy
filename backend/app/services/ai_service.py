import json
import logging
import os
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import load_env

logger = logging.getLogger(__name__)

load_env()

AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "600"))
TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.6"))
TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))


class AIServiceError(Exception):
    pass


def _get_ollama_config() -> tuple[str, str]:
    base_url = (os.getenv("AI_BASE_URL") or "http://192.168.0.104:11434/v1").rstrip("/")
    model = (os.getenv("AI_MODEL") or "deepseek-r1:32b").strip()
    return base_url, model


async def _single_ollama_call(body: dict, feature: str) -> tuple[str, dict]:
    base_url, _ = _get_ollama_config()
    url = f"{base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=float(TIMEOUT_SECONDS)) as client:
            response = await client.post(url, headers={"Content-Type": "application/json"}, json=body)

        if response.status_code != 200:
            logger.error(
                "ollama_non_200 feature=%s status=%s body_preview=%s",
                feature,
                response.status_code,
                response.text[:2000],
            )

        response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.exception("ollama_timeout feature=%s timeout=%ss", feature, TIMEOUT_SECONDS)
        raise HTTPException(status_code=504, detail="AI request timed out") from exc
    except httpx.HTTPStatusError as exc:
        logger.exception("ollama_http_error feature=%s status=%s", feature, exc.response.status_code)
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.exception("ollama_request_error feature=%s", feature)
        raise HTTPException(status_code=503, detail="Unable to connect to AI provider (Ollama)") from exc

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        logger.error("ollama_invalid_json feature=%s raw_preview=%s", feature, response.text[:2000])
        raise HTTPException(status_code=502, detail="AI provider returned invalid JSON response") from exc

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        logger.error("ollama_missing_choices feature=%s keys=%s", feature, list(data.keys()))
        raise HTTPException(status_code=502, detail="AI provider response missing choices")

    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    if not isinstance(message, dict):
        logger.error("ollama_missing_message feature=%s first_choice=%s", feature, str(first_choice)[:500])
        raise HTTPException(status_code=502, detail="AI provider response missing message payload")

    # Use only `content` (final answer) — never `reasoning` (chain-of-thought field deepseek-r1 returns separately)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        logger.error("ollama_empty_content feature=%s message=%s", feature, str(message)[:500])
        raise HTTPException(status_code=502, detail="AI provider returned empty content")

    return content, (data.get("usage", {}) or {})


async def call_ai(
    *,
    system_prompt: str,
    user_prompt: str,
    feature: str,
    db: Session,
    user_id: int = 0,
    json_mode: bool = False,
    metadata: Optional[dict] = None,
    return_usage: bool = False,
) -> str | tuple[str, dict]:
    if not AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI temporarily disabled by administrator")

    if not system_prompt or not user_prompt:
        raise ValueError("Empty prompts not allowed")
    if len(user_prompt.strip()) < 20:
        raise ValueError("User prompt too short (minimum 20 characters)")

    _, model = _get_ollama_config()

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    logger.info("ai_call_start feature=%s user_id=%s model=%s", feature, int(user_id or 0), model)

    content, usage = await _single_ollama_call(body, feature)

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)

    logger.info(
        "ai_call_success feature=%s user_id=%s tokens=%s",
        feature,
        int(user_id or 0),
        total_tokens,
    )

    if return_usage:
        return content, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
    return content


async def ai_health_test(db: Session, user_id: int = 0) -> dict:
    _, model = _get_ollama_config()
    system_prompt = "You are a concise assistant."
    user_prompt = "Reply with exactly: AI connectivity ok"

    content, usage = await call_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="health_check",
        db=db,
        user_id=user_id,
        return_usage=True,
    )

    return {
        "model": model,
        "usage": usage,
        "response_preview": content[:200],
        "success": True,
    }
