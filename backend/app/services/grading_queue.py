"""Submission-first grading orchestrator (Phase 1C).

Flow (see docs/NEXUS_V2_PHASE_1C_IMPLEMENTATION_NOTE.md):

    caller stages the student submission in its transaction
      -> submit_for_grading():
           deterministic grader runs first
           confident result            -> finished, no job row
           ambiguous (needs_review)    -> durable pending_grades row
      -> worker (run_pending_batch): claims due jobs, calls the AI provider
           accepted + confident        -> status=graded
           accepted + low confidence   -> status=needs_review
           retryable failure           -> status=failed_retryable, backoff
           retries exhausted           -> status=needs_review (mentor)
           terminal failure            -> status=failed_terminal / needs_review
      -> apply_mentor_override(): append-only override becomes the resolved grade

AI availability never affects whether the student's submission succeeded.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy.orm import Session

from app.models.grading import (
    AI_OUTCOME_ACCEPTED,
    AI_OUTCOME_ERROR_RETRYABLE,
    AI_OUTCOME_ERROR_TERMINAL,
    AI_OUTCOME_REJECTED_INVALID,
    GRADE_JOB_CLAIMABLE,
    GRADE_JOB_FAILED_RETRYABLE,
    GRADE_JOB_FAILED_TERMINAL,
    GRADE_JOB_GRADED,
    GRADE_JOB_NEEDS_REVIEW,
    GRADE_JOB_PENDING,
    GRADE_JOB_PROCESSING,
    GRADE_SOURCE_AI,
    GRADE_SOURCE_DETERMINISTIC,
    GRADE_SOURCE_MENTOR,
    AIGrade,
    MentorGradeOverride,
    PendingGrade,
)
from app.services.deterministic_grader import grade_free_response, grade_short_answer
from app.services.grading_config import GradingConfig, load_grading_config, next_retry_delay_seconds
from app.services.grading_provider import (
    OUTCOME_OK,
    OUTCOME_TERMINAL,
    GradingRequest,
    get_grading_provider,
)

# source_type helpers (extend as new graded surfaces are added)
SOURCE_SHORT_ANSWER = "module_assessment_short_answer"
SOURCE_FREE_RESPONSE = "free_response"
SOURCE_INTERVIEW = "interview_explain"

_INVALID_CATEGORIES = {"invalid_response", "invalid_json", "malformed_envelope"}


def _now(now: datetime | None = None) -> datetime:
    return now or datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Deterministic-first
# --------------------------------------------------------------------------- #

def run_deterministic(
    *,
    question_type: str,
    submitted_answer: str,
    acceptable_answers: list | None = None,
    expected_concepts: list | None = None,
    match_mode: str = "normalized",
    rubric_version: str | None = None,
    min_concepts_for_pass: int | None = None,
    partial_credit: bool = True,
) -> dict:
    if question_type in (SOURCE_FREE_RESPONSE, "free_response", SOURCE_INTERVIEW, "interview_explain"):
        return grade_free_response(
            submitted_answer,
            expected_concepts or [],
            rubric_version=rubric_version,
            min_concepts_for_pass=min_concepts_for_pass,
            partial_credit=partial_credit,
        )
    return grade_short_answer(
        submitted_answer,
        acceptable_answers or [],
        match_mode=match_mode,
        rubric_version=rubric_version,
    )


def submit_for_grading(
    db: Session,
    *,
    student_id: int,
    source_type: str,
    submission_ref: str,
    submitted_answer: str,
    question_type: str,
    source_key: str | None = None,
    question_text: str | None = None,
    acceptable_answers: list | None = None,
    expected_concepts: list | None = None,
    rubric: dict | None = None,
    rubric_version: str | None = None,
    match_mode: str = "normalized",
    min_concepts_for_pass: int | None = None,
    partial_credit: bool = True,
    pass_threshold: float | None = None,
    max_retries: int | None = None,
    commit: bool = True,
    now: datetime | None = None,
) -> dict:
    """Run deterministic grading; enqueue an AI job only if it is ambiguous.

    The caller must flush the student's submission before calling this so its
    stable reference exists. Callers that pass ``commit=False`` must commit the
    submission, grading decision/job, and progress update together. No grading
    provider is contacted by this function.
    """
    ts = _now(now)
    det = run_deterministic(
        question_type=question_type,
        submitted_answer=submitted_answer,
        acceptable_answers=acceptable_answers,
        expected_concepts=expected_concepts,
        match_mode=match_mode,
        rubric_version=rubric_version,
        min_concepts_for_pass=min_concepts_for_pass,
        partial_credit=partial_credit,
    )

    # Idempotency: one job per (source_type, submission_ref).
    existing = (
        db.query(PendingGrade)
        .filter(
            PendingGrade.source_type == source_type,
            PendingGrade.submission_ref == submission_ref,
        )
        .one_or_none()
    )

    if det["status"] == "graded":
        # Deterministic grader is confident. No AI, no job row. If a job was
        # somehow already created for this ref, leave its history intact.
        return {
            "outcome": "graded",
            "grade_source": GRADE_SOURCE_DETERMINISTIC,
            "score": det["score"],
            "passed": det["passed"],
            "pending_grade_id": existing.id if existing else None,
            "deterministic": det,
        }

    if existing is not None:
        return {
            "outcome": "pending",
            "grade_source": None,
            "pending_grade_id": existing.id,
            "status": existing.status,
            "deterministic": det,
        }

    cfg = load_grading_config()
    job = PendingGrade(
        student_id=student_id,
        source_type=source_type,
        source_key=source_key,
        submission_ref=submission_ref,
        question_text=question_text,
        submitted_answer=submitted_answer,
        rubric_json=rubric,
        rubric_version=rubric_version,
        expected_concepts_json=expected_concepts,
        deterministic_result_json=det,
        pass_threshold=pass_threshold,
        status=GRADE_JOB_PENDING,
        retry_count=0,
        max_retries=max_retries if max_retries is not None else cfg.max_retries,
        next_retry_at=ts,  # eligible immediately
    )
    db.add(job)
    db.flush()
    if commit:
        db.commit()
        db.refresh(job)
    return {
        "outcome": "pending",
        "grade_source": None,
        "pending_grade_id": job.id,
        "status": job.status,
        "deterministic": det,
    }


# --------------------------------------------------------------------------- #
# Worker
# --------------------------------------------------------------------------- #

def claim_due_jobs(
    db: Session, *, limit: int = 20, now: datetime | None = None,
    lease_seconds: int = 600,
) -> list[PendingGrade]:
    """Move up to ``limit`` due jobs to 'processing' and return them.

    SQLite (the active prod DB) serialises writers, so a plain UPDATE is a safe
    claim. On PostgreSQL add ``.with_for_update(skip_locked=True)`` to the
    SELECT for multi-worker safety (documented in the Phase 1C note)."""
    ts = _now(now)
    rows = (
        db.query(PendingGrade)
        .filter(
            (
                PendingGrade.status.in_(GRADE_JOB_CLAIMABLE)
                | (
                    (PendingGrade.status == GRADE_JOB_PROCESSING)
                    & (
                        PendingGrade.claimed_at.is_(None)
                        | (PendingGrade.claimed_at <= ts - timedelta(seconds=lease_seconds))
                    )
                )
            ),
            (PendingGrade.next_retry_at.is_(None)) | (PendingGrade.next_retry_at <= ts),
        )
        .order_by(PendingGrade.next_retry_at.is_(None).desc(), PendingGrade.next_retry_at.asc())
        .limit(limit)
        .all()
    )
    for row in rows:
        row.status = GRADE_JOB_PROCESSING
        row.claimed_at = ts
        row.claim_token = str(uuid.uuid4())
    db.commit()
    return rows


def _ai_outcome_for(result) -> str:
    if result.outcome == OUTCOME_OK:
        return AI_OUTCOME_ACCEPTED
    if result.outcome == OUTCOME_TERMINAL:
        return AI_OUTCOME_ERROR_TERMINAL
    if result.error_category in _INVALID_CATEGORIES:
        return AI_OUTCOME_REJECTED_INVALID
    return AI_OUTCOME_ERROR_RETRYABLE


def process_pending_grade(
    db: Session,
    job: PendingGrade,
    *,
    provider=None,
    cfg: GradingConfig | None = None,
    now: datetime | None = None,
    commit: bool = True,
    expected_claim_token: str | None = None,
) -> AIGrade | None:
    """One AI grading attempt for one job. Appends an ai_grades row, transitions
    the job, and never raises on provider failure."""
    if job.status in (GRADE_JOB_GRADED, GRADE_JOB_FAILED_TERMINAL):
        return None
    cfg = cfg or load_grading_config()
    provider = provider or get_grading_provider(cfg)
    ts = _now(now)

    request = GradingRequest(
        question_text=job.question_text or "",
        student_answer=job.submitted_answer or "",
        expected_concepts=job.expected_concepts_json,
        rubric=job.rubric_json,
        rubric_version=job.rubric_version,
        pass_threshold=job.pass_threshold,
        deterministic_findings=job.deterministic_result_json,
    )
    result = provider.grade(request)

    if expected_claim_token is not None:
        db.refresh(job)
        if job.status != GRADE_JOB_PROCESSING or job.claim_token != expected_claim_token:
            return None

    attempt_number = len(job.ai_grades) + 1
    ai_row = AIGrade(
        pending_grade_id=job.id,
        attempt_number=attempt_number,
        provider=result.provider,
        model=result.model,
        endpoint_label=result.endpoint_label,
        rubric_version=job.rubric_version,
        prompt_version=result.prompt_version,
        schema_version=result.schema_version,
        outcome=_ai_outcome_for(result),
        latency_ms=result.latency_ms,
        error_category=result.error_category,
        error_message=(result.error_message or None),
        raw_response_json=result.raw_json,
    )
    if result.parsed is not None:
        p = result.parsed
        ai_row.score = p.score
        ai_row.passed = p.passed
        ai_row.confidence = p.confidence
        ai_row.matched_concepts_json = p.matched_concepts
        ai_row.missing_concepts_json = p.missing_concepts
        ai_row.feedback = p.feedback
        ai_row.review_recommended = p.review_recommended
    # Append to the loaded collection (not just db.add) so resolve_pending below
    # sees this attempt without a round-trip.
    job.ai_grades.append(ai_row)

    job.retry_count += 1
    job.last_attempt_at = ts

    if result.outcome == OUTCOME_OK:
        p = result.parsed
        low_confidence = p.confidence < cfg.confidence_threshold
        review_needed = bool(p.review_recommended or low_confidence or p.passed is None)
        job.status = GRADE_JOB_NEEDS_REVIEW if review_needed else GRADE_JOB_GRADED
        job.graded_at = ts
        job.next_retry_at = None
        job.last_error_category = None
        job.last_error_message = None
    elif result.outcome == OUTCOME_TERMINAL:
        job.last_error_category = result.error_category
        job.last_error_message = result.error_message
        job.next_retry_at = None
        # 'disabled' is a normal operating mode -> hand to mentor.
        job.status = (
            GRADE_JOB_NEEDS_REVIEW
            if result.error_category == "disabled"
            else GRADE_JOB_FAILED_TERMINAL
        )
    else:  # retryable
        job.last_error_category = result.error_category
        job.last_error_message = result.error_message
        if job.retry_count >= job.max_retries:
            job.status = GRADE_JOB_NEEDS_REVIEW  # give up on AI, keep the work
            job.next_retry_at = None
        else:
            job.status = GRADE_JOB_FAILED_RETRYABLE
            delay = next_retry_delay_seconds(job.retry_count, cfg)
            job.next_retry_at = ts + timedelta(seconds=delay)

    db.flush()
    resolve_pending(db, job)
    job.claimed_at = None
    job.claim_token = None
    if commit:
        db.commit()
    return ai_row


def run_pending_batch(
    db: Session, *, limit: int = 20, provider=None, cfg: GradingConfig | None = None,
    now: datetime | None = None,
) -> dict:
    """Claim and process one batch of due jobs. Safe to run repeatedly (cron
    / systemd timer / admin 'run now'). Returns counts by resulting status."""
    cfg = cfg or load_grading_config()
    provider = provider or get_grading_provider(cfg)
    jobs = claim_due_jobs(db, limit=limit, now=now)
    counts: dict[str, int] = {"claimed": len(jobs)}
    for job in jobs:
        token = job.claim_token
        process_pending_grade(
            db, job, provider=provider, cfg=cfg, now=now,
            expected_claim_token=token,
        )
        counts[job.status] = counts.get(job.status, 0) + 1
    return counts


# --------------------------------------------------------------------------- #
# Resolution + mentor override
# --------------------------------------------------------------------------- #

def _latest_accepted_ai(job: PendingGrade) -> AIGrade | None:
    accepted = [g for g in job.ai_grades if g.outcome == AI_OUTCOME_ACCEPTED]
    return accepted[-1] if accepted else None


def resolve_pending(db: Session, job: PendingGrade, *, commit: bool = False) -> PendingGrade:
    """Recompute the effective grade: mentor override > latest accepted AI
    grade > deterministic result. Never rewrites history."""
    override = job.overrides[-1] if job.overrides else None
    if override is not None:
        job.resolved_grade_source = GRADE_SOURCE_MENTOR
        job.resolved_score = override.override_score
        job.resolved_passed = override.override_passed
        if job.status in (GRADE_JOB_NEEDS_REVIEW, GRADE_JOB_FAILED_TERMINAL, GRADE_JOB_FAILED_RETRYABLE):
            job.status = GRADE_JOB_GRADED
            job.graded_at = job.graded_at or _now()
    else:
        ai = _latest_accepted_ai(job)
        if ai is not None:
            job.resolved_grade_source = GRADE_SOURCE_AI
            job.resolved_score = ai.score
            job.resolved_passed = ai.passed
        elif job.deterministic_result_json and job.deterministic_result_json.get("status") == "graded":
            job.resolved_grade_source = GRADE_SOURCE_DETERMINISTIC
            job.resolved_score = job.deterministic_result_json.get("score")
            job.resolved_passed = job.deterministic_result_json.get("passed")
    db.flush()
    from app.services.v2_grading_reconciliation import reconcile_resolved_grade

    reconcile_resolved_grade(db, job)
    if commit:
        db.commit()
    return job


def apply_mentor_override(
    db: Session,
    job: PendingGrade,
    *,
    reason: str,
    override_score: float | None = None,
    override_passed: bool | None = None,
    mentor_label: str = "mentor",
    commit: bool = True,
    now: datetime | None = None,
) -> MentorGradeOverride:
    """Append a mentor override. The prior override (if any) is preserved and
    referenced via supersedes_id. The student's submission is never touched."""
    if not (reason or "").strip():
        raise ValueError("A mentor override requires a reason.")
    if override_score is None or override_passed is None:
        raise ValueError("A mentor override requires both score and pass result.")
    prior = job.overrides[-1] if job.overrides else None
    override = MentorGradeOverride(
        pending_grade_id=job.id,
        supersedes_id=prior.id if prior else None,
        mentor_label=(mentor_label or "mentor")[:120],
        override_score=override_score,
        override_passed=override_passed,
        reason=reason.strip(),
    )
    job.overrides.append(override)
    db.flush()
    job.status = GRADE_JOB_GRADED
    job.graded_at = _now(now)
    resolve_pending(db, job)
    if commit:
        db.commit()
    return override


