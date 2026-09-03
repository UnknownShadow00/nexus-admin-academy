"""Thin, student-safe presentation layer for the first V2 curriculum UI."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.certification import (
    Certification,
    CertificationDomain,
    CertificationModule,
    CertificationObjective,
    CertificationVersion,
    InterviewPrompt,
    LearningResource,
    LearningResourceLink,
    LessonObjective,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
    StudentResourceActivity,
    question_objective_codes,
)
from app.models.grading import GRADE_JOB_GRADED, GRADE_JOB_NEEDS_REVIEW, PendingGrade
from app.models.quiz import Question, Quiz
from app.models.service_desk import ServiceDeskAssignment, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.v2_progress import (
    V2_ACTIVITY_EXPLAIN,
    V2_ACTIVITY_LESSON,
    V2_ACTIVITY_MODULE_QUIZ,
    V2_ACTIVITY_PRACTICAL,
    V2_ACTIVITY_QUICK_CHECK,
    V2_ACTIVITY_RESOURCE,
    V2_ACTIVITY_SERVICE_DESK,
    V2_STATUS_COMPLETED,
    V2_STATUS_FAILED,
    V2_STATUS_IN_PROGRESS,
    V2_STATUS_NEEDS_REVIEW,
    V2_STATUS_PASSED,
    V2ExplainSubmission,
    V2AssessmentAttempt,
    V2AssessmentAttemptQuestion,
    V2ModuleActivity,
)
from app.services.deterministic_grader import grade_short_answer
from app.services.grading_queue import SOURCE_INTERVIEW, SOURCE_SHORT_ANSWER, submit_for_grading
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.v2_assessment_selector import ConstraintSelectionError, select_constrained
from app.services.v2_progress_service import V2ProgressError, module_progress, record_activity

DONE = {V2_STATUS_COMPLETED, V2_STATUS_PASSED}


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _activity(db: Session, student_id: int, activity_type: str, ref_key: str):
    return db.query(V2ModuleActivity).filter_by(
        student_id=student_id, activity_type=activity_type, ref_key=ref_key
    ).one_or_none()


def _activity_view(row: V2ModuleActivity | None) -> dict:
    if row is None:
        return {"status": "not_started", "score": None, "passed": None, "detail": {}, "updated_at": None}
    return {
        "status": row.status,
        "score": row.score,
        "passed": row.passed,
        "detail": row.detail or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _module(db: Session, module_key: str) -> CertificationModule:
    row = db.query(CertificationModule).filter_by(module_key=module_key, active=True).one_or_none()
    if row is None:
        raise V2ProgressError("This module is not available.")
    return row


def _lessons(db: Session, module_id: int) -> list[LessonV2Meta]:
    return db.query(LessonV2Meta).filter(
        LessonV2Meta.certification_module_id == module_id,
        LessonV2Meta.status.in_(("ready", "published")),
    ).order_by(LessonV2Meta.content_path, LessonV2Meta.id).all()


def _resources(db: Session, lesson_id: int) -> list[tuple[LearningResourceLink, LearningResource]]:
    return db.query(LearningResourceLink, LearningResource).join(
        LearningResource, LearningResource.id == LearningResourceLink.resource_id
    ).filter(
        LearningResourceLink.lesson_v2_meta_id == lesson_id,
        LearningResource.active.is_(True),
    ).order_by(LearningResourceLink.display_order, LearningResource.id).all()


def _module_resources(
    db: Session, module_id: int
) -> list[tuple[LearningResourceLink, LearningResource]]:
    return db.query(LearningResourceLink, LearningResource).join(
        LearningResource, LearningResource.id == LearningResourceLink.resource_id
    ).filter(
        LearningResourceLink.certification_module_id == module_id,
        LearningResourceLink.lesson_v2_meta_id.is_(None),
        LearningResource.active.is_(True),
    ).order_by(LearningResourceLink.display_order, LearningResource.id).all()


def _resource_view(
    db: Session,
    student_id: int,
    link: LearningResourceLink,
    resource: LearningResource,
) -> dict:
    tracked = db.query(StudentResourceActivity).filter_by(
        student_id=student_id, resource_id=resource.id
    ).one_or_none()
    return {
        "key": resource.resource_key,
        "title": resource.title,
        "provider": resource.provider,
        "type": resource.resource_type,
        "duration": resource.duration,
        "url": _safe_url(resource.url),
        "required": bool(link.is_required),
        "opened_at": tracked.opened_at.isoformat() if tracked and tracked.opened_at else None,
        "completed": bool(tracked and tracked.completed),
        "completed_at": tracked.completed_at.isoformat() if tracked and tracked.completed_at else None,
    }


def _assessments(db: Session, module_id: int) -> list[ModuleAssessment]:
    return db.query(ModuleAssessment).filter_by(
        certification_module_id=module_id, active=True
    ).order_by(ModuleAssessment.display_order, ModuleAssessment.id).all()


def _certification_view(db: Session, module: CertificationModule) -> dict:
    version = db.get(CertificationVersion, module.certification_version_id)
    cert = db.get(Certification, version.certification_id)
    domain = db.get(CertificationDomain, module.certification_domain_id) if module.certification_domain_id else None
    return {
        "key": cert.cert_key,
        "name": cert.name,
        "provider": cert.provider,
        "version": {"key": version.version_key, "label": version.label, "exam_codes": version.exam_codes or []},
        "domain": {"key": domain.domain_key, "title": domain.title} if domain else None,
    }


def _lesson_view(db: Session, student_id: int, lesson: LessonV2Meta, assessments: list[ModuleAssessment], *, include_content=False) -> dict:
    objective_rows = db.query(CertificationObjective).join(
        LessonObjective, LessonObjective.objective_id == CertificationObjective.id
    ).filter(LessonObjective.lesson_v2_meta_id == lesson.id).order_by(CertificationObjective.display_order).all()
    resource_views = [
        _resource_view(db, student_id, link, resource)
        for link, resource in _resources(db, lesson.id)
    ]
    quick_check = next((a for a in assessments if a.lesson_v2_meta_id == lesson.id and a.assessment_role == V2_ACTIVITY_QUICK_CHECK), None)
    result = {
        "key": lesson.lesson_key,
        "title": lesson.title,
        "summary": lesson.summary,
        "importance": lesson.importance,
        "learning_relationship": lesson.learning_relationship,
        "estimated_minutes": lesson.estimated_minutes,
        "objectives": [{"code": row.objective_code, "text": row.objective_text} for row in objective_rows],
        "resources": resource_views,
        "progress": _activity_view(_activity(db, student_id, V2_ACTIVITY_LESSON, lesson.lesson_key)),
        "quick_check": ({
            "key": quick_check.assessment_key,
            "title": quick_check.title,
            "question_count": quick_check.displayed_count,
            "pass_percent": quick_check.pass_percent,
            "progress": _activity_view(_activity(db, student_id, V2_ACTIVITY_QUICK_CHECK, quick_check.assessment_key)),
        } if quick_check else None),
    }
    if include_content:
        result["content_markdown"] = lesson.content_body or ""
    return result


def _assessment_view(db: Session, student_id: int, assessment: ModuleAssessment) -> dict:
    engine_ref = (assessment.config or {}).get("engine_service_desk_ref")
    scenario = db.get(ServiceDeskScenario, assessment.service_desk_scenario_id) if assessment.service_desk_scenario_id else None
    return {
        "key": assessment.assessment_key,
        "role": assessment.assessment_role,
        "title": assessment.title,
        "question_count": assessment.displayed_count,
        "pass_percent": assessment.pass_percent,
        "available": bool(
            assessment.quiz_id or assessment.lab_template_id or assessment.service_desk_scenario_id
            or assessment.assessment_role == V2_ACTIVITY_EXPLAIN
        ),
        "quiz_id": assessment.quiz_id,
        "lab_id": assessment.lab_template_id,
        "service_desk": ({
            "stable_key": scenario.stable_key if scenario else engine_ref,
            "title": scenario.title if scenario else assessment.title,
            "launch_url": f"/service-desk/tickets/{(scenario.stable_key if scenario else engine_ref).upper()}" if (scenario or engine_ref) else None,
        } if assessment.assessment_role == V2_ACTIVITY_SERVICE_DESK else None),
        "progress": _activity_view(_activity(db, student_id, assessment.assessment_role, assessment.assessment_key)),
    }


def module_view(db: Session, student_id: int, module_key: str) -> dict:
    module = _module(db, module_key)
    assessments = _assessments(db, module.id)
    lessons = [_lesson_view(db, student_id, row, assessments) for row in _lessons(db, module.id)]
    prompt_rows = db.query(InterviewPrompt).filter_by(
        certification_module_id=module.id, active=True
    ).order_by(InterviewPrompt.id).all()
    prompts = [{
        "key": row.prompt_key,
        "prompt": row.prompt,
        "importance": row.importance,
        "progress": _activity_view(_activity(db, student_id, V2_ACTIVITY_EXPLAIN, row.prompt_key)),
    } for row in prompt_rows]
    assessment_views = [_assessment_view(db, student_id, row) for row in assessments]
    progress = module_progress(db, student_id, module_key)
    result = {
        "certification": _certification_view(db, module),
        "module": {
            "key": module.module_key,
            "title": module.title,
            "description": module.skill_promise,
            "importance": module.importance_hint,
        },
        "lessons": lessons,
        "module_resources": [
            _resource_view(db, student_id, link, resource)
            for link, resource in _module_resources(db, module.id)
        ],
        "assessments": assessment_views,
        "explain_prompts": prompts,
        "progress": progress,
    }
    result["continue"] = resolve_continue(result)
    return result


def entry_view(db: Session, student_id: int) -> dict:
    modules = db.query(CertificationModule).join(
        CertificationVersion, CertificationVersion.id == CertificationModule.certification_version_id
    ).filter(CertificationModule.active.is_(True)).order_by(
        CertificationVersion.id, CertificationModule.display_order, CertificationModule.id
    ).all()
    items = []
    for module in modules:
        if not _lessons(db, module.id):
            continue
        # Only surface modules with the complete Nexus learning formula. This
        # keeps old foundation fixtures/drafts out of the student entry page
        # without hardcoding a module key or lesson count.
        roles = {row.assessment_role for row in _assessments(db, module.id)}
        if not {"quick_check", "module_quiz", "practical", "explain"}.issubset(roles):
            continue
        view = module_view(db, student_id, module.module_key)
        items.append({
            "certification": view["certification"], "module": view["module"],
            "progress": view["progress"], "continue": view["continue"],
        })
    current = next((item for item in items if not item["progress"]["module_complete"]), None)
    return {"modules": items, "current": current or (items[-1] if items else None)}


def lesson_view(db: Session, student_id: int, module_key: str, lesson_key: str) -> dict:
    module = _module(db, module_key)
    lessons = _lessons(db, module.id)
    lesson = next((row for row in lessons if row.lesson_key == lesson_key), None)
    if lesson is None:
        raise V2ProgressError("This lesson is not available.")
    assessments = _assessments(db, module.id)
    index = lessons.index(lesson)
    return {
        "certification": _certification_view(db, module),
        "module": {"key": module.module_key, "title": module.title},
        "lesson": _lesson_view(db, student_id, lesson, assessments, include_content=True),
        "previous_lesson_key": lessons[index - 1].lesson_key if index else None,
        "next_lesson_key": lessons[index + 1].lesson_key if index + 1 < len(lessons) else None,
    }


def resolve_continue(view: dict) -> dict:
    module_key = view["module"]["key"]
    for lesson in view["lessons"]:
        base = f"/learning-v2/modules/{module_key}/lessons/{lesson['key']}"
        if any(r["required"] and not r["completed"] for r in lesson["resources"]):
            return {"kind": "resource", "label": "Continue learning", "title": lesson["title"], "route": base}
        if lesson["progress"]["status"] not in DONE:
            return {"kind": "lesson", "label": "Continue learning", "title": lesson["title"], "route": base}
        qc = lesson.get("quick_check")
        if qc and qc["progress"]["status"] not in DONE:
            return {"kind": "quick_check", "label": "Continue with Quick Check", "title": qc["title"], "route": f"/learning-v2/modules/{module_key}/assessments/{qc['key']}"}
    for role, label in ((V2_ACTIVITY_MODULE_QUIZ, "Take the Module Quiz"), (V2_ACTIVITY_PRACTICAL, "Start the practical"), (V2_ACTIVITY_SERVICE_DESK, "Troubleshoot a ticket")):
        item = next((a for a in view["assessments"] if a["role"] == role), None)
        if item and item["progress"]["status"] not in DONE:
            route = (
                f"/learning-v2/modules/{module_key}/service-desk/{item['key']}"
                if role == V2_ACTIVITY_SERVICE_DESK
                else f"/learning-v2/modules/{module_key}/practical/{item['key']}"
                if role == V2_ACTIVITY_PRACTICAL
                else f"/learning-v2/modules/{module_key}/assessments/{item['key']}"
            )
            return {"kind": role, "label": label, "title": item["title"], "route": route, "available": item["available"]}
    for prompt in view["explain_prompts"]:
        if prompt["progress"]["status"] not in DONE:
            return {"kind": "explain", "label": "Explain what you know", "title": "Explain", "route": f"/learning-v2/modules/{module_key}/explain/{prompt['key']}"}
    return {"kind": "complete", "label": "Review module", "title": "Module complete", "route": f"/learning-v2/modules/{module_key}"}


def _student_visible_knowledge_assessment(
    db: Session, module_key: str, assessment_key: str,
) -> tuple[CertificationModule, ModuleAssessment]:
    module = _module(db, module_key)
    assessment = (
        db.query(ModuleAssessment)
        .join(Quiz, Quiz.id == ModuleAssessment.quiz_id)
        .filter(
            ModuleAssessment.certification_module_id == module.id,
            ModuleAssessment.assessment_key == assessment_key,
            ModuleAssessment.active.is_(True),
            *student_visible_quiz_filters(),
        )
        .one_or_none()
    )
    if assessment is None or assessment.assessment_role not in {V2_ACTIVITY_QUICK_CHECK, V2_ACTIVITY_MODULE_QUIZ} or not assessment.quiz_id:
        raise V2ProgressError("This knowledge check is not available.")
    return module, assessment


def _select_assessment_questions(
    db: Session, module_key: str, assessment_key: str
) -> tuple[CertificationModule, ModuleAssessment, list[tuple[Question, QuestionV2Meta]]]:
    module, assessment = _student_visible_knowledge_assessment(
        db, module_key, assessment_key,
    )
    rows = db.query(Question, QuestionV2Meta).join(
        QuestionV2Meta, QuestionV2Meta.question_id == Question.id
    ).filter(
        Question.quiz_id == assessment.quiz_id,
        Question.flagged_for_review.is_(False),
    ).order_by(Question.id).all()
    config = assessment.config or {}
    objective_codes = set(config.get("objective_codes") or [])
    if objective_codes:
        rows = [
            (q, meta)
            for q, meta in rows
            if objective_codes.intersection(question_objective_codes(meta))
        ]
    rows = [(q, meta) for q, meta in rows if (meta.question_type or "single") != "free_response"]
    tags_any = set(config.get("tags_any") or [])
    if tags_any:
        rows = [pair for pair in rows if tags_any.intersection(pair[0].tags or [])]

    limit = assessment.displayed_count or len(rows)
    blueprint = config.get("question_blueprint") or []
    categories = config.get("category_requirements") or []
    if categories:
        excluded_ids = {str(value) for value in config.get("exclude_question_ids") or []}
        def tagged_value(tags: list[str], prefix: str) -> str:
            return next(
                (str(tag).removeprefix(prefix) for tag in tags if str(tag).startswith(prefix)),
                "",
            )

        candidates = [
            {
                "id": str(question.id),
                "objective_codes": question_objective_codes(meta),
                "tags": list(question.tags or []),
                "question_type": meta.question_type or ("multi" if question.is_multi_select else "single"),
                "question_style": tagged_value(list(question.tags or []), "question_style:"),
                "category": tagged_value(list(question.tags or []), "category:"),
                "pair": (question, meta),
            }
            for question, meta in rows
        ]
        try:
            constrained = select_constrained(
                candidates,
                blueprint,
                categories,
                excluded_ids=excluded_ids,
                selection_requirements=config.get("selection_requirements") or {},
            )
        except ConstraintSelectionError as exc:
            raise V2ProgressError(f"This Module Quiz blueprint is invalid: {exc}") from exc
        selected = [row["pair"] for row in constrained]
        if len(selected) != limit:
            raise V2ProgressError(
                "This Module Quiz blueprint total does not match displayed_count."
            )
    else:
        # Keep the original selection path for all existing simple blueprints.
        selected = []
        for group in blueprint:
            group_objectives = set(group.get("objective_codes") or [])
            group_tags = set(group.get("tags_any") or [])
            eligible = [
                pair for pair in rows
                if pair not in selected
                and (
                    not group_objectives
                    or group_objectives.intersection(question_objective_codes(pair[1]))
                )
                and (not group_tags or group_tags.intersection(pair[0].tags or []))
            ]
            selected.extend(_balanced_question_take(eligible, min(int(group.get("count") or 0), limit - len(selected))))
            if len(selected) >= limit:
                break
        selected.extend(_balanced_question_take([pair for pair in rows if pair not in selected], limit - len(selected)))
    return module, assessment, selected


def _question_snapshot(question: Question, meta: QuestionV2Meta) -> dict:
    kind = meta.question_type or ("multi" if question.is_multi_select else "single")
    return {
            "id": question.id,
            "type": kind,
            "question_text": question.question_text,
            "is_multi_select": kind == "multi",
            "options": [{"key": letter, "text": getattr(question, f"option_{letter.lower()}")} for letter in "ABCDEFGH" if getattr(question, f"option_{letter.lower()}")],
            "correct_answers": question.all_correct_answers,
            "acceptable_answers": list(meta.acceptable_answers or []),
            "answer_match_mode": meta.answer_match_mode,
            "rubric_version": meta.rubric_version,
            "expected_concepts": list(meta.expected_concepts or []),
            "rubric": dict(meta.rubric or {}),
            "explanation": question.explanation or "",
        }


def _public_snapshot(snapshot: dict) -> dict:
    return {
        key: snapshot[key]
        for key in ("id", "type", "question_text", "is_multi_select", "options")
    }


def _attempt_payload(attempt: V2AssessmentAttempt, assessment: ModuleAssessment) -> dict:
    return {
        "module_key": attempt.module_key,
        "assessment": {"key": assessment.assessment_key, "role": assessment.assessment_role, "title": assessment.title, "pass_percent": assessment.pass_percent, "question_count": len(attempt.questions)},
        "attempt": {
            "id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "status": attempt.status,
            "grading_state": attempt.grading_state,
            "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        },
        "questions": [_public_snapshot(row.question_snapshot) for row in attempt.questions],
        "attempts": [],
    }


def assessment_questions(
    db: Session,
    student_id: int,
    module_key: str,
    assessment_key: str,
    *,
    explicit_start: bool = False,
) -> dict:
    module, assessment, selected = _select_assessment_questions(db, module_key, assessment_key)
    active = db.query(V2AssessmentAttempt).filter(
        V2AssessmentAttempt.student_id == student_id,
        V2AssessmentAttempt.assessment_id == assessment.id,
        V2AssessmentAttempt.status.in_((V2_STATUS_IN_PROGRESS, V2_STATUS_NEEDS_REVIEW)),
    ).order_by(V2AssessmentAttempt.attempt_number.desc()).first()
    if active is not None:
        if explicit_start and active.status == V2_STATUS_NEEDS_REVIEW:
            raise V2ProgressError("This attempt is still waiting for grading.")
        return _attempt_payload(active, assessment)

    attempt_number = (
        db.query(func.max(V2AssessmentAttempt.attempt_number))
        .filter_by(student_id=student_id, assessment_id=assessment.id)
        .scalar() or 0
    ) + 1
    attempt = V2AssessmentAttempt(
        student_id=student_id,
        assessment_id=assessment.id,
        module_key=module.module_key,
        assessment_key=assessment.assessment_key,
        attempt_number=attempt_number,
    )
    attempt.questions = [
        V2AssessmentAttemptQuestion(
            question_id=question.id,
            position=position,
            question_snapshot=_question_snapshot(question, meta),
        )
        for position, (question, meta) in enumerate(selected)
    ]
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        active = db.query(V2AssessmentAttempt).filter_by(
            student_id=student_id, assessment_id=assessment.id,
            attempt_number=attempt_number,
        ).one()
        return _attempt_payload(active, assessment)
    db.refresh(attempt)
    return _attempt_payload(attempt, assessment)


def _balanced_question_take(rows: list[tuple], limit: int) -> list[tuple]:
    """Take a deterministic mix of objective-filtered question types.

    Coverage is controlled by assessment YAML; this helper only prevents a
    blueprint group from returning all single-choice rows before a short-answer
    or multi-select row that belongs to the same concept group.
    """
    buckets = {kind: [] for kind in ("single", "multi", "short_answer")}
    for pair in rows:
        kind = pair[1].question_type or ("multi" if pair[0].is_multi_select else "single")
        buckets.setdefault(kind, []).append(pair)
    selected = []
    while len(selected) < limit and any(buckets.values()):
        for kind in ("single", "short_answer", "multi"):
            if buckets.get(kind) and len(selected) < limit:
                selected.append(buckets[kind].pop(0))
    return selected


def _attempt_result(attempt: V2AssessmentAttempt, assessment: ModuleAssessment) -> dict:
    results = []
    for row in attempt.questions:
        snapshot = row.question_snapshot
        results.append({
            "question_id": row.question_id,
            "question_text": snapshot["question_text"],
            "student_answer": row.submitted_answer or "",
            "is_correct": row.passed,
            "correct_answer": snapshot["correct_answers"] if snapshot["type"] != "short_answer" else None,
            "explanation": snapshot.get("explanation", ""),
            "grading_status": row.grading_status,
        })
    return {
        "attempt_id": attempt.id,
        "attempt_number": attempt.attempt_number,
        "score": attempt.score,
        "total": len(results),
        "passed": attempt.passed,
        "pass_percent": assessment.pass_percent,
        "grading_state": attempt.grading_state,
        "results": results,
    }


def finalize_assessment_attempt(db: Session, attempt: V2AssessmentAttempt, *, commit: bool = False) -> bool:
    """Finalize an attempt once every response has a resolved score."""
    for row in attempt.questions:
        if row.pending_grade_id:
            job = db.get(PendingGrade, row.pending_grade_id)
            if not job or job.resolved_passed is None or job.resolved_score is None:
                return False
            row.score = float(job.resolved_score)
            row.passed = job.resolved_passed is True
            row.grading_status = "graded"
        if row.score is None:
            return False
    earned = sum(float(row.score or 0) for row in attempt.questions)
    attempt.score = round(100 * earned / len(attempt.questions)) if attempt.questions else 0
    assessment = db.get(ModuleAssessment, attempt.assessment_id)
    attempt.passed = attempt.score >= assessment.pass_percent
    attempt.status = V2_STATUS_PASSED if attempt.passed else V2_STATUS_FAILED
    attempt.grading_state = "graded"
    record_activity(
        db, student_id=attempt.student_id, module_key=attempt.module_key,
        activity_type=assessment.assessment_role, ref_key=attempt.assessment_key,
        status=attempt.status, score=attempt.score, passed=attempt.passed,
        detail={"latest_attempt_id": attempt.id},
    )
    db.flush()
    if commit:
        db.commit()
    return True


def submit_assessment(db: Session, student_id: int, module_key: str, assessment_key: str, attempt_id: int, answers: dict[str, str]) -> dict:
    attempt = db.query(V2AssessmentAttempt).filter_by(
        id=attempt_id, student_id=student_id,
        module_key=module_key, assessment_key=assessment_key,
    ).with_for_update().one_or_none()
    if attempt is None:
        raise V2ProgressError("This assessment attempt is not available.")
    assessment = db.get(ModuleAssessment, attempt.assessment_id)
    if assessment is None:
        raise V2ProgressError("This assessment attempt is not available.")
    if attempt.status != V2_STATUS_IN_PROGRESS:
        return _attempt_result(attempt, assessment)

    pending_rows = []
    for row in attempt.questions:
        snapshot = row.question_snapshot
        answer = str(answers.get(str(row.question_id), "")).strip()
        kind = snapshot["type"]
        row.submitted_answer = answer
        if kind == "short_answer":
            det = grade_short_answer(
                answer, snapshot["acceptable_answers"],
                match_mode=snapshot["answer_match_mode"],
                rubric_version=snapshot["rubric_version"],
            )
            if det["status"] == "graded":
                row.score = float(det["score"])
                row.passed = det["passed"] is True
                row.grading_status = "graded"
            else:
                row.grading_status = "needs_review"
                pending_rows.append(row)
        else:
            submitted = sorted(x.strip().upper() for x in answer.split(",") if x.strip())
            expected = sorted(snapshot["correct_answers"])
            correct = bool(submitted) and submitted == expected
            row.score = 1.0 if correct else 0.0
            row.passed = correct
            row.grading_status = "graded"
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.grading_state = "pending" if pending_rows else "grading"
    attempt.status = V2_STATUS_NEEDS_REVIEW if pending_rows else V2_STATUS_IN_PROGRESS
    db.commit()  # Student answers survive a grading-provider failure.

    for row in pending_rows:
        snapshot = row.question_snapshot
        outcome = submit_for_grading(
            db, student_id=student_id, source_type=SOURCE_SHORT_ANSWER,
            submission_ref=f"v2-assessment-response:{row.id}",
            source_key=assessment.assessment_key,
            submitted_answer=row.submitted_answer or "", question_type=SOURCE_SHORT_ANSWER,
            question_text=snapshot["question_text"], acceptable_answers=snapshot["acceptable_answers"],
            expected_concepts=snapshot["expected_concepts"], rubric=snapshot["rubric"],
            rubric_version=snapshot["rubric_version"], match_mode=snapshot["answer_match_mode"],
            pass_threshold=1.0, commit=False,
        )
        row.pending_grade_id = outcome["pending_grade_id"]
    if pending_rows:
        record_activity(
            db, student_id=student_id, module_key=module_key,
            activity_type=assessment.assessment_role, ref_key=assessment_key,
            status=V2_STATUS_NEEDS_REVIEW, passed=None,
            detail={"latest_attempt_id": attempt.id},
        )
    else:
        finalize_assessment_attempt(db, attempt)
    db.commit()
    return _attempt_result(attempt, assessment)


def resource_activity(db: Session, student_id: int, module_key: str, resource_key: str, *, opened=False, completed=False) -> dict:
    module = _module(db, module_key)
    resource = db.query(LearningResource).filter_by(resource_key=resource_key, active=True).one_or_none()
    if resource is None:
        raise V2ProgressError("This resource is not available.")
    lesson_ids = [lesson.id for lesson in _lessons(db, module.id)]
    valid_link = db.query(LearningResourceLink).filter(
        LearningResourceLink.resource_id == resource.id,
        or_(
            LearningResourceLink.certification_module_id == module.id,
            LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids or [-1]),
        ),
    ).first()
    if not valid_link:
        raise V2ProgressError("This resource is not part of the module.")
    row = db.query(StudentResourceActivity).filter_by(student_id=student_id, resource_id=resource.id).one_or_none()
    if row is None:
        row = StudentResourceActivity(student_id=student_id, resource_id=resource.id)
        db.add(row)
    now = datetime.now(timezone.utc)
    if opened and row.opened_at is None:
        row.opened_at = now
    if completed:
        row.completed = True
        row.completed_at = row.completed_at or now
    record_activity(
        db, student_id=student_id, module_key=module_key, activity_type=V2_ACTIVITY_RESOURCE,
        ref_key=resource_key, status=V2_STATUS_COMPLETED if row.completed else V2_STATUS_IN_PROGRESS,
        detail={"opened_at": row.opened_at.isoformat() if row.opened_at else None, "completed_at": row.completed_at.isoformat() if row.completed_at else None},
    )
    db.commit()
    return {"resource_key": resource_key, "opened_at": row.opened_at, "completed": row.completed, "completed_at": row.completed_at}


def launch_service_desk(db: Session, student_id: int, module_key: str, assessment_key: str) -> dict:
    module = _module(db, module_key)
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_key=assessment_key,
        assessment_role=V2_ACTIVITY_SERVICE_DESK, active=True,
    ).one_or_none()
    if assessment is None:
        raise V2ProgressError("This troubleshooting activity is not available.")
    scenario = db.get(ServiceDeskScenario, assessment.service_desk_scenario_id) if assessment.service_desk_scenario_id else None
    if scenario is None:
        stable_key = (assessment.config or {}).get("engine_service_desk_ref")
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=stable_key, status="active").one_or_none() if stable_key else None
        if scenario:
            assessment.service_desk_scenario_id = scenario.id
    if scenario is None:
        raise V2ProgressError("This troubleshooting ticket is not available in this environment.")
    published = (
        db.query(ServiceDeskScenarioVersion)
        .filter_by(scenario_id=scenario.id, status="published")
        .order_by(ServiceDeskScenarioVersion.version_number.desc())
        .first()
    )
    curriculum = (published.definition_json or {}).get("curriculum", {}) if published else {}
    assignment_mode = "learning" if curriculum.get("mode") == "learning" else "simulation"
    assignment = db.query(ServiceDeskAssignment).filter_by(
        student_id=student_id, scenario_id=scenario.id, mode=assignment_mode
    ).one_or_none()
    if assignment is None:
        assignment = ServiceDeskAssignment(
            student_id=student_id, scenario_id=scenario.id, mode=assignment_mode,
            is_required=True, maximum_attempts=3,
            assigned_by=f"v2_curriculum:{module_key}:{assessment_key}",
        )
        db.add(assignment)
    record_activity(
        db, student_id=student_id, module_key=module_key,
        activity_type=V2_ACTIVITY_SERVICE_DESK, ref_key=assessment_key,
        status=V2_STATUS_IN_PROGRESS, detail={"scenario_id": scenario.id},
    )
    try:
        db.commit()
    except IntegrityError:
        # React development StrictMode can issue two launch requests together.
        # The unique assignment constraint is the final idempotency guard.
        db.rollback()
        assignment = db.query(ServiceDeskAssignment).filter_by(
            student_id=student_id, scenario_id=scenario.id, mode=assignment_mode
        ).one_or_none()
        if assignment is None:
            raise
        record_activity(
            db, student_id=student_id, module_key=module_key,
            activity_type=V2_ACTIVITY_SERVICE_DESK, ref_key=assessment_key,
            status=V2_STATUS_IN_PROGRESS, detail={"scenario_id": scenario.id},
            commit=True,
        )
    return {"launch_url": f"/service-desk/tickets/{scenario.stable_key.upper()}", "scenario_title": scenario.title}


def explain_view(db: Session, student_id: int, module_key: str, prompt_key: str) -> dict:
    module = _module(db, module_key)
    prompt = db.query(InterviewPrompt).filter_by(prompt_key=prompt_key, certification_module_id=module.id, active=True).one_or_none()
    if prompt is None:
        raise V2ProgressError("This Explain prompt is not available.")
    submissions = db.query(V2ExplainSubmission).filter_by(student_id=student_id, prompt_id=prompt.id).order_by(V2ExplainSubmission.attempt_number).all()
    history = []
    for row in submissions:
        ref = f"v2-explain:{row.id}"
        job = db.query(PendingGrade).filter_by(source_type=SOURCE_INTERVIEW, submission_ref=ref).one_or_none()
        if job and job.status == GRADE_JOB_GRADED:
            state, message, score, passed = "graded", "Your response has been graded.", job.resolved_score, job.resolved_passed
        elif job and job.status == GRADE_JOB_NEEDS_REVIEW:
            state, message, score, passed = "mentor_review", "Your response was saved and is waiting for a mentor to review it.", None, None
        elif job:
            state, message, score, passed = "pending", "Your response was saved and is waiting to be graded.", None, None
        else:
            act = _activity(db, student_id, V2_ACTIVITY_EXPLAIN, prompt_key)
            detail = (act.detail or {}) if act else {}
            state = detail.get("grading_state", "graded")
            score, passed = detail.get("score"), detail.get("passed")
            message = detail.get("message", "Your response has been saved.")
        history.append({"id": row.id, "attempt_number": row.attempt_number, "submitted_answer": row.submitted_answer, "submitted_at": row.submitted_at, "state": state, "message": message, "score": score, "passed": passed})
    return {"module_key": module_key, "prompt": {"key": prompt.prompt_key, "text": prompt.prompt, "importance": prompt.importance}, "submissions": history}


def submit_explain(db: Session, student_id: int, module_key: str, prompt_key: str, answer: str) -> dict:
    module = _module(db, module_key)
    prompt = db.query(InterviewPrompt).filter_by(prompt_key=prompt_key, certification_module_id=module.id, active=True).one_or_none()
    if prompt is None:
        raise V2ProgressError("This Explain prompt is not available.")
    attempt_number = (db.query(func.max(V2ExplainSubmission.attempt_number)).filter_by(student_id=student_id, prompt_id=prompt.id).scalar() or 0) + 1
    submission = V2ExplainSubmission(student_id=student_id, prompt_id=prompt.id, submitted_answer=answer.strip(), attempt_number=attempt_number)
    db.add(submission)
    db.commit()  # Required: original answer survives any grading failure.
    db.refresh(submission)
    outcome = submit_for_grading(
        db, student_id=student_id, source_type=SOURCE_INTERVIEW,
        submission_ref=f"v2-explain:{submission.id}", source_key=prompt.prompt_key,
        submitted_answer=submission.submitted_answer, question_type=SOURCE_INTERVIEW,
        question_text=prompt.prompt, expected_concepts=prompt.expected_concepts,
        rubric=prompt.rubric, rubric_version=prompt.rubric_version,
        # Explain prose is only a deterministic pass when every configured
        # concept is found. Partial concept matches are ambiguous wording, not
        # a confident failure, and therefore belong in mentor review.
        partial_credit=False, pass_threshold=0.7, commit=True,
    )
    if outcome["outcome"] == "graded":
        score = round(float(outcome["score"] or 0) * 100)
        passed = outcome["passed"] is True
        state, message = "graded", "Your response has been graded."
        status = V2_STATUS_PASSED if passed else V2_STATUS_FAILED
    else:
        score, passed = None, None
        state, message = "pending", "Your response was saved and is waiting to be graded."
        status = V2_STATUS_NEEDS_REVIEW
    record_activity(
        db, student_id=student_id, module_key=module_key, activity_type=V2_ACTIVITY_EXPLAIN,
        ref_key=prompt_key, status=status, score=score, passed=passed,
        detail={"submission_id": submission.id, "grading_state": state, "message": message, "score": score, "passed": passed}, commit=True,
    )
    return {"submission_id": submission.id, "attempt_number": attempt_number, "state": state, "message": message, "score": score, "passed": passed}
