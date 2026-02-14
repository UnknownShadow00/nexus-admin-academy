import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import load_env
from app.models.ai_usage_log import AIUsageLog
from app.services.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

load_env()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000")
OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "Nexus Admin Academy")

AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "600"))
TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.6"))
TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
COST_PER_1K_TOKENS = Decimal(str(os.getenv("COST_PER_1K_TOKENS", "0.001")))
DAILY_BUDGET_LIMIT = Decimal(str(os.getenv("DAILY_AI_BUDGET", "1.00")))

if not OPENROUTER_MODEL:
    raise RuntimeError("OPENROUTER_MODEL is required. Use OPENROUTER_MODEL=mistralai/mistral-large")
if "/" not in OPENROUTER_MODEL:
    raise RuntimeError(f"Invalid OPENROUTER_MODEL '{OPENROUTER_MODEL}'. Expected provider/model.")


class AIServiceError(Exception):
    pass


def _today_window() -> tuple[datetime, datetime]:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    return today_start, tomorrow_start


def check_daily_budget(db: Session) -> Decimal:
    today_start, _ = _today_window()
    today_spend = (
        db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0))
        .filter(AIUsageLog.created_at >= today_start)
        .scalar()
        or 0
    )
    return Decimal(str(today_spend))


def estimate_cost(prompt_length: int) -> Decimal:
    estimated_tokens = max(0, prompt_length // 4) + MAX_TOKENS
    return (Decimal(estimated_tokens) / Decimal(1000)) * COST_PER_1K_TOKENS


def _log_usage(
    *,
    db: Session,
    feature: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost_estimate: Decimal,
    metadata_json: Optional[dict] = None,
) -> None:
    try:
        db.add(
            AIUsageLog(
                feature=feature,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_estimate=cost_estimate,
                metadata_json=metadata_json,
            )
        )
        db.commit()
    except Exception as exc:
        logger.exception("ai_usage_log_failed feature=%s model=%s error=%s", feature, model, exc)
        db.rollback()


async def _single_openrouter_call(body: dict, feature: str) -> tuple[str, dict]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_SITE_NAME,
    }

    try:
        async with httpx.AsyncClient(timeout=float(TIMEOUT_SECONDS)) as client:
            response = await client.post(OPENROUTER_URL, headers=headers, json=body)

        if response.status_code != 200:
            logger.error(
                "openrouter_non_200 feature=%s status=%s body_preview=%s",
                feature,
                response.status_code,
                response.text[:2000],
            )

        response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.exception("openrouter_timeout feature=%s timeout=%ss", feature, TIMEOUT_SECONDS)
        raise HTTPException(status_code=504, detail="AI request timed out") from exc
    except httpx.HTTPStatusError as exc:
        logger.exception("openrouter_http_error feature=%s status=%s", feature, exc.response.status_code)
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.exception("openrouter_request_error feature=%s", feature)
        raise HTTPException(status_code=503, detail="Unable to connect to AI provider") from exc

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        logger.error("openrouter_invalid_json feature=%s raw_preview=%s", feature, response.text[:2000])
        raise HTTPException(status_code=502, detail="AI provider returned invalid JSON response") from exc

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        logger.error("openrouter_missing_choices feature=%s keys=%s", feature, list(data.keys()))
        raise HTTPException(status_code=502, detail="AI provider response missing choices")

    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    if not isinstance(message, dict):
        logger.error("openrouter_missing_message feature=%s first_choice=%s", feature, str(first_choice)[:500])
        raise HTTPException(status_code=502, detail="AI provider response missing message payload")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        logger.error("openrouter_empty_content feature=%s message=%s", feature, str(message)[:500])
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

    if not OPENROUTER_API_KEY:
        raise AIServiceError("OPENROUTER_API_KEY not configured")

    if not system_prompt or not user_prompt:
        raise ValueError("Empty prompts not allowed")
    if len(user_prompt.strip()) < 20:
        raise ValueError("User prompt too short (minimum 20 characters)")

    current_spend = check_daily_budget(db)
    _, tomorrow_start = _today_window()
    if current_spend >= DAILY_BUDGET_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "error": "Daily AI budget limit reached ($1.00). Resets at midnight.",
                "retry_after": tomorrow_start.isoformat(),
            },
        )

    estimated_cost = estimate_cost(len(system_prompt) + len(user_prompt))
    if current_spend + estimated_cost > DAILY_BUDGET_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "error": "Daily AI budget limit reached ($1.00). Resets at midnight.",
                "retry_after": tomorrow_start.isoformat(),
            },
        )

    check_rate_limit(user_id, feature, db)

    request_metadata = dict(metadata or {})
    request_metadata["user_id"] = int(user_id or 0)

    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    logger.info(
        "ai_call_start feature=%s user_id=%s est_cost=%s current_spend=%s",
        feature,
        int(user_id or 0),
        str(estimated_cost),
        str(current_spend),
    )

    content, usage = await _single_openrouter_call(body, feature)

    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    actual_cost = (Decimal(total_tokens) / Decimal(1000)) * COST_PER_1K_TOKENS

    _log_usage(
        db=db,
        feature=feature,
        model=OPENROUTER_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_estimate=actual_cost,
        metadata_json=request_metadata,
    )

    logger.info(
        "ai_call_success feature=%s user_id=%s tokens=%s cost=%s",
        feature,
        int(user_id or 0),
        total_tokens,
        str(actual_cost),
    )

    if return_usage:
        return content, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_estimate": float(actual_cost),
        }
    return content


async def ai_health_test(db: Session, user_id: int = 0) -> dict:
    system_prompt = "You are a concise assistant."
    user_prompt = "Reply with exactly: AI connectivity ok"

    content, usage = await call_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="ticket_description",
        db=db,
        user_id=user_id,
        json_mode=False,
        metadata={"healthcheck": True},
        return_usage=True,
    )

    return {
        "model": OPENROUTER_MODEL,
        "usage": usage,
        "response_preview": content[:200],
        "success": True,
    }
