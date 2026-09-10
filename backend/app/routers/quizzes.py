import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.quiz import QUIZ_PURPOSE_REMEDIATION, Quiz, QuizAttempt
from app.models.student import Student
from app.schemas.quiz import (
    PracticeAnswerRequest,
    PracticeCompleteRequest,
    QuizAttemptSaveRequest,
    QuizAttemptStartRequest,
    QuizSubmitRequest,
)
from app.services.assessment_access import require_quiz_access
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import (
    ensure_student_access,
    ensure_student_ownership,
    get_current_student,
)
from app.services.fsrs_service import create_cards_for_wrong_answers
from app.services.mastery_service import record_quiz_mastery
from app.services.quiz_scores import PASSING_PERCENTAGE, attempt_score, attempt_summary
from app.services.quiz_progression import (
    assigned_remediation_ids,
    triggered_remediation_ids,
)
from app.services.quiz_visibility import v1_student_visible_quiz_filters
from app.services.review_service import lesson_review
from app.services.xp_service import award_xp
from app.utils.responses import ok

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])
logger = logging.getLogger(__name__)

ATTEMPT_IN_PROGRESS = "in_progress"
ATTEMPT_SUBMITTED = "submitted"
PRACTICE_COMPLETE = "practice_complete"


def _grade_answer(question, raw_answer) -> tuple[object, bool]:
    """Grade a single question. Multi-select uses exact-set matching (all correct,
    no incorrect) so a partial or over-broad selection never earns credit."""
    correct_letters = question.all_correct_answers
    if question.is_multi_select:
        student_letters = sorted(
            letter.strip().upper()
            for letter in str(raw_answer or "").split(",")
            if letter.strip()
        )
        is_correct = bool(student_letters) and student_letters == sorted(
            letter.strip().upper() for letter in correct_letters
        )
        return raw_answer, is_correct
    is_correct = raw_answer in correct_letters
    return raw_answer, is_correct


def _avg_seconds_per_question(time_per_question: dict | None) -> float | None:
    if not time_per_question:
        return None
    values = [
        value for value in time_per_question.values() if isinstance(value, (int, float))
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _visible_quiz(db: Session, quiz_id: int) -> Quiz:
    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, *v1_student_visible_quiz_filters())
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


def _snapshot_questions(
    questions: list, *, shuffle_presentation: bool = True
) -> list[dict]:
    """Freeze a server-selected question and option presentation."""
    ordered = sorted(questions, key=lambda row: row.id)
    if shuffle_presentation:
        secrets.SystemRandom().shuffle(ordered)
    snapshot = []
    for position, question in enumerate(ordered):
        options = [
            {
                "source_letter": letter,
                "text": getattr(question, f"option_{letter.lower()}"),
            }
            for letter in "ABCDEFGH"
            if getattr(question, f"option_{letter.lower()}")
        ]
        if shuffle_presentation:
            secrets.SystemRandom().shuffle(options)
        for option_position, option in enumerate(options):
            option["letter"] = chr(65 + option_position)
        snapshot.append(
            {
                "id": question.id,
                "position": position,
                "question_text": question.question_text,
                "is_multi_select": question.is_multi_select,
                "options": options,
                "correct_source_answers": question.all_correct_answers,
                "explanation": question.explanation or "",
                "concepts": question.tags or [],
            }
        )
    return snapshot


def _public_snapshot(snapshot: list[dict] | None) -> list[dict]:
    return [
        {
            "id": row["id"],
            "position": row["position"],
            "question_text": row["question_text"],
            "is_multi_select": row.get("is_multi_select", False),
            "options": [
                {"letter": option["letter"], "text": option["text"]}
                for option in row.get("options", [])
            ],
        }
        for row in (snapshot or [])
    ]


def _attempt_view(attempt: QuizAttempt) -> dict:
    return {
        "id": attempt.id,
        "status": attempt.status,
        "answers": attempt.answers or {},
        "current_position": attempt.current_position or 0,
        "revision": attempt.revision or 0,
        "started_at": attempt.completed_at.isoformat()
        if attempt.completed_at
        else None,
        "submitted_at": attempt.submitted_at.isoformat()
        if attempt.submitted_at
        else None,
    }