# --------------------------------------------------------------------------- #
# Read models for a future mentor UI
# --------------------------------------------------------------------------- #

def _job_priority(job: PendingGrade) -> int:
    """Lower = more urgent. 1 low-confidence AI grade / AI asked for review;
    2 retries exhausted; 3 repeated/terminal failure; 4 pending manual."""
    ai = _latest_accepted_ai(job)
    if ai is not None and (ai.review_recommended or (ai.confidence is not None and ai.confidence < load_grading_config().confidence_threshold)):
        return 1
    if job.status == GRADE_JOB_NEEDS_REVIEW and job.retry_count >= job.max_retries:
        return 2
    if job.status in (GRADE_JOB_FAILED_RETRYABLE, GRADE_JOB_FAILED_TERMINAL):
        return 3
    return 4


def mentor_queue(db: Session, *, limit: int = 50, offset: int = 0) -> list[dict]:
    jobs = (
        db.query(PendingGrade)
        .filter(PendingGrade.status.in_((
            GRADE_JOB_PENDING,
            GRADE_JOB_NEEDS_REVIEW,
            GRADE_JOB_FAILED_RETRYABLE,
            GRADE_JOB_FAILED_TERMINAL,
        )))
        .order_by(PendingGrade.updated_at.asc())
        .all()
    )
    ranked = sorted(jobs, key=lambda j: (_job_priority(j), j.created_at))
    return [_job_summary(j) for j in ranked[offset : offset + limit]]


