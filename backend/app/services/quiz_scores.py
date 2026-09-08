"""V1 attempt reporting. Legacy score/best_score columns remain raw counts.

Saved per-question results are the historical denominator. Pre-snapshot rows
can only use the current bank, explicitly identified as a legacy estimate.
No quiz-bank edit or reporting read rewrites an attempt.
"""

from typing import TypedDict

from app.models.quiz import QuizAttempt

PASSING_PERCENTAGE = 70


class AttemptScore(TypedDict):
    correct_count: int
    question_count: int
    percentage: float | None
    passed: bool | None
    passing_percentage: int
    attempt_id: int
    submitted_at: str | None
    score_basis: str


def attempt_score(
    attempt: QuizAttempt, fallback_total: int | None = None
) -> AttemptScore:
    snapshot = attempt.results
    if snapshot:
        total = len(snapshot)
        basis = "saved_results"
    else:
        total = (
            fallback_total
            if fallback_total is not None
            else (len(attempt.quiz.questions) or int(attempt.quiz.question_count or 0))
        )
        basis = "current_bank_legacy_estimate"
    passing_percentage = (
        int(snapshot[0].get("passing_percentage", PASSING_PERCENTAGE))
        if snapshot
        else PASSING_PERCENTAGE
    )
    correct = int(attempt.score or 0)
    valid = total > 0 and 0 <= correct <= total
    return {
        "correct_count": correct,
        "question_count": total,
        "percentage": round(correct * 100 / total, 2) if valid else None,
        "passed": correct * 100 >= total * passing_percentage if valid else None,
        "passing_percentage": passing_percentage,
        "attempt_id": attempt.id,
        "submitted_at": attempt.completed_at.isoformat()
        if attempt.completed_at
        else None,
        "score_basis": basis,
    }


def attempt_summary(
    attempts: list[QuizAttempt], fallback_total: int | None = None
) -> dict:
    scores = [attempt_score(row, fallback_total) for row in attempts]
    scores.sort(key=lambda row: (row["submitted_at"] or "", row["attempt_id"]))
    known = [row for row in scores if row["percentage"] is not None]
    best = (
        max(
            known,
            key=lambda row: (
                row["correct_count"] / row["question_count"],
                row["submitted_at"] or "",
                row["attempt_id"],
            ),
        )
        if known
        else None
    )
    earned = any(row["passed"] for row in scores)
    # Before append-only history, best_score could retain passing credit after
    # a lower retry replaced the only row. Preserve that existing completion
    # rule without inventing an identifiable passing attempt or percentage.
    legacy_credit = False
    if not earned:
        for attempt in attempts:
            total = (
                fallback_total
                if fallback_total is not None
                else (
                    len(attempt.quiz.questions) or int(attempt.quiz.question_count or 0)
                )
            )
            if (
                total > 0
                and attempt.best_score > attempt.score
                and attempt.best_score * 100 >= total * PASSING_PERCENTAGE
            ):
                legacy_credit = True
                break
    return {
        "latest_attempt": scores[-1] if scores else None,
        "best_attempt": best,
        "earned_pass": earned or legacy_credit,
        "legacy_passing_credit": legacy_credit,
        "attempts": scores,
    }


def average_attempt_percentage(attempts: list[QuizAttempt]) -> float | None:
    values = [
        score
        for row in attempts
        if (score := attempt_score(row)["percentage"]) is not None
    ]
    return round(sum(values) / len(values), 2) if values else None
