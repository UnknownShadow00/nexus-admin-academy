"""Composable mentor intelligence for the frozen Nexus V2 reference module.

This is a read model, not an analytics store. It derives teaching signals from
V2 attempts, grading history, resource reports, and Lab / Service Desk records.
Nothing here feeds legacy progression.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.models.certification import (
    Certification, CertificationModule, CertificationObjective,
    CertificationVersion, InterviewPrompt, LearningResource,
    LearningResourceLink, LessonV2Meta, ModuleAssessment, QuestionV2Meta,
    StudentResourceActivity, question_objective_codes,
)
from app.models.grading import PendingGrade
from app.models.lab import LabRun
from app.models.quiz import Question
from app.models.service_desk import ServiceDeskAttempt, ServiceDeskAttemptGrade
from app.models.student import Student
from app.models.v2_progress import (
    V2_ACTIVITY_EXPLAIN, V2_ACTIVITY_MODULE_QUIZ, V2_ACTIVITY_QUICK_CHECK,
    V2AssessmentAttempt, V2AssessmentAttemptQuestion, V2ExplainSubmission,
    V2ModuleActivity,
)
from app.services.grading_queue import grading_history, mentor_queue
from app.services.v2_curriculum_service import module_view
from app.services.v2_progress_service import V2ProgressError

COHORT_FOCUS_KEY = "v2_cohort_focus"
DEFAULT_MODULE_KEY = "module.aplus.core1.ip_configuration"

# Specific tags win over generic ones, so dns+troubleshooting remains DNS.
TOPIC_TAGS = (
    ({"apipa", "dhcp"}, "DHCP and APIPA"),
    ({"dns", "nslookup"}, "DNS troubleshooting"),
    ({"gateway"}, "Default gateway"),
    ({"subnet-mask"}, "Subnet masks"),
    ({"ipv4", "private-addressing", "static-vs-dynamic"}, "IPv4 configuration"),
    ({"methodology"}, "Troubleshooting methodology"),
    ({"commands", "ping"}, "Windows network commands"),
)


def _module(db: Session, module_key: str) -> CertificationModule:
    row = db.query(CertificationModule).filter_by(module_key=module_key).one_or_none()
    if row is None:
        raise V2ProgressError(f"module '{module_key}' is not loaded")
    return row


def _friendly_topic(tags: list | None, objective_text: str | None) -> str:
    normalized = {str(tag).strip().lower() for tag in (tags or [])}
    for candidates, title in TOPIC_TAGS:
        if normalized & candidates:
            return title
    return objective_text or "Module knowledge"


def _correct_answers(question: Question) -> list[str]:
    answers = []
    for letter in question.all_correct_answers:
        option = getattr(question, f"option_{letter.lower()}", None)
        answers.append(f"{letter} — {option}" if option else letter)
    return answers


def _assessment_misses(
    db: Session, student_id: int, activities: list[V2ModuleActivity], version_id: int,
):
    """A miss is one incorrect result in one Nexus assessment attempt."""
    misses: dict[int, dict] = {}
    assessment_by_key = {
        row.assessment_key: row
        for row in db.query(ModuleAssessment).filter(
            ModuleAssessment.assessment_key.in_([a.ref_key for a in activities] or [""])
        )
    }
    for activity in activities:
        if activity.activity_type not in {V2_ACTIVITY_QUICK_CHECK, V2_ACTIVITY_MODULE_QUIZ}:
            continue
        # Phase 2A fixtures stored only ids. Keep that development history
        # readable while Phase 2B+ uses the richer attempts/results payload.
        for raw_qid in (activity.detail or {}).get("missed_question_ids") or []:
            try:
                qid = int(raw_qid)
            except (TypeError, ValueError):
                continue
            assessment = assessment_by_key.get(activity.ref_key)
            misses.setdefault(qid, {
                "question_id": qid, "times_missed": 1, "student_answer": None,
                "assessment_key": activity.ref_key,
                "assessment_title": assessment.title if assessment else None,
                "assessment_role": activity.activity_type,
            })
        for attempt in (activity.detail or {}).get("attempts") or []:
            for result in attempt.get("results") or []:
                if result.get("is_correct") is not False:
                    continue
                try:
                    qid = int(result.get("question_id"))
                except (TypeError, ValueError):
                    continue
                assessment = assessment_by_key.get(activity.ref_key)
                row = misses.setdefault(qid, {
                    "question_id": qid, "times_missed": 0, "student_answer": None,
                    "assessment_key": activity.ref_key,
                    "assessment_title": assessment.title if assessment else None,
                    "assessment_role": activity.activity_type,
                })
                row["times_missed"] += 1
                row["student_answer"] = result.get("student_answer")

    # Durable V2 attempt rows are the authoritative history. The JSON loop
    # above remains read-only compatibility for pre-migration development data.
    attempt_results = (
        db.query(V2AssessmentAttemptQuestion, V2AssessmentAttempt)
        .join(V2AssessmentAttempt, V2AssessmentAttempt.id == V2AssessmentAttemptQuestion.attempt_id)
        .filter(
            V2AssessmentAttempt.student_id == student_id,
            V2AssessmentAttempt.assessment_key.in_(list(assessment_by_key) or [""]),
            V2AssessmentAttemptQuestion.passed.is_(False),
        )
        .all()
    )
    for result, attempt in attempt_results:
        assessment = assessment_by_key.get(attempt.assessment_key)
        row = misses.setdefault(result.question_id, {
            "question_id": result.question_id, "times_missed": 0,
            "student_answer": None, "assessment_key": attempt.assessment_key,
            "assessment_title": assessment.title if assessment else None,
            "assessment_role": assessment.assessment_role if assessment else None,
        })
        row["times_missed"] += 1
        row["student_answer"] = result.submitted_answer

    if not misses:
        return [], [], []
    pairs = (
        db.query(Question, QuestionV2Meta)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(Question.id.in_(list(misses))).all()
    )
    question_by_id = {q.id: (q, meta) for q, meta in pairs}
    codes_by_meta = {meta.id: question_objective_codes(meta) for _, meta in pairs}
    objective_codes = {code for codes in codes_by_meta.values() for code in codes}
    objectives = {
        row.objective_code: row.objective_text
        for row in db.query(CertificationObjective).filter(
            CertificationObjective.certification_version_id == version_id,
            CertificationObjective.objective_code.in_(objective_codes or {""}),
        )
    }
    objective_counts: dict[str, int] = defaultdict(int)
    topic_counts: dict[str, int] = defaultdict(int)
    output = []
    for qid, stored in misses.items():
        if qid not in question_by_id:
            continue
        question, meta = question_by_id[qid]
        codes = codes_by_meta[meta.id]
        primary_code = codes[0] if codes else meta.objective_code
        objective_text = objectives.get(primary_code)
        topic = _friendly_topic(question.tags, objective_text)
        stored.update(
            question_text=question.question_text,
            correct_answer=_correct_answers(question), explanation=question.explanation,
            objective_code=primary_code, objective_codes=codes,
            objective_text=objective_text,
            objective_texts=[objectives.get(code) for code in codes], topic=topic,
        )
        output.append(stored)
        for code in codes:
            objective_counts[code] += stored["times_missed"]
        topic_counts[topic] += stored["times_missed"]
    weak_objectives = sorted((
        {"objective_code": code, "objective_text": objectives.get(code), "missed_count": count}
        for code, count in objective_counts.items()
    ), key=lambda row: (-row["missed_count"], row["objective_code"]))
    weak_topics = sorted((
        {"topic": topic, "missed_count": count} for topic, count in topic_counts.items()
    ), key=lambda row: (-row["missed_count"], row["topic"]))
    return sorted(output, key=lambda row: (-row["times_missed"], row["question_id"])), weak_objectives, weak_topics


def _external_practice(db: Session, student_id: int, module_id: int) -> list[dict]:
    rows = (
        db.query(StudentResourceActivity, LearningResource)
        .join(LearningResource, LearningResource.id == StudentResourceActivity.resource_id)
        .join(LearningResourceLink, LearningResourceLink.resource_id == LearningResource.id)
        .outerjoin(LessonV2Meta, LessonV2Meta.id == LearningResourceLink.lesson_v2_meta_id)
        .filter(
            StudentResourceActivity.student_id == student_id,
            (LearningResourceLink.certification_module_id == module_id)
            | (LessonV2Meta.certification_module_id == module_id),
        ).distinct().all()
    )
    return [{
        "resource_key": resource.resource_key, "resource": resource.title,
        "provider": resource.provider, "completed": activity.completed,
        "reported_score": activity.reported_score, "student_note": activity.student_note,
        "confusing_topic": activity.confusing_topic,
        "question_for_mentor": activity.question_for_mentor, "self_reported": True,
    } for activity, resource in rows if any((
        activity.completed, activity.reported_score is not None, activity.student_note,
        activity.confusing_topic, activity.question_for_mentor,
    ))]


def _explain_responses(db: Session, student_id: int, module_id: int) -> list[dict]:
    prompts = db.query(InterviewPrompt).filter_by(certification_module_id=module_id).all()
    prompt_by_key = {row.prompt_key: row for row in prompts}
    if not prompt_by_key:
        return []
    jobs = db.query(PendingGrade).filter(
        PendingGrade.student_id == student_id,
        PendingGrade.source_key.in_(list(prompt_by_key)),
    ).order_by(PendingGrade.created_at).all()
    job_by_ref = {job.submission_ref: job for job in jobs}
    prompt_by_id = {row.id: row for row in prompts}
    activities = {
        row.ref_key: row for row in db.query(V2ModuleActivity).filter(
            V2ModuleActivity.student_id == student_id,
            V2ModuleActivity.activity_type == V2_ACTIVITY_EXPLAIN,
            V2ModuleActivity.ref_key.in_(list(prompt_by_key)),
        )
    }

    def queued(job: PendingGrade, prompt: InterviewPrompt) -> dict:
        history = grading_history(db, job)
        safe_ai_attempts = [{
            "attempt_number": row["attempt_number"], "outcome": row["outcome"],
            "score": row["score"], "passed": row["passed"], "confidence": row["confidence"],
            "matched_concepts": row["matched_concepts"], "missing_concepts": row["missing_concepts"],
            "feedback": row["feedback"], "review_recommended": row["review_recommended"],
            "rubric_version": row["rubric_version"], "created_at": row["created_at"],
        } for row in history["ai_attempts"]]
        return {
            "pending_grade_id": job.id, "submission_ref": job.submission_ref,
            "prompt_key": prompt.prompt_key, "prompt": job.question_text or prompt.prompt,
            "submitted_answer": job.submitted_answer, "status": job.status,
            "deterministic": history["deterministic"], "ai_attempts": safe_ai_attempts,
            "confidence": next((r["confidence"] for r in reversed(history["ai_attempts"]) if r["confidence"] is not None), None),
            "review_recommended": any(r["review_recommended"] for r in history["ai_attempts"]),
            "rubric": job.rubric_json or prompt.rubric,
            "rubric_version": job.rubric_version or prompt.rubric_version,
            "expected_concepts": job.expected_concepts_json or prompt.expected_concepts,
            "mentor_overrides": history["mentor_overrides"], "resolved": history["resolved"],
        }

    output = []
    used_jobs = set()
    submissions = db.query(V2ExplainSubmission).filter(
        V2ExplainSubmission.student_id == student_id,
        V2ExplainSubmission.prompt_id.in_(list(prompt_by_id)),
    ).order_by(V2ExplainSubmission.submitted_at, V2ExplainSubmission.id).all()
    for submission in submissions:
        prompt = prompt_by_id[submission.prompt_id]
        ref = f"v2-explain:{submission.id}"
        job = job_by_ref.get(ref)
        if job:
            output.append(queued(job, prompt))
            used_jobs.add(job.id)
            continue
        activity = activities.get(prompt.prompt_key)
        detail = activity.detail or {} if activity else {}
        is_latest = detail.get("submission_id") == submission.id
        output.append({
            "pending_grade_id": None, "submission_ref": ref,
            "prompt_key": prompt.prompt_key, "prompt": prompt.prompt,
            "submitted_answer": submission.submitted_answer,
            "status": activity.status if activity and is_latest else "graded",
            "deterministic": {
                "status": detail.get("grading_state", "graded") if is_latest else "graded",
                "score": (detail.get("score") / 100) if is_latest and detail.get("score") is not None else None,
                "passed": detail.get("passed") if is_latest else None,
            },
            "ai_attempts": [], "confidence": None, "review_recommended": False,
            "rubric": prompt.rubric, "rubric_version": prompt.rubric_version,
            "expected_concepts": prompt.expected_concepts, "mentor_overrides": [],
            "resolved": {
                "grade_source": "deterministic",
                "score": (detail.get("score") / 100) if is_latest and detail.get("score") is not None else None,
                "passed": detail.get("passed") if is_latest else None,
                "graded_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            },
        })
    for job in jobs:
        if job.id not in used_jobs:
            output.append(queued(job, prompt_by_key[job.source_key]))
    return output


def _engine_details(db: Session, progress: dict):
    practical = progress.get("practical")
    practical_activity = (practical or {}).get("activity") or {}
    lab_run_id = (practical_activity.get("detail") or {}).get("lab_run_id")
    lab_run = db.get(LabRun, lab_run_id) if lab_run_id else None
    practical_detail = ({
        "title": practical.get("title"), "status": practical_activity.get("status"),
        "score": lab_run.final_score if lab_run else practical_activity.get("score"),
        "feedback": lab_run.feedback if lab_run else None, "notes": lab_run.notes if lab_run else None,
        "lab_run_id": lab_run_id,
        "review_url": f"/admin/labs?student_id={lab_run.student_id}" if lab_run else "/admin/labs",
        "activity": practical_activity,
    } if practical else None)

    service = progress.get("service_desk")
    service_activity = (service or {}).get("activity") or {}
    attempt_id = (service_activity.get("detail") or {}).get("attempt_id")
    attempt = db.get(ServiceDeskAttempt, attempt_id) if attempt_id else None
    grade = db.query(ServiceDeskAttemptGrade).filter_by(attempt_id=attempt_id).one_or_none() if attempt_id else None
    breakdown = []
    if grade:
        details = grade.details_json or {}
        checks, weights = details.get("objective_checks") or {}, details.get("process_weights") or {}
        for key in ("investigation", "diagnosis", "remediation", "verification", "documentation"):
            breakdown.append({"key": key, "label": key.title(), "met": checks.get(key), "weight": weights.get(key)})
    service_detail = ({
        "title": service.get("title"), "status": service_activity.get("status"),
        "score": attempt.score if attempt else service_activity.get("score"),
        "passed": attempt.passed if attempt else service_activity.get("passed"),
        "attempt_id": attempt_id, "breakdown": breakdown,
        "feedback": grade.feedback_summary if grade else None,
        "review_url": f"/admin/service-desk-review?attempt_id={attempt_id}" if attempt_id else "/admin/service-desk-review",
    } if service else None)
    return practical_detail, service_detail


def module_report(db: Session, student_id: int, module_key: str) -> dict:
    module = _module(db, module_key)
    student = db.get(Student, student_id)
    if student is None:
        raise V2ProgressError(f"student '{student_id}' does not exist")
    # Reuse the same engine-sync and Continue composition as the student V2
    # view. Sync is transaction-local on this read request and never touches
    # legacy progress.
    student_view = module_view(db, student_id, module_key)
    progress = student_view["progress"]
    activities = db.query(V2ModuleActivity).filter_by(student_id=student_id, module_key=module_key).all()
    missed, weak_objectives, weak_topics = _assessment_misses(
        db, student_id, activities, module.certification_version_id,
    )
    external = _external_practice(db, student_id, module.id)
    explain = _explain_responses(db, student_id, module.id)
    explain_activity = [{
        "submission_ref": row.ref_key, "source_type": "v2_module_activity",
        "status": row.status, "resolved_score": row.score, "resolved_passed": row.passed,
        "rubric_version": (row.detail or {}).get("rubric_version"),
    } for row in activities if row.activity_type == "explain"]
    practical, service_desk = _engine_details(db, progress)
    version = db.get(CertificationVersion, module.certification_version_id)
    certification = db.get(Certification, version.certification_id)
    current = student_view["continue"]
    quiz = progress.get("module_quiz") or {}
    quiz_activity = quiz.get("activity") or {}
    required_resources = [{
        "resource_key": resource["key"], "resource": resource["title"],
        "lesson": lesson["title"], "completed": resource["completed"],
    } for lesson in student_view["lessons"] for resource in lesson["resources"] if resource["required"]]
    return {
        "student_id": student_id, "student_name": student.name,
        "certification": {"name": certification.name, "version": version.label},
        "module_key": module_key, "module_title": module.title,
        "completion": {
            "module_complete": progress["module_complete"],
            "lessons_completed": progress["lessons"]["completed"], "lessons_total": progress["lessons"]["total"],
            "resources_completed": progress["resources"]["completed"], "resources_total": progress["resources"]["total"],
            "required_resources_completed": progress["resources"]["required_completed"],
            "required_resources_total": progress["resources"]["required"],
        },
        "module_quiz": {"score": quiz_activity.get("score"), "passed": quiz_activity.get("passed"),
                        "status": quiz_activity.get("status", "not_started"), "pass_percent": quiz.get("pass_percent")},
        "quick_checks": [{
            "assessment_key": item["assessment_key"], "title": item["title"],
            "status": (item.get("activity") or {}).get("status", "not_started"),
            "score": (item.get("activity") or {}).get("score"),
        } for item in progress["quick_checks"]["items"]],
        "required_resources": required_resources,
        "missed_questions": missed, "weak_objectives": weak_objectives, "weak_topics": weak_topics,
        "explain_responses": explain,
        "explain_state": [
            {"submission_ref": row["submission_ref"], "source_type": "interview_explain",
             "status": row["status"], "resolved_score": row["resolved"]["score"],
             "resolved_passed": row["resolved"]["passed"], "rubric_version": row["rubric_version"]}
            for row in explain
        ] + explain_activity,
        "explain_status": "needs_review" if any(r["status"] != "graded" for r in explain) else ("graded" if explain else "not_started"),
        "practical": practical, "service_desk": service_desk, "external_practice": external,
        "student_notes": [r for r in external if r["student_note"] or r["confusing_topic"] or r["question_for_mentor"]],
        "current_position": current,
    }


def cohort_focus(db: Session) -> dict | None:
    row = db.get(AppSetting, COHORT_FOCUS_KEY)
    return row.value if row else None


def set_cohort_focus(db: Session, module_key: str) -> dict:
    module = _module(db, module_key)
    version = db.get(CertificationVersion, module.certification_version_id)
    cert = db.get(Certification, version.certification_id)
    value = {"module_key": module.module_key, "certification": cert.name,
             "module_title": module.title, "display": f"{cert.name} → {module.title}"}
    row = db.get(AppSetting, COHORT_FOCUS_KEY)
    if row is None:
        db.add(AppSetting(key=COHORT_FOCUS_KEY, value=value))
    else:
        row.value = value
    db.commit()
    return value


def cohort_progress(db: Session, module_key: str = DEFAULT_MODULE_KEY) -> dict:
    _module(db, module_key)
    available_modules = db.query(CertificationModule).join(
        CertificationVersion, CertificationVersion.id == CertificationModule.certification_version_id
    ).filter(CertificationModule.active.is_(True)).order_by(
        CertificationVersion.id, CertificationModule.display_order, CertificationModule.id
    ).all()
    available_modules = [
        {"module_key": row.module_key, "title": row.title}
        for row in available_modules
        if db.query(LessonV2Meta).filter_by(certification_module_id=row.id).first() is not None
    ]
    students = db.query(Student).filter(Student.is_mentor.is_(False)).order_by(Student.name, Student.id).all()
    reports = [module_report(db, student.id, module_key) for student in students]
    topic_students: dict[str, set[int]] = defaultdict(set)
    topic_misses: dict[str, int] = defaultdict(int)
    repeated_students: dict[str, set[int]] = defaultdict(set)
    for report in reports:
        for row in report["weak_topics"]:
            topic, count = row["topic"], row["missed_count"]
            topic_students[topic].add(report["student_id"])
            topic_misses[topic] += count
            if count > 1:
                repeated_students[topic].add(report["student_id"])
    weak_areas = sorted(({
        "topic": topic, "students_affected": len(ids), "student_count": len(students),
        "total_misses": topic_misses[topic], "students_with_repeated_misses": len(repeated_students[topic]),
    } for topic, ids in topic_students.items()), key=lambda row: (-row["students_affected"], -row["total_misses"], row["topic"]))
    suggestions = [{
        "topic": row["topic"], "students_affected": row["students_affected"],
        "reason": f"{row['students_affected']} student{'s' if row['students_affected'] != 1 else ''} showing difficulty",
    } for row in weak_areas[:5]]
    questions = [{"student_id": report["student_id"], "student_name": report["student_name"], **note}
                 for report in reports for note in report["student_notes"]]
    return {
        "module_key": module_key, "available_modules": available_modules,
        "student_count": len(students), "cohort_focus": cohort_focus(db),
        "students": [{
            "student_id": r["student_id"], "student_name": r["student_name"], "certification": r["certification"],
            "module_key": r["module_key"], "module_title": r["module_title"], "completion": r["completion"],
            "module_quiz": r["module_quiz"], "practical": r["practical"], "service_desk": r["service_desk"],
            "explain_status": r["explain_status"], "weak_topics": r["weak_topics"], "current_position": r["current_position"],
        } for r in reports],
        "needs_review": mentor_queue(db, limit=50), "weak_areas": weak_areas,
        "suggested_review_topics": suggestions, "student_questions": questions,
    }