def _job_summary(job: PendingGrade) -> dict:
    ai = _latest_accepted_ai(job)
    return {
        "pending_grade_id": job.id,
        "student_id": job.student_id,
        "source_type": job.source_type,
        "source_key": job.source_key,
        "submission_ref": job.submission_ref,
        "status": job.status,
        "priority": _job_priority(job),
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "last_error_category": job.last_error_category,
        "rubric_version": job.rubric_version,
        "resolved_grade_source": job.resolved_grade_source,
        "resolved_score": job.resolved_score,
        "resolved_passed": job.resolved_passed,
        "latest_ai_confidence": ai.confidence if ai else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def grading_history(db: Session, job: PendingGrade) -> dict:
    """Full audit timeline for one submission — deterministic finding, every AI
    attempt (timeouts and rejects included), every mentor override, resolved."""
    return {
        "pending_grade_id": job.id,
        "student_id": job.student_id,
        "source_type": job.source_type,
        "submission_ref": job.submission_ref,
        "question_text": job.question_text,
        "submitted_answer": job.submitted_answer,
        "status": job.status,
        "rubric_version": job.rubric_version,
        "deterministic": job.deterministic_result_json,
        "ai_attempts": [
            {
                "attempt_number": g.attempt_number,
                "outcome": g.outcome,
                "provider": g.provider,
                "model": g.model,
                "endpoint_label": g.endpoint_label,
                "rubric_version": g.rubric_version,
                "prompt_version": g.prompt_version,
                "schema_version": g.schema_version,
                "score": g.score,
                "passed": g.passed,
                "confidence": g.confidence,
                "matched_concepts": g.matched_concepts_json,
                "missing_concepts": g.missing_concepts_json,
                "feedback": g.feedback,
                "review_recommended": g.review_recommended,
                "error_category": g.error_category,
                "error_message": g.error_message,
                "latency_ms": g.latency_ms,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in job.ai_grades
        ],
        "mentor_overrides": [
            {
                "id": o.id,
                "supersedes_id": o.supersedes_id,
                "mentor_label": o.mentor_label,
                "override_score": o.override_score,
                "override_passed": o.override_passed,
                "reason": o.reason,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in job.overrides
        ],
        "resolved": {
            "grade_source": job.resolved_grade_source,
            "score": job.resolved_score,
            "passed": job.resolved_passed,
            "graded_at": job.graded_at.isoformat() if job.graded_at else None,
        },
    }
