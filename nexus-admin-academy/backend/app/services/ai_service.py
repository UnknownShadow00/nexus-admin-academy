import json
import logging
import os
import re
import time
from hashlib import sha256

from app.services.content_extractor import extract_source_summary

logger = logging.getLogger(__name__)

QUIZ_CACHE: dict[str, list[dict]] = {}


def _call_claude_with_retry(client, *, model: str, max_tokens: int, prompt: str):
    wait_seconds = 1
    for attempt in range(2):
        try:
            return client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            if attempt == 1:
                raise
            time.sleep(wait_seconds)
            wait_seconds *= 2


def _extract_json_block(text: str) -> list[dict] | None:
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        return None
    return None


def _sanitize_text(value: str, max_len: int = 8000) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", value)
    return cleaned.strip()[:max_len]


def _fallback_quiz(topic: str) -> list[dict]:
    return [
        {
            "question_text": f"{topic}: Which command shows full IP configuration on Windows?",
            "option_a": "ip route",
            "option_b": "ipconfig /all",
            "option_c": "net use",
            "option_d": "gpupdate /force",
            "correct_answer": "B",
            "explanation": "ipconfig /all returns detailed adapter and DNS settings.",
        }
    ] * 10


def generate_quiz_questions(source_url: str, topic: str) -> list[dict]:
    source_url = _sanitize_text(source_url, max_len=2000)
    topic = _sanitize_text(topic, max_len=300)
    cache_key = sha256(f"{source_url}|{topic}".encode("utf-8")).hexdigest()
    if cache_key in QUIZ_CACHE:
        return QUIZ_CACHE[cache_key]

    content_summary = extract_source_summary(source_url)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        questions = _fallback_quiz(topic)
        QUIZ_CACHE[cache_key] = questions
        return questions

    prompt = (
        "Generate exactly 10 multiple-choice questions for IT admin training. "
        "Return JSON array only. Each object must include: question_text, option_a, option_b, option_c, option_d, "
        "correct_answer (A/B/C/D), explanation."
        f" Topic: {topic}. Source: {content_summary}"
    )

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        start = time.time()
        response = _call_claude_with_retry(
            client,
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            prompt=prompt,
        )
        duration_ms = int((time.time() - start) * 1000)
        text = "\n".join(chunk.text for chunk in response.content if hasattr(chunk, "text"))
        logger.info("quiz_generation model=claude-sonnet-4-20250514 duration_ms=%s", duration_ms)
        parsed = _extract_json_block(text)
        if parsed and len(parsed) >= 10:
            QUIZ_CACHE[cache_key] = parsed[:10]
            return parsed[:10]
    except Exception as exc:
        logger.exception("quiz generation failed: %s", exc)

    questions = _fallback_quiz(topic)
    QUIZ_CACHE[cache_key] = questions
    return questions


def grade_ticket_submission(ticket_title: str, ticket_description: str, writeup: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    safe_title = _sanitize_text(ticket_title, max_len=300)
    safe_description = _sanitize_text(ticket_description, max_len=3000)
    safe_writeup = _sanitize_text(writeup, max_len=6000)

    if not api_key:
        score = min(10, max(0, len(safe_writeup) // 200 + 5))
        return {
            "ai_score": score,
            "feedback": {
                "strengths": ["Clear writeup structure", "Attempted a practical troubleshooting flow"],
                "weaknesses": ["Could include more command output evidence"],
                "feedback": "Solid baseline response. Add validation commands and expected results.",
            },
        }

    prompt = (
        "Grade this IT support ticket solution from 0-10. Return JSON object only with keys: "
        "ai_score (int), strengths (string array), weaknesses (string array), feedback (string). "
        f"Ticket title: {safe_title}\n"
        f"Ticket description: {safe_description}\n"
        f"Student writeup: {safe_writeup}"
    )

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        start = time.time()
        response = _call_claude_with_retry(
            client,
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            prompt=prompt,
        )
        duration_ms = int((time.time() - start) * 1000)
        logger.info("ticket_grading model=claude-sonnet-4-20250514 duration_ms=%s", duration_ms)

        text = "\n".join(chunk.text for chunk in response.content if hasattr(chunk, "text"))
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            obj = json.loads(match.group(0))
            score = int(obj.get("ai_score", 0))
            return {
                "ai_score": max(0, min(10, score)),
                "feedback": {
                    "strengths": obj.get("strengths", []),
                    "weaknesses": obj.get("weaknesses", []),
                    "feedback": obj.get("feedback", ""),
                },
            }
    except Exception as exc:
        logger.exception("ticket grading failed: %s", exc)

    return {
        "ai_score": 6,
        "feedback": {
            "strengths": ["Submitted a complete response"],
            "weaknesses": ["Missing validation details"],
            "feedback": "Add exact commands, checks, and rollback notes.",
        },
    }
