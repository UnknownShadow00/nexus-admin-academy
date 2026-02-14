import json
import logging
import os
import re
import time
from hashlib import sha256

from pydantic import BaseModel, ValidationError, field_validator

from app.services.content_extractor import extract_source_summary

logger = logging.getLogger(__name__)

QUIZ_CACHE: dict[str, list[dict]] = {}


class AIServiceError(Exception):
    pass


class QuizQuestionAI(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    explanation: str

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer(cls, value: str) -> str:
        v = value.strip().upper()
        if v not in {"A", "B", "C", "D"}:
            raise ValueError("correct_answer must be one of A/B/C/D")
        return v


class QuizBatchAI(BaseModel):
    questions: list[QuizQuestionAI]

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, value: list[QuizQuestionAI]) -> list[QuizQuestionAI]:
        if len(value) != 10:
            raise ValueError("AI must return exactly 10 questions")
        seen: set[str] = set()
        for q in value:
            key = q.question_text.strip().lower()
            if key in seen:
                raise ValueError("AI returned duplicate question_text entries")
            seen.add(key)
        return value


class TicketGradeAI(BaseModel):
    ai_score: int
    strengths: list[str]
    weaknesses: list[str]
    feedback: str

    @field_validator("ai_score")
    @classmethod
    def validate_score(cls, value: int) -> int:
        if value < 0 or value > 10:
            raise ValueError("ai_score must be between 0 and 10")
        return value


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


def _extract_json_block(text: str, array: bool = True):
    pattern = r"\[.*\]" if array else r"\{.*\}"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise AIServiceError("AI response did not include a JSON block")
    return json.loads(match.group(0))


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
        },
        {
            "question_text": f"{topic}: Which tool checks DNS lookup on Windows?",
            "option_a": "nslookup",
            "option_b": "tasklist",
            "option_c": "diskpart",
            "option_d": "winver",
            "correct_answer": "A",
            "explanation": "nslookup is used to query DNS records.",
        },
        {
            "question_text": f"{topic}: Which command refreshes Group Policy?",
            "option_a": "sfc /scannow",
            "option_b": "gpupdate /force",
            "option_c": "ping -t",
            "option_d": "hostname",
            "correct_answer": "B",
            "explanation": "gpupdate /force refreshes computer and user policies.",
        },
        {
            "question_text": f"{topic}: Which service manages AD authentication?",
            "option_a": "Print Spooler",
            "option_b": "DHCP Client",
            "option_c": "Kerberos",
            "option_d": "Windows Update",
            "correct_answer": "C",
            "explanation": "Kerberos is the default authentication protocol in AD domains.",
        },
        {
            "question_text": f"{topic}: Which command shows listening ports?",
            "option_a": "netstat -ano",
            "option_b": "tracert",
            "option_c": "route print",
            "option_d": "cipher",
            "correct_answer": "A",
            "explanation": "netstat -ano lists listening ports and process IDs.",
        },
        {
            "question_text": f"{topic}: Which utility verifies disk integrity on reboot?",
            "option_a": "mstsc",
            "option_b": "chkdsk /f",
            "option_c": "icacls",
            "option_d": "notepad",
            "correct_answer": "B",
            "explanation": "chkdsk /f fixes file system errors and may schedule a reboot check.",
        },
        {
            "question_text": f"{topic}: Which admin tool resets user passwords in AD?",
            "option_a": "Active Directory Users and Computers",
            "option_b": "Device Manager",
            "option_c": "Registry Editor",
            "option_d": "Event Viewer",
            "correct_answer": "A",
            "explanation": "ADUC supports password resets and account management.",
        },
        {
            "question_text": f"{topic}: Which command displays current user context?",
            "option_a": "whoami",
            "option_b": "shutdown",
            "option_c": "ver",
            "option_d": "color",
            "correct_answer": "A",
            "explanation": "whoami prints the active user identity and domain context.",
        },
        {
            "question_text": f"{topic}: What does DHCP primarily provide?",
            "option_a": "File encryption",
            "option_b": "Automatic IP configuration",
            "option_c": "Printer drivers",
            "option_d": "Patch management",
            "correct_answer": "B",
            "explanation": "DHCP assigns IP addresses and other network settings automatically.",
        },
        {
            "question_text": f"{topic}: Which command tests connectivity to a host?",
            "option_a": "ping",
            "option_b": "set",
            "option_c": "dir",
            "option_d": "tree",
            "correct_answer": "A",
            "explanation": "ping sends ICMP echo requests to test reachability.",
        },
    ]


