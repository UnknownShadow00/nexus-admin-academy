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
from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
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
from app.services.grading_queue import (
    SOURCE_FREE_RESPONSE,
    SOURCE_INTERVIEW,
    SOURCE_SHORT_ANSWER,
    submit_for_grading,
)
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.service_desk_progression import (
    V2_CURRICULUM_MAXIMUM_ATTEMPTS,
    assignment_attempt_limit,
    assignment_attempts_used,
)
from app.services.v2_assessment_selector import ConstraintSelectionError, select_constrained
from app.services.v2_progress_service import V2ProgressError, module_progress, record_activity

DONE = {V2_STATUS_COMPLETED, V2_STATUS_PASSED}

#: A module reaches the student entry page only with the complete Nexus
#: learning formula. Content still missing one of these is invisible, which is
#: also what lets the foundation load tell "being authored" from "broken".
STUDENT_MODULE_ROLES = frozenset({"quick_check", "module_quiz", "practical", "explain"})


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
        "status": "completed" if tracked and tracked.completed else "in_progress" if tracked and tracked.opened_at else "not_started",
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
        "quick_check": (_assessment_view(db, student_id, quick_check) | {
            "question_count": quick_check.displayed_count,
        } if quick_check else None),
    }
    if include_content:
        result["content_markdown"] = lesson.content_body or ""
    return result


KNOWLEDGE_ROLES = {V2_ACTIVITY_QUICK_CHECK, V2_ACTIVITY_MODULE_QUIZ}


def quiz_is_student_visible(db: Session, quiz_id: int | None) -> bool:
    """Would a student actually be allowed to open this quiz?

    Delegates to the one authoritative visibility contract in
    ``quiz_visibility`` — draft, inactive, editorially unvalidated, and
    answer-key-unvalidated quizzes are all invisible. Availability and
    openability must never be decided by two different rules.
    """
    if not quiz_id:
        return False
    return db.query(Quiz.id).filter(
        Quiz.id == quiz_id, *student_visible_quiz_filters()
    ).first() is not None


def assessment_is_available(
    db: Session, assessment: ModuleAssessment, student_id: int | None = None
) -> bool:
    """Whether a student can actually open this assessment right now.

    A knowledge check needs a quiz that passes the student visibility
    contract, not merely a ``quiz_id`` that exists. Reporting availability
    from the presence of the foreign key alone produced an "available but
    unopenable" dead end: the module card said Continue, and opening it was
    then refused by the visibility filter.
    """
    if assessment.assessment_role in KNOWLEDGE_ROLES:
        return quiz_is_student_visible(db, assessment.quiz_id)
    if assessment.assessment_role == V2_ACTIVITY_EXPLAIN:
        return True
    if assessment.assessment_role == V2_ACTIVITY_SERVICE_DESK:
        return service_desk_scenario_is_playable(
            db, assessment
        ) and service_desk_has_attempt_capacity(db, assessment, student_id)
    if assessment.assessment_role == V2_ACTIVITY_PRACTICAL:
        from app.models.lab import LabTemplate

        if not assessment.lab_template_id:
            return False
        return db.query(LabTemplate.id).filter(
            LabTemplate.id == assessment.lab_template_id,
            LabTemplate.is_published.is_(True),
        ).first() is not None
    return bool(
        assessment.quiz_id or assessment.lab_template_id or assessment.service_desk_scenario_id
    )


def service_desk_scenario_is_playable(db: Session, assessment: ModuleAssessment) -> bool:
    """Return whether the assessment resolves to an active published scenario."""
    scenario = (
        db.get(ServiceDeskScenario, assessment.service_desk_scenario_id)
        if assessment.service_desk_scenario_id else None
    )
    if scenario is None:
        stable_key = (assessment.config or {}).get("engine_service_desk_ref")
        scenario = db.query(ServiceDeskScenario).filter_by(
            stable_key=stable_key, status="active"
        ).one_or_none() if stable_key else None
    if scenario is None or scenario.status != "active":
        return False
    return db.query(ServiceDeskScenarioVersion.id).filter_by(
        scenario_id=scenario.id, status="published"
    ).first() is not None


