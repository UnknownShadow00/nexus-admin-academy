import json
import logging
import re
from pathlib import Path
from typing import Dict, List

from sqlalchemy.orm import Session
from youtube_transcript_api import YouTubeTranscriptApi

from app.services.ai_service import call_ai

logger = logging.getLogger(__name__)

OBJECTIVES_PATH = Path(__file__).resolve().parents[1] / "data" / "comptia_objectives.json"


def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL format")


def chunk_transcript(transcript_text: str, max_length: int = 10000) -> str:
    if len(transcript_text) <= max_length:
        return transcript_text
    truncated = transcript_text[:max_length]
    boundary = max(truncated.rfind('.'), truncated.rfind('?'), truncated.rfind('!'))
    return transcript_text[: boundary + 1] if boundary > 0 else transcript_text[:max_length]


def load_objectives(domain_id: str) -> list[dict]:
    try:
        raw = json.loads(OBJECTIVES_PATH.read_text(encoding="utf-8"))
        return raw.get(domain_id, [])
    except Exception:
        return []


async def generate_quiz_from_video(
    video_url: str,
    title: str,
    week_number: int,
    db: Session,
    admin_id: int,
    domain_id: str = "1.0",
) -> List[Dict]:
    if not video_url or len(video_url.strip()) < 10:
        raise ValueError("Invalid video URL")
    if not title or len(title.strip()) < 3:
        raise ValueError("Title too short")

    try:
        video_id = extract_video_id(video_url)
    except Exception as exc:
        raise ValueError(f"Invalid video URL: {exc}") from exc

    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as exc:
        logger.exception("transcript_extraction_failed video_id=%s", video_id)
        raise ValueError(f"Failed to extract video transcript: {exc}") from exc

    transcript_text = " ".join(item.get("text", "") for item in transcript_data).strip()
    if len(transcript_text) < 200:
        raise ValueError("Video transcript too short (need at least 200 characters)")

    chunked_transcript = chunk_transcript(transcript_text, max_length=10000)
    objectives = load_objectives(domain_id)
    objective_block = "\n".join([f"- {o.get('id')}: {o.get('title')}" for o in objectives[:6]]) or "- General domain coverage"

    system_prompt = """You are an IT instructor writing certification quiz questions.
Use the provided objective list and transcript as anchors.
Generate EXACTLY 10 unique MCQ questions with 4 options each and one correct answer.
Return ONLY JSON: {"questions": [...]}"""

    user_prompt = f"""Domain: {domain_id}
Objectives:
{objective_block}

Generate 10 questions aligned to these objectives and this transcript.
Include at least 3 questions directly tied to one objective id from the list.

Transcript:
{chunked_transcript}
"""

    response_text = await call_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="quiz_generation",
        db=db,
        user_id=admin_id,
        json_mode=True,
        metadata={"video_url": video_url, "title": title, "week": week_number, "domain_id": domain_id, "user_id": admin_id},
    )

    if not response_text or not response_text.strip():
        raise ValueError("AI returned empty response while generating quiz")

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        logger.error("quiz_generation_invalid_json raw_preview=%s", response_text[:2000])
        raise ValueError("AI returned invalid JSON for quiz generation") from exc

    questions = data.get("questions", [])

    if len(questions) != 10:
        raise ValueError(f"Expected 10 questions, got {len(questions)}")

    question_texts = [q.get("question_text", "").strip() for q in questions]
    if len(question_texts) != len(set(question_texts)):
        raise ValueError("AI generated duplicate questions")

    required_fields = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer", "explanation"]
    for i, q in enumerate(questions, start=1):
        missing = [f for f in required_fields if f not in q]
        if missing:
            raise ValueError(f"Question {i} missing fields: {missing}")
        if q["correct_answer"] not in ["A", "B", "C", "D"]:
            raise ValueError(f"Question {i} has invalid correct_answer: {q['correct_answer']}")

    return questions
