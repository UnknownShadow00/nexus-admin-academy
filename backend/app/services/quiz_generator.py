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
    # Strip common timestamp params before parsing.
    url = url.split("&t=")[0].split("?t=")[0]
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


def get_transcript_with_fallback(video_id: str) -> list[dict]:
    """
    Try multiple strategies to get a transcript.
    Raises ValueError with a clear user-facing message if all fail.
    """
    try:
        return YouTubeTranscriptApi.get_transcript(video_id)
    except Exception:
        pass

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            try:
                return transcript.fetch()
            except Exception:
                continue
    except Exception:
        pass

    for lang in ["en", "en-US", "en-GB", "a.en"]:
        try:
            return YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        except Exception:
            continue

    raise ValueError(
        "Could not retrieve transcript for this video. "
        "Make sure the video has captions enabled. "
        f"Video ID: {video_id}"
    )


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


async def generate_quiz_from_videos(
    video_urls: list[str],
    title: str,
    week_number: int,
    question_count: int,
    db: Session,
    admin_id: int,
    domain_id: str = "1.0",
) -> List[Dict]:
    """
    Extracts transcripts from each video, distributes questions proportionally,
    generates per-video question batches, merges and deduplicates.
    """
    if not 1 <= len(video_urls) <= 5:
        raise ValueError("Provide between 1 and 5 video URLs")
    if not 5 <= question_count <= 20:
        raise ValueError("Question count must be between 5 and 20")
    if not title or len(title.strip()) < 3:
        raise ValueError("Title too short")

    transcripts: list[dict] = []
    for url in video_urls:
        cleaned_url = url.strip()
        video_id = extract_video_id(cleaned_url)
        try:
            data = get_transcript_with_fallback(video_id)
        except Exception as exc:
            logger.exception("transcript_extraction_failed video_url=%s video_id=%s", cleaned_url, video_id)
            raise ValueError(f"Could not get transcript for {cleaned_url}: {exc}") from exc
        text = " ".join(item.get("text", "") for item in data).strip()
        if len(text) < 200:
            raise ValueError(f"Transcript too short for video: {cleaned_url}")
        transcripts.append({"url": cleaned_url, "video_id": video_id, "text": chunk_transcript(text, 8000)})

    base = question_count // len(transcripts)
    remainder = question_count % len(transcripts)
    distribution = [base + (1 if i < remainder else 0) for i in range(len(transcripts))]

    objectives = load_objectives(domain_id)
    objective_block = "\n".join([f"- {o.get('id')}: {o.get('title')}" for o in objectives[:6]]) or "- General domain coverage"

    all_questions: list[dict] = []
    for i, (transcript, count) in enumerate(zip(transcripts, distribution)):
        system_prompt = f"""You are an IT instructor writing certification quiz questions.
Generate EXACTLY {count} unique MCQ questions with 4 options each.
Each question must have one clearly correct answer.
Return ONLY valid JSON: {{"questions": [...]}}
Each question must have: question_text, option_a, option_b, option_c, option_d, correct_answer (A/B/C/D), explanation"""

        user_prompt = f"""Domain: {domain_id}
Objectives:
{objective_block}

Generate {count} questions from this video transcript. Questions must be directly based on the content below.

Transcript:
{transcript['text']}
"""

        response_text = await call_ai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            feature="quiz_generation",
            db=db,
            user_id=admin_id,
            json_mode=True,
            metadata={
                "video_url": transcript["url"],
                "title": title,
                "week": week_number,
                "domain_id": domain_id,
                "video_index": i,
            },
        )

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as exc:
            logger.error("quiz_generation_invalid_json video_index=%s raw_preview=%s", i, (response_text or "")[:2000])
            raise ValueError(f"AI returned invalid JSON for video {i + 1}") from exc

        questions = data.get("questions", [])
        if len(questions) != count:
            raise ValueError(f"Expected {count} questions from video {i + 1}, got {len(questions)}")

        for question in questions:
            question["source_video_url"] = transcript["url"]
        all_questions.extend(questions)

    required_fields = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer", "explanation"]
    texts: list[str] = []
    for idx, question in enumerate(all_questions, start=1):
        missing = [field for field in required_fields if field not in question]
        if missing:
            raise ValueError(f"Question {idx} missing fields: {missing}")
        if question["correct_answer"] not in ["A", "B", "C", "D"]:
            raise ValueError(f"Question {idx} invalid correct_answer: {question['correct_answer']}")
        texts.append(question["question_text"].strip())

    if len(texts) != len(set(texts)):
        raise ValueError("Duplicate questions detected across videos")

    return all_questions


async def generate_quiz_from_video(
    video_url: str,
    title: str,
    week_number: int,
    db: Session,
    admin_id: int,
    domain_id: str = "1.0",
) -> List[Dict]:
    # Backward-compatible wrapper.
    return await generate_quiz_from_videos(
        video_urls=[video_url],
        title=title,
        week_number=week_number,
        question_count=10,
        db=db,
        admin_id=admin_id,
        domain_id=domain_id,
    )
