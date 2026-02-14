from sqlalchemy.orm import Session

from app.services.ai_service import call_ai


async def generate_ticket_description(title: str, week: int, difficulty: int, db: Session, user_id: int = 0) -> str:
    if not title or len(title.strip()) < 3:
        raise ValueError("Ticket title too short")

    system_prompt = """You are writing ONLY a problem description from a frustrated employee's perspective.

CRITICAL RULES:
- Write like a non-technical user (2-3 sentences max)
- Include urgency/context (for example: meeting in 1 hour)
- DO NOT include solution steps or troubleshooting instructions
- DO NOT include expected outcomes or documentation requirements
- DO NOT sound like an IT trainer
- Use realistic casual language"""

    user_prompt = f"""Write a help desk ticket from a frustrated user's perspective:

Title: {title}
Difficulty: {difficulty}/5

Write 2-3 sentences describing their problem. Make it realistic and urgent."""

    description = await call_ai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        feature="ticket_description",
        db=db,
        user_id=user_id,
        json_mode=False,
        metadata={"title": title, "week": week, "difficulty": difficulty, "user_id": user_id},
    )
    return description.strip()