def service_desk_has_attempt_capacity(
    db: Session, assessment: ModuleAssessment, student_id: int | None
) -> bool:
    if student_id is None:
        return True
    scenario_id = assessment.service_desk_scenario_id
    if not scenario_id:
        return True
    passed = db.query(V2ModuleActivity.id).filter_by(
        student_id=student_id,
        activity_type=V2_ACTIVITY_SERVICE_DESK,
        ref_key=assessment.assessment_key,
        status=V2_STATUS_PASSED,
    ).first() is not None
    mode = "simulation" if passed else "learning"
    assignment = db.query(ServiceDeskAssignment).filter_by(
        student_id=student_id, scenario_id=scenario_id, mode=mode
    ).one_or_none()
    if assignment is None:
        return True
    module = db.get(CertificationModule, assessment.certification_module_id)
    context = (module.module_key, assessment.assessment_key) if module else None
    attempt_limit = assignment_attempt_limit(assignment, context)
    if attempt_limit is None:
        return True
    attempts = assignment_attempts_used(
        db,
        student_id=student_id,
        scenario_id=scenario_id,
        assignment_mode=mode,
        v2_context=context,
    )
    return attempts < attempt_limit


def _assessment_view(db: Session, student_id: int, assessment: ModuleAssessment) -> dict:
    engine_ref = (assessment.config or {}).get("engine_service_desk_ref")
    scenario = db.get(ServiceDeskScenario, assessment.service_desk_scenario_id) if assessment.service_desk_scenario_id else None
    available = assessment_is_available(db, assessment, student_id)
    unavailable = None
    if not available:
        activity_name = {
            V2_ACTIVITY_QUICK_CHECK: "Quick Check",
            V2_ACTIVITY_MODULE_QUIZ: "Module Quiz",
            V2_ACTIVITY_PRACTICAL: "Practical",
            V2_ACTIVITY_SERVICE_DESK: "Service Desk ticket",
        }.get(assessment.assessment_role, assessment.title)
        # Deliberately generic. A student must never be told *why* a bank is
        # blocked — "editorial approval missing" is mentor-facing detail.
        reason = (
            "This knowledge check is not available yet."
            if assessment.assessment_role in KNOWLEDGE_ROLES
            else "This ticket is not available yet."
            if assessment.assessment_role == V2_ACTIVITY_SERVICE_DESK
            else "This activity has not been prepared for students yet."
        )
        unavailable = {
            "status": "not_available",
            "reason": reason,
            "required_action": "Choose another available activity in this module.",
            "blocker_route": None,
            "activity_name": activity_name,
        }
    return {
        "key": assessment.assessment_key,
        "role": assessment.assessment_role,
        "title": assessment.title,
        "question_count": assessment.displayed_count,
        "pass_percent": assessment.pass_percent,
        "available": available,
        "unavailable": unavailable,
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
        if not STUDENT_MODULE_ROLES.issubset(roles):
            continue
        view = module_view(db, student_id, module.module_key)
        explain_feedback = next(({
            "title": prompt["prompt"],
            "status": prompt["progress"]["status"],
            "message": prompt["progress"]["detail"].get("message"),
            "route": f"/learning-v2/modules/{module.module_key}/explain/{prompt['key']}",
        } for prompt in reversed(view["explain_prompts"])
            if prompt["progress"]["status"] != "not_started"), None)
        items.append({
            "certification": view["certification"], "module": view["module"],
            "progress": view["progress"], "continue": view["continue"],
            "explain_feedback": explain_feedback,
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
    """Pick the single next thing the student can actually do.

    Availability is enforced here, not just displayed: an assessment whose
    quiz is not student-visible (draft, inactive, editorially unvalidated,
    answer key unvalidated) is skipped rather than pointed at. Routing a
    student into an activity the server will then refuse to open is a dead
    end, so a blocked activity is remembered and reported only if nothing
    else in the module is actionable.
    """
    module_key = view["module"]["key"]
    blocked: dict | None = None

    def _remember_blocked(item: dict) -> None:
        nonlocal blocked
        if blocked is None:
            blocked = item

    for lesson in view["lessons"]:
        base = f"/learning-v2/modules/{module_key}/lessons/{lesson['key']}"
        required_resource = next(
            (resource for resource in lesson["resources"] if resource["required"] and not resource["completed"]),
            None,
        )
        if required_resource:
            return {
                "kind": "resource", "label": "Continue learning", "title": required_resource["title"],
                "route": base, "status": required_resource["status"],
                "estimated_minutes": lesson["estimated_minutes"],
            }
        if lesson["progress"]["status"] not in DONE:
            return {
                "kind": "lesson", "label": "Continue learning", "title": lesson["title"],
                "route": base, "status": lesson["progress"]["status"],
                "estimated_minutes": lesson["estimated_minutes"],
            }
        qc = lesson.get("quick_check")
        if qc and qc["progress"]["status"] not in DONE:
            if qc.get("available", True):
                return {
                    "kind": "quick_check", "label": "Continue with Quick Check", "title": qc["title"],
                    "route": f"/learning-v2/modules/{module_key}/assessments/{qc['key']}",
                    "available": True,
                    "status": qc["progress"]["status"], "estimated_minutes": None,
                }
            _remember_blocked(qc)

    for role, label in ((V2_ACTIVITY_MODULE_QUIZ, "Take the Module Quiz"), (V2_ACTIVITY_PRACTICAL, "Start the practical"), (V2_ACTIVITY_SERVICE_DESK, "Troubleshoot a ticket")):
        item = next((a for a in view["assessments"] if a["role"] == role), None)
        if item and item["progress"]["status"] not in DONE:
            if not item.get("available", False):
                _remember_blocked(item)
                continue
            route = (
                f"/learning-v2/modules/{module_key}/service-desk/{item['key']}"
                if role == V2_ACTIVITY_SERVICE_DESK
                else f"/learning-v2/modules/{module_key}/practical/{item['key']}"
                if role == V2_ACTIVITY_PRACTICAL
                else f"/learning-v2/modules/{module_key}/assessments/{item['key']}"
            )
            return {
                "kind": role, "label": label, "title": item["title"], "route": route,
                "available": True, "status": item["progress"]["status"],
                "estimated_minutes": None,
            }
    for prompt in view["explain_prompts"]:
        if prompt["progress"]["status"] not in DONE:
            return {
                "kind": "explain", "label": "Explain what you know", "title": "Explain",
                "route": f"/learning-v2/modules/{module_key}/explain/{prompt['key']}",
                "status": prompt["progress"]["status"], "estimated_minutes": None,
            }
    if blocked is not None:
        # Everything left in this module is waiting on content review. Point
        # the student back at the module rather than at an activity that
        # would be refused, and reuse the same safe, non-diagnostic wording.
        return {
            "kind": "blocked", "label": "Nothing to do here yet",
            "title": blocked["title"],
            "route": f"/learning-v2/modules/{module_key}",
            "available": False,
            "unavailable": blocked.get("unavailable"),
            "status": blocked["progress"]["status"], "estimated_minutes": None,
        }
    return {
        "kind": "complete", "label": "Review module", "title": "Module complete",
        "route": f"/learning-v2/modules/{module_key}", "status": "completed",
        "estimated_minutes": None,
    }


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
    payload = {
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
    if attempt.status not in {V2_STATUS_IN_PROGRESS}:
        payload["result"] = _attempt_result(attempt, assessment)
    return payload


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

    latest = db.query(V2AssessmentAttempt).filter_by(
        student_id=student_id, assessment_id=assessment.id,
    ).order_by(V2AssessmentAttempt.attempt_number.desc()).first()
    latest_result = (
        _attempt_result(latest, assessment)
        if latest is not None and not explicit_start
        else None
    )

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
        payload = _attempt_payload(active, assessment)
        if latest_result is not None:
            payload["result"] = latest_result
        return payload
    db.refresh(attempt)
    payload = _attempt_payload(attempt, assessment)
    if latest_result is not None:
        payload["result"] = latest_result
    return payload


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
        if kind in {"short_answer", "free_response"}:
            source_type = (
                SOURCE_SHORT_ANSWER if kind == "short_answer" else SOURCE_FREE_RESPONSE
            )
            outcome = submit_for_grading(
                db, student_id=student_id, source_type=source_type,
                submission_ref=f"v2-assessment-response:{row.id}",
                source_key=assessment.assessment_key,
                submitted_answer=answer, question_type=source_type,
                question_text=snapshot["question_text"],
                acceptable_answers=snapshot.get("acceptable_answers") or [],
                expected_concepts=snapshot.get("expected_concepts") or [],
                rubric=snapshot.get("rubric") or {},
                rubric_version=snapshot.get("rubric_version"),
                match_mode=snapshot.get("answer_match_mode") or "normalized",
                pass_threshold=1.0 if kind == "short_answer" else 0.7,
                commit=False,
            )
            if outcome["outcome"] == "graded":
                row.score = float(outcome["score"] or 0)
                row.passed = outcome["passed"] is True
                row.grading_status = "graded"
            else:
                row.grading_status = "needs_review"
                row.pending_grade_id = outcome["pending_grade_id"]
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
    guided_completed = False
    if published:
        guided_completed = db.query(V2ModuleActivity).filter_by(
            student_id=student_id,
            activity_type=V2_ACTIVITY_SERVICE_DESK,
            ref_key=assessment_key,
            status=V2_STATUS_PASSED,
        ).first() is not None
    # A curriculum launch is the student's guided introduction until that
    # scenario has been completed once. Later launches retain the existing
    # assessment path and its server-authoritative grading.
    assignment_mode = "simulation" if guided_completed else "learning"
    assignment = db.query(ServiceDeskAssignment).filter_by(
        student_id=student_id, scenario_id=scenario.id, mode=assignment_mode
    ).one_or_none()
    if assignment is None:
        assignment = ServiceDeskAssignment(
            student_id=student_id, scenario_id=scenario.id, mode=assignment_mode,
            is_required=True, maximum_attempts=V2_CURRICULUM_MAXIMUM_ATTEMPTS,
            assigned_by=f"v2_curriculum:{module_key}:{assessment_key}",
        )
        db.add(assignment)
    else:
        # A V1/admin assignment can already own the unique scenario+mode row.
        # Reuse it without changing its provenance or retry policy, so V2
        # enrollment and revocation cannot silently alter the V1 experience.
        if (assignment.assigned_by or "").startswith("v2_curriculum:"):
            assignment.is_required = True
    db.flush()
    if not service_desk_has_attempt_capacity(db, assessment, student_id):
        raise V2ProgressError(
            "The retry limit for this troubleshooting activity has been reached. "
            "Ask your mentor to review the attempt."
        )
    if not guided_completed:
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
        if not guided_completed:
            record_activity(
                db, student_id=student_id, module_key=module_key,
                activity_type=V2_ACTIVITY_SERVICE_DESK, ref_key=assessment_key,
                status=V2_STATUS_IN_PROGRESS, detail={"scenario_id": scenario.id},
                commit=True,
            )
    return {
        "launch_url": (
            f"/service-desk/tickets/{scenario.stable_key.upper()}"
            f"?returnTo=/learning-v2/modules/{module_key}"
            f"&v2ModuleKey={module_key}&v2AssessmentKey={assessment_key}"
        ),
        "scenario_title": scenario.title,
        "mode": assignment_mode,
        "experience_mode": "assessment" if assignment_mode == "simulation" else "guided",
    }


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
    latest = db.query(V2ExplainSubmission).filter_by(
        student_id=student_id, prompt_id=prompt.id,
    ).order_by(V2ExplainSubmission.attempt_number.desc()).first()
    if latest:
        job = db.query(PendingGrade).filter_by(
            source_type=SOURCE_INTERVIEW,
            submission_ref=f"v2-explain:{latest.id}",
        ).one_or_none()
        if job and job.status not in {GRADE_JOB_GRADED}:
            return {
                "submission_id": latest.id,
                "attempt_number": latest.attempt_number,
                "state": "mentor_review" if job.status == GRADE_JOB_NEEDS_REVIEW else "pending",
                "message": "Your response was already saved and is still waiting for grading. You do not need to submit it again.",
                "score": None,
                "passed": None,
            }
    attempt_number = (db.query(func.max(V2ExplainSubmission.attempt_number)).filter_by(student_id=student_id, prompt_id=prompt.id).scalar() or 0) + 1
    submission = V2ExplainSubmission(student_id=student_id, prompt_id=prompt.id, submitted_answer=answer.strip(), attempt_number=attempt_number)
    db.add(submission)
    # Flush assigns the immutable submission reference while keeping the
    # submission, grading decision/job, and progress update in one database
    # transaction.  There is no provider call on this request path.
    db.flush()
    outcome = submit_for_grading(
        db, student_id=student_id, source_type=SOURCE_INTERVIEW,
        submission_ref=f"v2-explain:{submission.id}", source_key=prompt.prompt_key,
        submitted_answer=submission.submitted_answer, question_type=SOURCE_INTERVIEW,
        question_text=prompt.prompt, expected_concepts=prompt.expected_concepts,
        rubric=prompt.rubric, rubric_version=prompt.rubric_version,
        # Explain prose is only a deterministic pass when every configured
        # concept is found. Partial concept matches are ambiguous wording, not
        # a confident failure, and therefore belong in mentor review.
        partial_credit=False, pass_threshold=0.7, commit=False,
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
