import json
import logging
import os
import re
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import load_env

logger = logging.getLogger(__name__)

load_env()

DEFAULT_AI_BASE_URL = "http://192.168.0.104:11434/v1"
DEFAULT_AI_MODEL = "deepseek-r1:32b"

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCED_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


def extract_json_payload(content: str) -> str:
    """deepseek-r1 wraps JSON answers in markdown fences, may emit <think>
    blocks even in json_mode, and sometimes appends prose after the JSON —
    strip all of that so callers can json.loads."""
    text = _THINK_BLOCK_RE.sub("", content).strip()

    fenced = _FENCED_BLOCK_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    # Take the first complete JSON value, ignoring surrounding prose.
    decoder = json.JSONDecoder()
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if starts:
        start = min(starts)
        try:
            _, end = decoder.raw_decode(text[start:])
            return text[start : start + end]
        except json.JSONDecodeError:
            pass

    return text


def _get_ollama_config() -> tuple[str, str, int, float, float]:
    base_url = (os.getenv("AI_BASE_URL") or DEFAULT_AI_BASE_URL).strip().rstrip("/")
    model = (os.getenv("AI_MODEL") or DEFAULT_AI_MODEL).strip()
    try:
        parsed_url = httpx.URL(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.host:
            raise ValueError
        max_tokens = int(os.getenv("MAX_TOKENS", "600"))
        temperature = float(os.getenv("AI_TEMPERATURE", "0.6"))
        timeout_seconds = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
        if not model or max_tokens <= 0 or timeout_seconds <= 0:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Invalid local AI configuration") from exc
    return base_url, model, max_tokens, temperature, timeout_seconds


async def _single_ollama_call(body: dict, feature: str, base_url: str, timeout_seconds: float) -> tuple[str, dict]:
    url = f"{base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
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
        logger.exception("ollama_timeout feature=%s timeout=%ss", feature, timeout_seconds)
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
        if isinstance(message.get("reasoning"), str) and message["reasoning"].strip():
            # deepseek-r1 exhausted max_tokens on chain-of-thought before answering
            raise HTTPException(
                status_code=502,
                detail="AI spent its whole token budget reasoning and returned no answer — increase MAX_TOKENS",
            )
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
    if os.getenv("AI_ENABLED", "true").lower() != "true":
        raise HTTPException(status_code=503, detail="AI temporarily disabled by administrator")

    if not system_prompt or not user_prompt:
        raise ValueError("Empty prompts not allowed")
    if len(user_prompt.strip()) < 20:
        raise ValueError("User prompt too short (minimum 20 characters)")

    base_url, model, max_tokens, temperature, timeout_seconds = _get_ollama_config()

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    logger.info("ai_call_start feature=%s user_id=%s model=%s", feature, int(user_id or 0), model)

    content, usage = await _single_ollama_call(body, feature, base_url, timeout_seconds)

    if json_mode:
        content = extract_json_payload(content)

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
        "model": (os.getenv("AI_MODEL") or DEFAULT_AI_MODEL).strip(),
        "usage": usage,
        "response_preview": content[:200],
        "success": True,
    }