def _result_for_learner(db: Session, quiz: Quiz, attempt: QuizAttempt) -> dict:
    score = attempt_score(attempt)
    passed = bool(score["passed"])
    disclose = passed
    review = lesson_review(db, quiz)
    rows = []
    for stored in attempt.results or []:
        row = dict(stored)
        row["review"] = review
        if not disclose:
            row.pop("correct_answer", None)
            row.pop("correct_answers", None)
            row.pop("explanation", None)
            row.pop("correct_answer_text", None)
            title = quiz.title.casefold()
            if "ticket" in title:
                row["key_idea"] = (
                    "Review how ticket intake, categorization, escalation, and troubleshooting updates map to the appropriate ticket fields."
                )
            elif "hardware" in title:
                row["key_idea"] = (
                    "Review each component's role, likely failure symptoms, and the evidence needed before replacement."
                )
            elif "incident" in title:
                row["key_idea"] = (
                    "Review the incident-response sequence and what evidence supports each next action."
                )
            else:
                row["key_idea"] = (
                    f"Review the core ideas in {quiz.title} before another graded attempt."
                )
            row["needs_review"] = row.get("concepts") or [
                quiz.title.removesuffix(" Quiz")
            ]
        rows.append(row)
    return {
        **score,
        "score": score["correct_count"],
        "total": score["question_count"],
        "passed": passed,
        "purpose": "assessment",
        "awards_credit": passed,
        "disclosure": "full_review" if disclose else "concepts_only",
        "results": rows,
        "review": review,
        "message": (
            "Assessment passed. Module requirement completed."
            if passed
            else "Assessment not passed yet. No module credit earned. Review the weak concepts before retrying."
        ),
    }


