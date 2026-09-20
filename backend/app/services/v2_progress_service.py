"""Nexus V2 Phase 2A per-student module progress (development flow).

This records what a student has done in a V2 module and rolls it up for the
student's own view. It is deliberately NOT authoritative: no promotion gate,
mastery calculation, XP ledger, login streak, or legacy TrainingWeek reads
``v2_module_activity``. Nothing here migrates or touches existing students.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.certification import (
    CertificationModule,
    InterviewPrompt,
    LearningResource,
    LearningResourceLink,
    LessonV2Meta,
    ModuleAssessment,
)
from app.models.v2_progress import (
    V2_ACTIVITY_EXPLAIN,
    V2_ACTIVITY_MODULE_QUIZ,
    V2_ACTIVITY_PRACTICAL,
    V2_ACTIVITY_QUICK_CHECK,
    V2_ACTIVITY_RESOURCE,
    V2_ACTIVITY_SERVICE_DESK,
    V2_ACTIVITY_TYPES,
    V2_STATUS_COMPLETED,
    V2_STATUS_IN_PROGRESS,
    V2_STATUS_PASSED,
    V2_STATUS_VALUES,
    V2ModuleActivity,
)
from app.models.student import Student
from app.services.v2_access import student_has_v2_access

_DONE_STATUSES = {V2_STATUS_COMPLETED, V2_STATUS_PASSED}


class V2ProgressError(ValueError):
    """Bad input to the progress service (unknown activity type / status)."""


def record_activity(
    db: Session,
    *,
    student_id: int,
    module_key: str,
    activity_type: str,
    ref_key: str,
    status: str | None = None,
    score: int | None = None,
    passed: bool | None = None,
    detail: dict | None = None,
    merge_detail: bool = True,
    commit: bool = False,
) -> V2ModuleActivity:
    """Upsert one activity row for (student, activity_type, ref_key).

    Only the fields you pass are changed; ``detail`` is merged key-by-key
    unless ``merge_detail=False``. Returns the persisted row.
    """
    if activity_type not in V2_ACTIVITY_TYPES:
        raise V2ProgressError(
            f"activity_type '{activity_type}' is not one of {sorted(V2_ACTIVITY_TYPES)}"
        )
    if status is not None and status not in V2_STATUS_VALUES:
        raise V2ProgressError(
            f"status '{status}' is not one of {sorted(V2_STATUS_VALUES)}"
        )
    if not ref_key:
        raise V2ProgressError("ref_key is required")

    row = (
        db.query(V2ModuleActivity)
        .filter(
            V2ModuleActivity.student_id == student_id,
            V2ModuleActivity.activity_type == activity_type,
            V2ModuleActivity.ref_key == ref_key,
        )
        .one_or_none()
    )
    if row is None:
        try:
            # GET composition can run twice concurrently in a browser (for
            # example React StrictMode). Keep the unique-key race inside a
            # savepoint so the losing request can reuse the authoritative row
            # without rolling back unrelated caller work.
            with db.begin_nested():
                row = V2ModuleActivity(
                    student_id=student_id,
                    module_key=module_key,
                    activity_type=activity_type,
                    ref_key=ref_key,
                    status=status or V2_STATUS_IN_PROGRESS,
                )
                db.add(row)
                db.flush()
        except IntegrityError:
            row = (
                db.query(V2ModuleActivity)
                .filter(
                    V2ModuleActivity.student_id == student_id,
                    V2ModuleActivity.activity_type == activity_type,
                    V2ModuleActivity.ref_key == ref_key,
                )
                .one()
            )
    else:
        # module_key is stable for a ref, but tolerate a corrected value.
        row.module_key = module_key or row.module_key
        already_passed = row.passed is True and row.status in _DONE_STATUSES
        incoming_regresses = already_passed and (
            passed is False or (status is not None and status not in _DONE_STATUSES)
        )
        if incoming_regresses:
            prior_detail = dict(row.detail or {})
            prior_detail["latest_result"] = {
                "status": status,
                "score": score,
                "passed": passed,
            }
            row.detail = prior_detail
            status = None
            score = None
            passed = None
        elif status is not None:
            row.status = status

    if score is not None:
        row.score = int(score)
    if passed is not None:
        row.passed = bool(passed)
    if detail is not None:
        if merge_detail and isinstance(row.detail, dict):
            merged = dict(row.detail)
            merged.update(detail)
            row.detail = merged
        else:
            row.detail = dict(detail)

    db.flush()
    if commit:
        db.commit()
        db.refresh(row)
    return row


def _module_or_none(db: Session, module_key: str) -> CertificationModule | None:
    return (
        db.query(CertificationModule)
        .filter(CertificationModule.module_key == module_key)
        .one_or_none()
    )


def _module_resource_links(db: Session, module: CertificationModule, lesson_meta_ids: list[int]):
    return db.query(LearningResourceLink).filter(
        (LearningResourceLink.certification_module_id == module.id)
        | (LearningResourceLink.lesson_v2_meta_id.in_(lesson_meta_ids or [-1]))
    ).all()


def module_progress(db: Session, student_id: int, module_key: str) -> dict:
    """Roll up one student's activity for one V2 module (their own view)."""
    module = _module_or_none(db, module_key)
    if module is None:
        raise V2ProgressError(f"module '{module_key}' is not loaded")

    lesson_metas = (
        db.query(LessonV2Meta)
        .filter(
            LessonV2Meta.certification_module_id == module.id,
            LessonV2Meta.status.in_(("ready", "published")),
        )
        .order_by(LessonV2Meta.id)
        .all()
    )
    lesson_keys = [m.lesson_key for m in lesson_metas]
    lesson_meta_ids = [m.id for m in lesson_metas]

    # Only active assessments are requirements. A Service Desk assessment that
    # was deactivated for lacking a supported grading profile (P0 integrity
    # sprint) must not leave its module permanently incompletable.
    assessments = (
        db.query(ModuleAssessment)
        .filter(
            ModuleAssessment.certification_module_id == module.id,
            ModuleAssessment.active.is_(True),
        )
        .order_by(ModuleAssessment.display_order, ModuleAssessment.id)
        .all()
    )

    resource_links = _module_resource_links(db, module, lesson_meta_ids)
    resource_ids = {link.resource_id for link in resource_links}
    resource_required = {
        resource_id: any(link.is_required for link in resource_links if link.resource_id == resource_id)
        for resource_id in resource_ids
    }
    resource_key_by_id = {
        rid: key
        for rid, key in db.query(LearningResource.id, LearningResource.resource_key).filter(
            LearningResource.id.in_(resource_ids or [-1])
        )
    }

    acts = (
        db.query(V2ModuleActivity)
        .filter(
            V2ModuleActivity.student_id == student_id,
            V2ModuleActivity.module_key == module_key,
        )
        .all()
    )
    by_ref: dict[tuple[str, str], V2ModuleActivity] = {
        (a.activity_type, a.ref_key): a for a in acts
    }

    def _activity_view(a: V2ModuleActivity | None) -> dict | None:
        if a is None:
            return None
        return {
            "status": a.status,
            "score": a.score,
            "passed": a.passed,
            "detail": a.detail,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }

    lessons_view = [
        {"lesson_key": key, "activity": _activity_view(by_ref.get(("lesson", key)))}
        for key in lesson_keys
    ]
    lessons_done = sum(
        1
        for lv in lessons_view
        if lv["activity"] and lv["activity"]["status"] in _DONE_STATUSES
    )

    resources_view = [
        {
            "resource_key": key,
            "required": resource_required.get(rid, False),
            "activity": _activity_view(by_ref.get((V2_ACTIVITY_RESOURCE, key))),
        }
        for rid, key in sorted(resource_key_by_id.items(), key=lambda item: item[1])
    ]
    resources_done = sum(
        1
        for rv in resources_view
        if rv["activity"] and rv["activity"]["status"] in _DONE_STATUSES
    )
    required_resources = [rv for rv in resources_view if rv["required"]]
    required_resources_done = sum(
        1 for rv in required_resources
        if rv["activity"] and rv["activity"]["status"] in _DONE_STATUSES
    )

    role_views: dict[str, list] = {
        V2_ACTIVITY_QUICK_CHECK: [],
        V2_ACTIVITY_MODULE_QUIZ: [],
        V2_ACTIVITY_PRACTICAL: [],
        V2_ACTIVITY_SERVICE_DESK: [],
        V2_ACTIVITY_EXPLAIN: [],
    }
    for a in assessments:
        role = a.assessment_role
        if role not in role_views:
            continue
        role_views[role].append(
            {
                "assessment_key": a.assessment_key,
                "title": a.title,
                "lesson_key": (
                    db.get(LessonV2Meta, a.lesson_v2_meta_id).lesson_key
                    if a.lesson_v2_meta_id
                    else None
                ),
                "pass_percent": a.pass_percent,
                "engine_bound": bool(
                    a.quiz_id or a.lab_template_id or a.service_desk_scenario_id
                ),
                "activity": _activity_view(by_ref.get((role, a.assessment_key))),
            }
        )

    quiz_entry = next(iter(role_views[V2_ACTIVITY_MODULE_QUIZ]), None)
    module_quiz_passed = bool(
        quiz_entry and quiz_entry["activity"] and quiz_entry["activity"]["passed"]
    )

    quick_checks_done = sum(
        1
        for qc in role_views[V2_ACTIVITY_QUICK_CHECK]
        if qc["activity"] and qc["activity"]["status"] in _DONE_STATUSES | {V2_STATUS_PASSED}
    )

    prompt_keys = [
        key for (key,) in db.query(InterviewPrompt.prompt_key).filter(
            InterviewPrompt.certification_module_id == module.id,
            InterviewPrompt.active.is_(True),
        )
    ]
    explain_done = sum(
        1 for key in prompt_keys
        if by_ref.get((V2_ACTIVITY_EXPLAIN, key))
        and by_ref[(V2_ACTIVITY_EXPLAIN, key)].status in _DONE_STATUSES
    )
    practical_entry = next(iter(role_views[V2_ACTIVITY_PRACTICAL]), None)
    service_desk_entry = next(iter(role_views[V2_ACTIVITY_SERVICE_DESK]), None)
    practical_done = not practical_entry or bool(
        practical_entry["activity"] and practical_entry["activity"]["status"] in _DONE_STATUSES
    )
    service_desk_done = not service_desk_entry or bool(
        service_desk_entry["activity"] and service_desk_entry["activity"]["status"] in _DONE_STATUSES
    )

    return {
        "module_key": module_key,
        "module_title": module.title,
        "lessons": {
            "total": len(lesson_keys),
            "completed": lessons_done,
            "items": lessons_view,
        },
        "resources": {
            "total": len(resources_view),
            "completed": resources_done,
            "required": len(required_resources),
            "required_completed": required_resources_done,
            "items": resources_view,
        },
        "quick_checks": {
            "total": len(role_views[V2_ACTIVITY_QUICK_CHECK]),
            "completed": quick_checks_done,
            "items": role_views[V2_ACTIVITY_QUICK_CHECK],
        },
        "module_quiz": quiz_entry,
        "practical": practical_entry,
        "service_desk": service_desk_entry,
        "explain": role_views[V2_ACTIVITY_EXPLAIN],
        "explain_prompts": {"total": len(prompt_keys), "completed": explain_done},
        "module_complete": bool(
            len(lesson_keys)
            and lessons_done == len(lesson_keys)
            and required_resources_done == len(required_resources)
            and quick_checks_done == len(role_views[V2_ACTIVITY_QUICK_CHECK])
            and module_quiz_passed
            and practical_done
            and service_desk_done
            and explain_done == len(prompt_keys)
        ),
    }


