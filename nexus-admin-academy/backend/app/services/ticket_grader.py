import json
import re

from sqlalchemy.orm import Session

from app.services.ai_service import call_ai


async def grade_ticket_submission(
    ticket_id: int,
    ticket_title: str,
    ticket_description: str,
    student_writeup: str,
    difficulty: int,
    db: Session,
    student_id: int,
) -> dict:
    trimmed = (student_writeup or "").strip()
    if len(trimmed) < 20:
        raise ValueError("Writeup too short (minimum 20 characters)")

    if len(trimmed) > 5000:
        trimmed = trimmed[:5000]

    system_prompt = """You are an IT training instructor grading help desk ticket responses.

STRICT GRADING SCALE (Be Harsh):
- 0-1: Nonsense, one-liners, typos only, completely wrong approach
- 2-3: Minimal effort, vague steps, no verification
- 4-5: Basic attempt with major gaps, missing troubleshooting methodology
- 6-7: Decent work with some issues, missing root cause or verification
- 8-9: Professional, complete, systematic approach with minor improvements needed
- 10: Perfect, comprehensive, professional-grade response

CRITICAL RULES:
- One-sentence answers = 0-1 score
- Responses under 50 characters = 0-1 score
- Typo-filled responses = 0-2 score
- No verification step = Maximum 6/10
- No root cause identified = Maximum 7/10

Return ONLY valid JSON:
{
  "structure_score": 1,
  "technical_score": 1,
  "communication_score": 1,
  "strengths": ["..."],
  "weaknesses": ["..."],
  "feedback": "..."
}"""

    user_prompt = f"""Grade this help desk ticket response:

TICKET: {ticket_title}
DESCRIPTION: {ticket_description}
DIFFICULTY: {difficulty}/5

STUDENT WRITEUP:
{trimmed}
"""

    response_text = await call_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="ticket_grading",
        db=db,
        user_id=student_id,
        json_mode=True,
        metadata={"ticket_id": ticket_id, "difficulty": difficulty, "user_id": student_id},
    )

    grading = json.loads(response_text)
    required_keys = ["structure_score", "technical_score", "communication_score", "strengths", "weaknesses", "feedback"]
    missing = [k for k in required_keys if k not in grading]
    if missing:
        raise ValueError(f"AI grading missing keys: {missing}")

    for key in ["structure_score", "technical_score", "communication_score"]:
        if not isinstance(grading[key], int) or not (0 <= grading[key] <= 10):
            raise ValueError(f"Invalid {key}: {grading[key]}")

    if not isinstance(grading["strengths"], list):
        grading["strengths"] = [str(grading["strengths"])]
    if not isinstance(grading["weaknesses"], list):
        grading["weaknesses"] = [str(grading["weaknesses"])]

    structure_penalty = _calculate_structure_penalty(trimmed)
    structure_score = max(0, int(round(grading["structure_score"] * (1 - structure_penalty))))
    technical_score = grading["technical_score"]
    communication_score = grading["communication_score"]

    final_score = int(
        round(
            (structure_score * 0.3)
            + (technical_score * 0.5)
            + (communication_score * 0.2)
        )
    )
    final_score = max(1, min(10, final_score))

    grading["structure_score"] = structure_score
    grading["technical_score"] = technical_score
    grading["communication_score"] = communication_score
    grading["final_score"] = final_score
    grading["structure_penalty_applied"] = structure_penalty > 0
    return grading


def _calculate_structure_penalty(writeup: str) -> float:
    required_headers = ["symptom:", "root cause:", "resolution:", "verification:"]
    lowered = writeup.lower()
    missing = [h for h in required_headers if h not in lowered]
    if missing:
        return 0.3

    # Penalize mostly-noisy responses even if headers exist.
    tokens = re.findall(r"[a-zA-Z]{3,}", writeup)
    if len(tokens) < 30:
        return 0.3

    return 0.0