def _owned_attempt(
    db: Session, quiz_id: int, attempt_id: int, student_id: int
) -> QuizAttempt:
    attempt = (
        db.query(QuizAttempt)
        .filter_by(id=attempt_id, quiz_id=quiz_id, student_id=student_id)
        .with_for_update()
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    return attempt


@router.post("/{quiz_id}/attempts")
def start_or_resume_assessment(
    quiz_id: int,
    payload: QuizAttemptStartRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    ensure_student_ownership(current_student, payload.student_id)
    quiz = _visible_quiz(db, quiz_id)
    student = db.get(Student, payload.student_id)
    require_quiz_access(db, student, quiz)
    if not (quiz.is_required and quiz.show_in_weekly_checklist):
        raise HTTPException(
            status_code=409,
            detail="This quiz is a practice check, not a credit-bearing assessment",
        )
    attempt = (
        db.query(QuizAttempt)
        .filter_by(student_id=student.id, quiz_id=quiz.id, status=ATTEMPT_IN_PROGRESS)
        .order_by(QuizAttempt.id.desc())
        .first()
    )
    if not attempt:
        attempt = QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=None,
            score=0,
            xp_awarded=0,
            best_score=0,
            first_attempt_xp=0,
            status=ATTEMPT_IN_PROGRESS,
            question_snapshot=_snapshot_questions(quiz.questions),
            current_position=0,
            revision=0,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    return ok(
        {
            "purpose": "assessment",
            "credit_eligible": True,
            "awards_credit": False,
            "quiz": {
                "id": quiz.id,
                "title": quiz.title,
                "lesson_id": quiz.lesson_id,
                "question_count": len(attempt.question_snapshot or []),
            },
            "attempt": _attempt_view(attempt),
            "questions": _public_snapshot(attempt.question_snapshot),
            "bank_depth": {
                "bank_size": len(quiz.questions),
                "draw_size": len(attempt.question_snapshot or []),
                "materially_distinct_sets": 1,
                "safe_to_reveal_before_retry": False,
                "policy": "withhold_until_passed",
            },
        }
    )


@router.patch("/{quiz_id}/attempts/{attempt_id}")
def save_assessment_attempt(
    quiz_id: int,
    attempt_id: int,
    payload: QuizAttemptSaveRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    ensure_student_ownership(current_student, payload.student_id)
    attempt = _owned_attempt(db, quiz_id, attempt_id, payload.student_id)
    if attempt.status != ATTEMPT_IN_PROGRESS:
        raise HTTPException(
            status_code=409, detail="This assessment attempt has already been submitted"
        )
    if payload.revision != attempt.revision:
        raise HTTPException(
            status_code=409,
            detail="A newer version of this assessment attempt is already saved",
        )
    allowed = {str(row["id"]) for row in attempt.question_snapshot or []}
    if not set(payload.answers).issubset(allowed):
        raise HTTPException(
            status_code=422, detail="Answers do not match this assessment attempt"
        )
    max_position = max(len(attempt.question_snapshot or []) - 1, 0)
    attempt.answers = dict(payload.answers)
    attempt.current_position = min(payload.current_position, max_position)
    attempt.revision += 1
    db.commit()
    return ok(_attempt_view(attempt))


@router.post("/{quiz_id}/attempts/{attempt_id}/submit")
def submit_assessment_attempt(
    quiz_id: int,
    attempt_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    ensure_student_ownership(current_student, payload.student_id)
    quiz = _visible_quiz(db, quiz_id)
    student = db.get(Student, payload.student_id)
    require_quiz_access(db, student, quiz)
    attempt = _owned_attempt(db, quiz_id, attempt_id, student.id)
    if attempt.status == ATTEMPT_SUBMITTED:
        return ok(_result_for_learner(db, quiz, attempt))

    snapshot = attempt.question_snapshot or []
    allowed = {str(row["id"]) for row in snapshot}
    if not set(payload.answers).issubset(allowed):
        raise HTTPException(
            status_code=422, detail="Answers do not match this assessment attempt"
        )
    results = []
    wrong_answers = {}
    correct_count = 0
    for row in snapshot:
        raw = payload.answers.get(str(row["id"]), "")
        selected = [letter for letter in raw.split(",") if letter]
        option_by_letter = {option["letter"]: option for option in row["options"]}
        selected_sources = sorted(
            option_by_letter[letter]["source_letter"]
            for letter in selected
            if letter in option_by_letter
        )
        correct_sources = sorted(row["correct_source_answers"])
        is_correct = bool(selected_sources) and selected_sources == correct_sources
        if is_correct:
            correct_count += 1
        else:
            wrong_answers[row["id"]] = raw
        correct_display = sorted(
            option["letter"]
            for option in row["options"]
            if option["source_letter"] in correct_sources
        )
        results.append(
            {
                "question_id": row["id"],
                "passing_percentage": PASSING_PERCENTAGE,
                "question_number": row["position"] + 1,
                "question_text": row["question_text"],
                "student_answer": raw,
                "student_answer_text": "; ".join(
                    option_by_letter[letter]["text"]
                    for letter in selected
                    if letter in option_by_letter
                ),
                "correct_answer": correct_display[0] if correct_display else None,
                "correct_answers": correct_display,
                "correct_answer_text": "; ".join(
                    option["text"]
                    for option in row["options"]
                    if option["letter"] in correct_display
                ),
                "is_multi_select": row.get("is_multi_select", False),
                "is_correct": is_correct,
                "explanation": row.get("explanation", ""),
                "concepts": row.get("concepts", []),
                "options": {
                    option["letter"]: option["text"] for option in row["options"]
                },
            }
        )
    prior = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.student_id == student.id,
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.status == ATTEMPT_SUBMITTED,
            QuizAttempt.id != attempt.id,
        )
        .all()
    )
    prior_best = max((row.score or 0) for row in prior) if prior else 0
    is_first = not prior
    xp = round(correct_count * 100 / len(snapshot)) if is_first and snapshot else 0
    attempt.answers = dict(payload.answers)
    attempt.results = results
    attempt.score = correct_count
    attempt.xp_awarded = xp
    attempt.best_score = max(prior_best, correct_count)
    attempt.first_attempt_xp = xp if is_first else 0
    attempt.time_per_question = payload.time_per_question
    attempt.status = ATTEMPT_SUBMITTED
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.current_position = max(len(snapshot) - 1, 0)
    db.flush()
    score = attempt_score(attempt)
    if xp:
        award_xp(
            db,
            student_id=student.id,
            delta=xp,
            source_type="quiz",
            source_id=attempt.id,
            description=f"Assessment: {quiz.title} (Score: {correct_count}/{len(snapshot)})",
        )
    if quiz.is_required and quiz.show_in_weekly_checklist:
        record_quiz_mastery(
            db, student.id, quiz.domain_id, max(prior_best, correct_count)
        )
    log_activity(
        db,
        student.id,
        "quiz_passed" if score["passed"] else "quiz_failed",
        quiz.title,
        f"Attempt #{attempt.id}: {correct_count}/{len(snapshot)} ({score['percentage']}%)",
    )
    create_cards_for_wrong_answers(db, student.id, wrong_answers)
    db.commit()
    return ok(_result_for_learner(db, quiz, attempt))


@router.post("/{quiz_id}/practice/check")
def check_practice_answer(
    quiz_id: int,
    payload: PracticeAnswerRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    ensure_student_ownership(current_student, payload.student_id)
    quiz = _visible_quiz(db, quiz_id)
    student = db.get(Student, payload.student_id)
    require_quiz_access(db, student, quiz)
    if quiz.is_required and quiz.show_in_weekly_checklist:
        raise HTTPException(
            status_code=409,
            detail="Use a separate Practice Check; assessment items stay independent",
        )
    question = next(
        (row for row in quiz.questions if row.id == payload.question_id), None
    )
    if not question:
        raise HTTPException(status_code=404, detail="Practice question not found")
    student_answer, is_correct = _grade_answer(question, payload.answer)
    selected = [letter for letter in str(student_answer or "").split(",") if letter]
    options = {
        letter: getattr(question, f"option_{letter.lower()}") for letter in "ABCDEFGH"
    }
    return ok(
        {
            "purpose": "practice",
            "awards_credit": False,
            "is_correct": is_correct,
            "your_answer": "; ".join(
                options[letter] for letter in selected if options.get(letter)
            )
            or "No answer selected",
            "correct_answer": "; ".join(
                options[letter]
                for letter in question.all_correct_answers
                if options.get(letter)
            ),
            "key_idea": question.explanation
            or "Review the concept and compare each option to the symptom.",
            "review": lesson_review(db, quiz),
        }
    )


@router.post("/{quiz_id}/practice/complete")
def complete_practice(
    quiz_id: int,
    payload: PracticeCompleteRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    ensure_student_ownership(current_student, payload.student_id)
    quiz = _visible_quiz(db, quiz_id)
    student = db.get(Student, payload.student_id)
    require_quiz_access(db, student, quiz)
    if quiz.is_required and quiz.show_in_weekly_checklist:
        raise HTTPException(
            status_code=409,
            detail="Assessment activity cannot be recorded as practice",
        )
    question_ids = {question.id for question in quiz.questions}
    if set(payload.checked_question_ids) != question_ids:
        raise HTTPException(
            status_code=422,
            detail="Check each practice question before finishing practice",
        )
    existing = (
        db.query(QuizAttempt)
        .filter_by(
            student_id=student.id,
            quiz_id=quiz.id,
            status=PRACTICE_COMPLETE,
        )
        .first()
    )
    if not existing:
        db.add(
            QuizAttempt(
                student_id=student.id,
                quiz_id=quiz.id,
                answers={"checked_question_ids": sorted(payload.checked_question_ids)},
                results=[],
                score=0,
                xp_awarded=0,
                best_score=0,
                first_attempt_xp=0,
                status=PRACTICE_COMPLETE,
                submitted_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    return ok(
        {
            "purpose": "practice",
            "practice_completed": True,
            "awards_credit": False,
        }
    )


@router.get("")
def get_quizzes(
    week_number: int | None = None,
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    scoped_student_id = student_id or current_student.id
    ensure_student_access(current_student, scoped_student_id)
    remediation_ids = assigned_remediation_ids(
        db, scoped_student_id
    ) | triggered_remediation_ids(db, scoped_student_id)
    query = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(*v1_student_visible_quiz_filters())
    )
    if week_number is not None:
        query = query.filter(Quiz.week_number == week_number)
    quizzes = query.order_by(Quiz.created_at.desc()).all()
    quizzes = [
        quiz
        for quiz in quizzes
        if quiz.quiz_purpose != QUIZ_PURPOSE_REMEDIATION or quiz.id in remediation_ids
    ]

    attempts_by_quiz = {}
    attempt_counts_by_quiz = {}
    if scoped_student_id is not None:
        attempts = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.student_id == scoped_student_id,
                QuizAttempt.status == ATTEMPT_SUBMITTED,
            )
            .all()
        )
        for attempt in attempts:
            attempts_by_quiz.setdefault(attempt.quiz_id, []).append(attempt)
        attempt_counts = (
            db.query(QuizAttempt.quiz_id, func.count(QuizAttempt.id))
            .filter(
                QuizAttempt.student_id == scoped_student_id,
                QuizAttempt.status == ATTEMPT_SUBMITTED,
            )
            .group_by(QuizAttempt.quiz_id)
            .all()
        )
        attempt_counts_by_quiz = {quiz_id: count for quiz_id, count in attempt_counts}

    data = []
    for quiz in quizzes:
        rows = attempts_by_quiz.get(quiz.id, [])
        summary = attempt_summary(rows)
        attempt = (
            max(rows, key=lambda row: (row.completed_at, row.id)) if rows else None
        )
        attempt_count = (
            attempt_counts_by_quiz.get(quiz.id, 0) if scoped_student_id else 0
        )
        data.append(
            {
                "id": quiz.id,
                "title": quiz.title,
                "week_number": quiz.week_number,
                "domain_id": quiz.domain_id,
                "lesson_id": quiz.lesson_id,
                "question_count": len(quiz.questions),
                "video_count": len(
                    quiz.source_urls or ([quiz.source_url] if quiz.source_url else [])
                ),
                "status": "completed"
                if summary["earned_pass"]
                else "attempted"
                if attempt
                else "not_started",
                **summary,
                "best_score": attempt.best_score if attempt else None,
                "first_attempt_xp": attempt.first_attempt_xp if attempt else None,
                "attempt_count": attempt_count,
                "retake_available": attempt is not None,
                "quiz_purpose": quiz.quiz_purpose,
                "is_required": quiz.is_required,
                "show_in_weekly_checklist": quiz.show_in_weekly_checklist,
                "show_in_practice_library": quiz.show_in_practice_library,
                "editorial_status": quiz.editorial_status,
                "recommended_week": quiz.recommended_week,
                "quality_score": quiz.quality_score,
                "source_type": quiz.source_type,
                "answer_keys_validated": quiz.answer_keys_validated,
                "explanations_complete": quiz.explanations_complete,
            }
        )

    return ok(data, total=len(data), page=1, per_page=len(data) or 1)


@router.get("/{quiz_id}")
def get_quiz_details(
    quiz_id: int,
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    scoped_student_id = student_id or current_student.id
    ensure_student_access(current_student, scoped_student_id)
    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(
            Quiz.id == quiz_id,
            *v1_student_visible_quiz_filters(),
        )
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    require_quiz_access(db, db.get(Student, scoped_student_id), quiz)

    attempts = []
    if scoped_student_id:
        rows = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.student_id == scoped_student_id,
                QuizAttempt.status == ATTEMPT_SUBMITTED,
            )
            .order_by(QuizAttempt.completed_at.asc(), QuizAttempt.id.asc())
            .all()
        )
        attempts = [
            {
                "attempt_number": i + 1,
                **attempt_score(row),
                "score": row.score,
                "total": attempt_score(row)["question_count"],
                "xp_awarded": row.xp_awarded or 0,
                "is_first_attempt": i == 0,
                "created_at": row.completed_at.isoformat()
                if row.completed_at
                else None,
            }
            for i, row in enumerate(rows)
        ]

    return ok(
        {
            "id": quiz.id,
            "title": quiz.title,
            "week_number": quiz.week_number,
            "domain_id": quiz.domain_id,
            "lesson_id": quiz.lesson_id,
            "question_count": len(quiz.questions),
            "source_urls": quiz.source_urls
            or ([quiz.source_url] if quiz.source_url else []),
            "questions": [
                {
                    "id": question.id,
                    "question_text": question.question_text,
                    "option_a": question.option_a,
                    "option_b": question.option_b,
                    "option_c": question.option_c,
                    "option_d": question.option_d,
                    "option_e": question.option_e or "",
                    "option_f": question.option_f or "",
                    "option_g": question.option_g or "",
                    "option_h": question.option_h or "",
                    "is_multi_select": question.is_multi_select,
                }
                for question in quiz.questions
            ],
            "attempts": attempts,
            "quiz_purpose": quiz.quiz_purpose,
            "is_required": quiz.is_required,
            "show_in_weekly_checklist": quiz.show_in_weekly_checklist,
        }
    )


@router.post("/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    student_id = payload.student_id
    ensure_student_ownership(current_student, student_id)
    answers = payload.answers
    time_per_question = payload.time_per_question
    avg_seconds = _avg_seconds_per_question(time_per_question)

    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(
            Quiz.id == quiz_id,
            *v1_student_visible_quiz_filters(),
        )
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    require_quiz_access(db, student, quiz)
    if quiz.is_required and quiz.show_in_weekly_checklist:
        # Compatibility for older clients: even this one-shot route first
        # creates an owned immutable snapshot, then submits through the same
        # server-controlled assessment path. Current clients use /attempts so
        # they can resume before submission.
        attempt = QuizAttempt(
            student_id=student.id,
            quiz_id=quiz.id,
            answers={},
            results=None,
            score=0,
            xp_awarded=0,
            best_score=0,
            first_attempt_xp=0,
            status=ATTEMPT_IN_PROGRESS,
            question_snapshot=_snapshot_questions(
                quiz.questions, shuffle_presentation=False
            ),
            current_position=0,
            revision=0,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return submit_assessment_attempt(
            quiz_id=quiz.id,
            attempt_id=attempt.id,
            payload=payload,
            db=db,
            current_student=current_student,
        )
    mark_student_active(db, student_id)

    questions = sorted(quiz.questions, key=lambda q: q.id)
    total_questions = len(questions)
    if total_questions < 1:
        raise HTTPException(status_code=500, detail="Invalid quiz (no questions)")

    results = []
    correct_count = 0
    wrong_answers = {}

    for i, question in enumerate(questions, start=1):
        raw_answer = answers.get(str(question.id)) or answers.get(str(i))
        student_answer, is_correct = _grade_answer(question, raw_answer)
        if is_correct:
            correct_count += 1
        else:
            wrong_answers[question.id] = student_answer

        results.append(
            {
                "question_id": question.id,
                "passing_percentage": PASSING_PERCENTAGE,
                "question_number": i,
                "question_text": question.question_text,
                "student_answer": student_answer,
                "correct_answer": question.correct_answer,
                "correct_answers": question.all_correct_answers,
                "is_multi_select": question.is_multi_select,
                "is_correct": is_correct,
                "explanation": question.explanation or "",
                "options": {
                    "A": question.option_a,
                    "B": question.option_b,
                    "C": question.option_c,
                    "D": question.option_d,
                    "E": question.option_e or "",
                    "F": question.option_f or "",
                    "G": question.option_g or "",
                    "H": question.option_h or "",
                },
            }
        )

    score = correct_count
    passed = bool(
        total_questions and score * 100 >= total_questions * PASSING_PERCENTAGE
    )
    # TB-06: every attempt is a new row (migration c2d3e4f5a6b7 dropped uq_student_quiz).
    prior_attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == student_id, QuizAttempt.quiz_id == quiz_id)
        .all()
    )
    is_first_attempt = len(prior_attempts) == 0
    prior_best = max((a.score or 0) for a in prior_attempts) if prior_attempts else 0
    # XP policy unchanged: only the first attempt earns quiz XP.
    xp_awarded = round((score / total_questions) * 100) if is_first_attempt else 0

    attempt = QuizAttempt(
        student_id=student_id,
        quiz_id=quiz_id,
        answers=answers,
        results=results,
        score=score,
        xp_awarded=xp_awarded,
        best_score=max(prior_best, score),
        # live DB column is NOT NULL DEFAULT 0 (migration 0002) — 0, not None, on retakes
        first_attempt_xp=xp_awarded if is_first_attempt else 0,
        time_per_question=time_per_question,
        status=ATTEMPT_SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.flush()

    if xp_awarded > 0:
        award_xp(
            db,
            student_id=student_id,
            delta=xp_awarded,
            source_type="quiz",
            source_id=attempt.id,
            description=f"Quiz: {quiz.title} (Score: {score}/{total_questions})",
        )
    # Mastery uses best-known score across attempts (documented rule: mastery=best,
    # speed-flags evaluate every attempt individually).
    if quiz.is_required and quiz.show_in_weekly_checklist:
        record_quiz_mastery(db, student_id, quiz.domain_id, max(prior_best, score))
    log_activity(
        db,
        student_id,
        "quiz_practice_completed",
        quiz.title,
        f"Practice #{attempt.id}: {score}/{total_questions} ({attempt_score(attempt)['percentage']}%)",
    )
    create_cards_for_wrong_answers(db, student.id, wrong_answers)
    db.commit()

    return ok(
        {
            **attempt_score(attempt),
            "score": score,
            "total": total_questions,
            "xp_awarded": xp_awarded,
            "is_first_attempt": is_first_attempt,
            "passed": passed,
            "avg_seconds_per_question": round(avg_seconds, 1)
            if avg_seconds is not None
            else None,
            "is_speed_flagged": avg_seconds is not None and avg_seconds < 8,
            "purpose": "practice",
            "awards_credit": False,
            "result_label": "PRACTICE COMPLETE",
            "results": results,
            "message": f"Practice complete: {score}/{total_questions} correct. Learn from the feedback; this does not affect module credit.",
        }
    )


@router.get("/{quiz_id}/review/{student_id}")
def get_quiz_review(
    quiz_id: int,
    student_id: int,
    attempt_id: int | None = None,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Latest by submission time/id by default; explicit history remains scoped."""
    ensure_student_access(current_student, student_id)
    quiz = (
        db.query(Quiz)
        .options(selectinload(Quiz.questions))
        .filter(Quiz.id == quiz_id, *v1_student_visible_quiz_filters())
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    rows = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student_id)
        .filter(QuizAttempt.status == ATTEMPT_SUBMITTED)
        .order_by(QuizAttempt.completed_at.asc(), QuizAttempt.id.asc())
        .all()
    )
    attempt = (
        next((row for row in rows if row.id == attempt_id), None)
        if attempt_id is not None
        else (rows[-1] if rows else None)
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="No attempt found for this quiz")
    summary = attempt_summary(rows)
    score = attempt_score(attempt)
    avg_seconds = _avg_seconds_per_question(attempt.time_per_question)
    # Never regrade old answers against a changed bank. Missing snapshots are
    # explicitly disclosed, with only the recorded aggregate available.
    stored_results = attempt.results or []
    if quiz.is_required and quiz.show_in_weekly_checklist:
        results = _result_for_learner(db, quiz, attempt)["results"]
    else:
        results = stored_results
    questions = [
        {
            "id": row["question_id"],
            "question_text": row.get("question_text", ""),
            "correct_answer": row.get("correct_answer"),
            "correct_answers": row.get("correct_answers")
            or ([row.get("correct_answer")] if row.get("correct_answer") else []),
            "explanation": row.get("explanation", ""),
            **{
                f"option_{key.lower()}": value
                for key, value in row.get("options", {}).items()
            },
        }
        for row in results
    ]
    return ok(
        {
            **summary,
            **score,
            "quiz_id": quiz_id,
            "title": quiz.title,
            "attempt_number": rows.index(attempt) + 1,
            "review_selection": "latest" if attempt.id == rows[-1].id else "historical",
            "score": score["correct_count"],
            "total": score["question_count"],
            "xp_awarded": attempt.xp_awarded,
            "is_first_attempt": attempt.id == rows[0].id,
            "avg_seconds_per_question": round(avg_seconds, 1)
            if avg_seconds is not None
            else None,
            "is_speed_flagged": avg_seconds is not None and avg_seconds < 8,
            "results": results,
            "questions": questions,
            "review_available": bool(results),
            "purpose": "assessment"
            if quiz.is_required and quiz.show_in_weekly_checklist
            else "practice",
            "disclosure": "full_review"
            if (score["passed"] or not quiz.is_required)
            else "concepts_only",
        }
    )
