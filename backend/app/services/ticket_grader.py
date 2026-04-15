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


async def grade_ticket_with_answer_key(
    *,
    ticket_id: int,
    ticket_title: str,
    root_cause: str | None,
    required_checkpoints: dict | None,
    scoring_anchors: dict | None,
    student_writeup: str,
    db: Session,
    student_id: int,
) -> dict:
    writeup = (student_writeup or "").strip()
    if len(writeup) < 20:
        raise ValueError("Writeup too short (minimum 20 characters)")
    if len(writeup) > 5000:
        writeup = writeup[:5000]

    checkpoints = (required_checkpoints or {}).get("checkpoints", [])
    checkpoint_score = 0.0
    checkpoints_met: list[str] = []
    checkpoints_missed: list[str] = []

    for checkpoint in checkpoints:
        step = checkpoint.get("step", "Unnamed checkpoint")
        weight = float(checkpoint.get("weight", 0))
        required_mention = checkpoint.get("required_mention", []) or []
        commands = checkpoint.get("commands", []) or []
        terms = [str(x).lower() for x in required_mention + commands]
        mentioned = any(term and term in writeup.lower() for term in terms)
        if mentioned:
            checkpoint_score += weight * 10
            checkpoints_met.append(step)
        else:
            checkpoints_missed.append(step)

    system_prompt = f"""Grade IT ticket response against rubric.

RUBRIC:
{json.dumps(scoring_anchors or {}, indent=2)}

ANSWER KEY:
Root Cause: {root_cause or "Not provided"}
Required Checkpoints: {[c.get("step") for c in checkpoints]}

Return ONLY valid JSON:
{{
  "structure_score": 0,
  "technical_score": 0,
  "communication_score": 0,
  "strengths": ["..."],
  "weaknesses": ["..."],
  "feedback": "Detailed paragraph",
  "root_cause_correct": false
}}"""

    user_prompt = f"""Ticket: {ticket_title}

Student Response:
{writeup}

Checkpoints mentioned: {checkpoints_met}
Checkpoints missed: {checkpoints_missed}

Grade their work."""

    response_text = await call_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="ticket_grading",
        db=db,
        user_id=student_id,
        json_mode=True,
        metadata={"ticket_id": ticket_id, "user_id": student_id},
    )
    ai_grading = json.loads(response_text)

    for key in ["structure_score", "technical_score", "communication_score"]:
        if key not in ai_grading:
            raise ValueError(f"AI grading missing key: {key}")
        ai_grading[key] = int(ai_grading[key])
        if ai_grading[key] < 0 or ai_grading[key] > 10:
            raise ValueError(f"Invalid {key}: {ai_grading[key]}")

    structure = ai_grading["structure_score"]
    technical = ai_grading["technical_score"]
    communication = ai_grading["communication_score"]

    if not ai_grading.get("root_cause_correct", False):
        technical = max(0, technical - 3)

    checkpoint_penalty = len(checkpoints_missed) * 0.5
    technical = max(0, technical - checkpoint_penalty)

    structure_penalty = _calculate_structure_penalty(writeup)
    structure = max(0, int(round(structure * (1 - structure_penalty))))

    final_score = int(round((structure * 0.3) + (technical * 0.5) + (communication * 0.2)))
    final_score = max(1, min(10, final_score))

    strengths = ai_grading.get("strengths", [])
    weaknesses = ai_grading.get("weaknesses", [])
    if not isinstance(strengths, list):
        strengths = [str(strengths)]
    if not isinstance(weaknesses, list):
        weaknesses = [str(weaknesses)]

    return {
        "structure_score": structure,
        "technical_score": int(round(technical)),
        "communication_score": communication,
        "checkpoint_score": round(checkpoint_score, 1),
        "checkpoints_met": checkpoints_met,
        "checkpoints_missed": checkpoints_missed,
        "final_score": final_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "feedback": ai_grading.get("feedback", ""),
        "root_cause_correct": bool(ai_grading.get("root_cause_correct", False)),
    }


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
