from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.onboarding import StudentOnboardingPractice
from app.models.student import Student
from app.services.auth_service import get_current_student
from app.services.onboarding_service import get_orientation_state
from app.utils.responses import ok

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OrientationPracticeRequest(BaseModel):
    response: str = Field(min_length=1, max_length=2000)


@router.get("")
def get_onboarding_progress(
    db: Session = Depends(get_db), current_student: Student = Depends(get_current_student)
):
    return ok(get_orientation_state(db, current_student))


@router.put("/practice-response")
def save_orientation_practice(
    payload: OrientationPracticeRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    # This is intentionally not a ticket submission: no XP, AI call, mentor
    # review, leaderboard event, or promotion-gate record is created here.
    state = get_orientation_state(db, current_student)
    if not state["steps"]["lesson_note"] or not state["steps"]["quiz"]:
        raise HTTPException(status_code=409, detail="Save your orientation note and take the Ticketing Systems Quiz before this practice step.")

    row = (
        db.query(StudentOnboardingPractice)
        .filter(StudentOnboardingPractice.student_id == current_student.id)
        .first()
    )
    if row is None:
        row = StudentOnboardingPractice(student_id=current_student.id, response=payload.response.strip())
        db.add(row)
    else:
        row.response = payload.response.strip()
    db.commit()
    return ok({"message": "Nice work — you just saved a practice response. No grading or mentor review is needed.", "onboarding": get_orientation_state(db, current_student)})