def reconcile_v2_service_desk_attempt(
    db: Session, *, student_id: int, scenario_id: int, attempt_id: int,
    score: int, passed: bool,
) -> V2ModuleActivity | None:
    """Reconcile only a relationship created by the gated V2 launch route.

    Assignments may predate V2 (the legacy seed creates simulation rows), and
    the same scenario can have learning and simulation assignments. The V2
    activity is therefore the authoritative curriculum relationship.
    """
    from app.models.service_desk import (
        ServiceDeskAttempt,
        ServiceDeskAttemptEvent,
        ServiceDeskScenarioVersion,
    )

    student = db.get(Student, student_id)
    if not student_has_v2_access(student):
        return None

    attempt = (
        db.query(ServiceDeskAttempt)
        .join(
            ServiceDeskScenarioVersion,
            ServiceDeskScenarioVersion.id == ServiceDeskAttempt.scenario_version_id,
        )
        .filter(
            ServiceDeskAttempt.id == attempt_id,
            ServiceDeskAttempt.student_id == student_id,
            ServiceDeskScenarioVersion.scenario_id == scenario_id,
        )
        .one_or_none()
    )
    if attempt is None:
        return None

    activities = db.query(V2ModuleActivity).filter_by(
        student_id=student_id, activity_type=V2_ACTIVITY_SERVICE_DESK
    ).all()
    marker = db.query(ServiceDeskAttemptEvent).filter_by(
        attempt_id=attempt_id,
        event_type="v2.curriculum_launch",
        trusted=True,
    ).one_or_none()
    context = marker.payload_json or {} if marker else {}
    if not context:
        return None
    for activity in activities:
        if (
            activity.module_key != context.get("module_key")
            or activity.ref_key != context.get("assessment_key")
        ):
            continue
        if (activity.detail or {}).get("scenario_id") != scenario_id:
            continue
        module = db.query(CertificationModule).filter_by(
            module_key=activity.module_key, active=True
        ).one_or_none()
        if module is None:
            continue
        assessment = db.query(ModuleAssessment).filter_by(
            certification_module_id=module.id,
            assessment_key=activity.ref_key,
            assessment_role=V2_ACTIVITY_SERVICE_DESK,
            service_desk_scenario_id=scenario_id,
            active=True,
        ).one_or_none()
        if assessment is None:
            continue
        # The required curriculum case is the guided/learning experience.
        # Practice and assessment attempts are optional reinforcement after
        # that requirement has already passed; they cannot earn the initial
        # module credit even when launched with trusted V2 context.
        if activity.status != V2_STATUS_PASSED and attempt.experience_mode != "guided":
            return None
        # Once the required guided case has passed, later assessment/practice
        # launches are optional reinforcement and cannot regress module credit.
        if activity.status == V2_STATUS_PASSED and not passed:
            return activity
        return record_activity(
            db, student_id=student_id, module_key=activity.module_key,
            activity_type=V2_ACTIVITY_SERVICE_DESK, ref_key=activity.ref_key,
            status=V2_STATUS_PASSED if passed else "failed", score=score,
            passed=passed,
            detail={"attempt_id": attempt_id, "scenario_id": scenario_id},
        )
    return None