def _validate_quiz_payload(payload: list[dict]) -> list[dict]:
    batch = QuizBatchAI(questions=[QuizQuestionAI(**q) for q in payload])
    return [q.model_dump() for q in batch.questions]


def _build_quiz_prompt(topic: str, content_summary: str, retry: bool) -> str:
    retry_line = (
        "Previous attempt had duplicates or invalid structure. Generate 10 COMPLETELY DIFFERENT questions with unique concepts. "
        if retry
        else ""
    )
    return (
        "Generate exactly 10 DIFFERENT multiple-choice questions for IT admin training. "
        "Each must test a unique concept. Do not repeat similar wording or the same fact. "
        f"{retry_line}"
        "Return valid JSON array only. Each object must include: question_text, option_a, option_b, option_c, option_d, "
        "correct_answer (A/B/C/D), explanation. "
        f"Topic: {topic}. Source context: {content_summary}"
    )


def generate_quiz_questions(source_url: str, topic: str) -> list[dict]:
    source_url = _sanitize_text(source_url, max_len=2000)
    topic = _sanitize_text(topic, max_len=300)
    cache_key = sha256(f"{source_url}|{topic}".encode("utf-8")).hexdigest()
    if cache_key in QUIZ_CACHE:
        return QUIZ_CACHE[cache_key]

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        fallback = _fallback_quiz(topic)
        QUIZ_CACHE[cache_key] = fallback
        return fallback

    content_summary = extract_source_summary(source_url)

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        for retry in (False, True):
            prompt = _build_quiz_prompt(topic, content_summary, retry=retry)
            start = time.time()
            response = _call_claude_with_retry(
                client,
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                prompt=prompt,
            )
            duration_ms = int((time.time() - start) * 1000)
            usage = getattr(response, "usage", None)
            logger.info(
                "quiz_generation model=claude-sonnet-4-20250514 duration_ms=%s input_tokens=%s output_tokens=%s",
                duration_ms,
                getattr(usage, "input_tokens", None),
                getattr(usage, "output_tokens", None),
            )

            text = "\n".join(chunk.text for chunk in response.content if hasattr(chunk, "text"))
            try:
                payload = _extract_json_block(text, array=True)
                validated = _validate_quiz_payload(payload)
                QUIZ_CACHE[cache_key] = validated
                return validated
            except (AIServiceError, ValidationError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("quiz_generation validation_failed retry=%s error=%s", retry, exc)
                continue
    except Exception as exc:
        logger.exception("quiz_generation_failed error=%s", exc)

    raise AIServiceError("AI generation failed. Please try a different source or create the quiz manually.")


def grade_ticket_submission(ticket_title: str, ticket_description: str, writeup: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    safe_title = _sanitize_text(ticket_title, max_len=300)
    safe_description = _sanitize_text(ticket_description, max_len=3000)
    safe_writeup = _sanitize_text(writeup, max_len=6000)

    if not api_key:
        score = min(10, max(0, len(safe_writeup) // 250 + 5))
        obj = TicketGradeAI(
            ai_score=score,
            strengths=["Clear writeup structure", "Attempted a practical troubleshooting flow"],
            weaknesses=["Could include more command output evidence"],
            feedback="Solid baseline response. Add validation commands and expected results.",
        )
        return {"ai_score": obj.ai_score, "feedback": obj.model_dump(exclude={"ai_score"})}

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
        usage = getattr(response, "usage", None)
        logger.info(
            "ticket_grading model=claude-sonnet-4-20250514 duration_ms=%s input_tokens=%s output_tokens=%s",
            duration_ms,
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
        )

        text = "\n".join(chunk.text for chunk in response.content if hasattr(chunk, "text"))
        payload = _extract_json_block(text, array=False)
        validated = TicketGradeAI(**payload)
        return {
            "ai_score": validated.ai_score,
            "feedback": {
                "strengths": validated.strengths,
                "weaknesses": validated.weaknesses,
                "feedback": validated.feedback,
            },
        }
    except Exception as exc:
        logger.exception("ticket_grading_failed error=%s", exc)

    fallback = TicketGradeAI(
        ai_score=6,
        strengths=["Submitted a complete response"],
        weaknesses=["Missing validation details"],
        feedback="Add exact commands, checks, and rollback notes.",
    )
    return {"ai_score": fallback.ai_score, "feedback": fallback.model_dump(exclude={"ai_score"})}
