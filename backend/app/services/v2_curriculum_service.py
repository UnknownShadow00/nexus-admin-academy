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
from app.models.lab import LabRun
from app.models.quiz import Question
from app.models.service_desk import ServiceDeskAssignment, ServiceDeskAttempt, ServiceDeskScenario, ServiceDeskScenarioVersion
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
    V2ModuleActivity,
)
from app.services.deterministic_grader import grade_short_answer
from app.services.grading_queue import SOURCE_INTERVIEW, submit_for_grading
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
        LessonV2Meta.status.in_(("draft", "ready", "published")),
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


def sync_engine_progress(db: Session, student_id: int, module: CertificationModule) -> None:
    """Reflect authoritative resource/lab/Service Desk evidence into V2 roll-up."""
    assessments = _assessments(db, module.id)
    for assessment in assessments:
        if assessment.assessment_role == V2_ACTIVITY_PRACTICAL and assessment.lab_template_id:
            run = db.query(LabRun).filter_by(
                student_id=student_id, lab_template_id=assessment.lab_template_id
            ).order_by(LabRun.created_at.desc(), LabRun.id.desc()).first()
            if run:
                status = V2_STATUS_COMPLETED if run.status == "submitted" else V2_STATUS_IN_PROGRESS
                record_activity(
                    db, student_id=student_id, module_key=module.module_key,
                    activity_type=V2_ACTIVITY_PRACTICAL, ref_key=assessment.assessment_key,
                    status=status, score=run.final_score,
                    passed=(run.status == "submitted"), detail={"lab_run_id": run.id},
                )
        if assessment.assessment_role == V2_ACTIVITY_SERVICE_DESK and assessment.service_desk_scenario_id:
            attempt = db.query(ServiceDeskAttempt).join(
                ServiceDeskScenarioVersion,
                ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id,
            ).filter(
                ServiceDeskAttempt.student_id == student_id,
                ServiceDeskScenarioVersion.scenario_id == assessment.service_desk_scenario_id,
            ).order_by(ServiceDeskAttempt.started_at.desc(), ServiceDeskAttempt.id.desc()).first()
            if attempt:
                status = V2_STATUS_PASSED if attempt.passed else (
                    V2_STATUS_FAILED if attempt.status == "failed" else V2_STATUS_IN_PROGRESS
                )
                record_activity(
                    db, student_id=student_id, module_key=module.module_key,
                    activity_type=V2_ACTIVITY_SERVICE_DESK, ref_key=assessment.assessment_key,
                    status=status, score=attempt.score, passed=attempt.passed,
                    detail={"attempt_id": attempt.id},
                )
    db.flush()


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
    sync_engine_progress(db, student_id, module)
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


def assessment_questions(db: Session, student_id: int, module_key: str, assessment_key: str) -> dict:
    module = _module(db, module_key)
    assessment = db.query(ModuleAssessment).filter_by(
        certification_module_id=module.id, assessment_key=assessment_key, active=True
    ).one_or_none()
    if assessment is None or assessment.assessment_role not in {V2_ACTIVITY_QUICK_CHECK, V2_ACTIVITY_MODULE_QUIZ} or not assessment.quiz_id:
        raise V2ProgressError("This knowledge check is not available.")
    rows = db.query(Question, QuestionV2Meta).join(
        QuestionV2Meta, QuestionV2Meta.question_id == Question.id
    ).filter(Question.quiz_id == assessment.quiz_id).order_by(Question.id).all()
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
    questions = []
    for question, meta in selected:
        kind = meta.question_type or ("multi" if question.is_multi_select else "single")
        questions.append({
            "id": question.id,
            "type": kind,
            "question_text": question.question_text,
            "is_multi_select": kind == "multi",
            "options": [{"key": letter, "text": getattr(question, f"option_{letter.lower()}")} for letter in "ABCDEFGH" if getattr(question, f"option_{letter.lower()}")],
        })
    act = _activity(db, student_id, assessment.assessment_role, assessment.assessment_key)
    return {
        "module_key": module_key,
        "assessment": {"key": assessment.assessment_key, "role": assessment.assessment_role, "title": assessment.title, "pass_percent": assessment.pass_percent, "question_count": len(questions)},
        "questions": questions,
        "attempts": (_activity_view(act)["detail"].get("attempts") or []),
    }


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


def submit_assessment(db: Session, student_id: int, module_key: str, assessment_key: str, answers: dict[str, str]) -> dict:
    payload = assessment_questions(db, student_id, module_key, assessment_key)
    question_ids = [q["id"] for q in payload["questions"]]
    rows = {q.id: q for q in db.query(Question).filter(Question.id.in_(question_ids)).all()}
    meta = {m.question_id: m for m in db.query(QuestionV2Meta).filter(QuestionV2Meta.question_id.in_(question_ids)).all()}
    results = []
    earned = 0.0
    for public in payload["questions"]:
        question = rows[public["id"]]
        answer = str(answers.get(str(question.id), "")).strip()
        kind = public["type"]
        if kind == "short_answer":
            det = grade_short_answer(answer, meta[question.id].acceptable_answers, match_mode=meta[question.id].answer_match_mode, rubric_version=meta[question.id].rubric_version)
            correct = det["passed"] is True
            credit = det["score"] if det["status"] == "graded" else 0.0
            correct_answer = None
        else:
            submitted = sorted(x.strip().upper() for x in answer.split(",") if x.strip())
            expected = sorted(question.all_correct_answers)
            correct = bool(submitted) and submitted == expected
            credit = 1.0 if correct else 0.0
            correct_answer = expected
        earned += credit
        results.append({
            "question_id": question.id, "question_text": question.question_text,
            "student_answer": answer, "is_correct": correct,
            "correct_answer": correct_answer, "explanation": question.explanation or "",
        })
    total = len(results)
    score = round(100 * earned / total) if total else 0
    passed = score >= payload["assessment"]["pass_percent"]
    now = datetime.now(timezone.utc).isoformat()
    previous = payload["attempts"]
    attempt = {"attempt_number": len(previous) + 1, "score": score, "passed": passed, "submitted_at": now, "results": results}
    activity_type = payload["assessment"]["role"]
    record_activity(
        db, student_id=student_id, module_key=module_key, activity_type=activity_type,
        ref_key=assessment_key, status=V2_STATUS_PASSED if passed else V2_STATUS_FAILED,
        score=score, passed=passed, detail={"attempts": [*previous, attempt]},
        merge_detail=False, commit=True,
    )
    return {"score": score, "total": total, "passed": passed, "pass_percent": payload["assessment"]["pass_percent"], "results": results, "attempt_number": attempt["attempt_number"]}


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
