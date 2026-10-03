"""Continuation is durable permission while mentor correction and mastery diverge."""

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from conftest import auth_headers, enroll_v2, make_client, make_student
from test_v2_beginner_stages import _load

from app.models.certification import (
    Certification, CertificationModule, CertificationVersion, LearningResource, LearningResourceLink,
    LessonV2Meta, ModuleAssessment, StudentResourceActivity,
)
from app.models.lab import LabRun, LabTemplate
from app.models.v2_continuation import V2BeginnerContinuationGrant
from app.models.v2_evidence import V2EvidenceRecord, V2EvidenceRequirement
from app.models.v2_progress import V2ModuleActivity
from app.database import Base
from app.models.student import Student
from app.routers.v2_curriculum import router
from app.services.v2_beginner_path import STAGE_KEYS, stage_lock_reason
from app.services.v2_continuation_backfill import backfill_beginner_continuation
from app.services.v2_continuation_service import create_beginner_continuation_grant, ensure_beginner_continuation_grant
import app.services.v2_continuation_service as continuation_service
from app.services.v2_curriculum_service import entry_view, module_view
from app.services.v2_progress_service import module_progress, record_activity


def _automatic_evidence(db, student_id, module_key, *, leave_assessment=None):
    """Construct the same trusted rollups the real resource/engine routes own."""
    module = db.query(CertificationModule).filter_by(module_key=module_key).one()
    lesson_ids = [row.id for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
    links = db.query(LearningResourceLink).filter(
        (LearningResourceLink.certification_module_id == module.id)
        | (LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids or [-1]))
    ).all()
    now = datetime.now(timezone.utc)
    for resource_id in {row.resource_id for row in links if row.is_required}:
        resource = db.get(LearningResource, resource_id)
        db.add(StudentResourceActivity(
            student_id=student_id, resource_id=resource_id, opened_at=now,
            watched_at=now if resource.resource_type == "video" else None,
        ))
    for requirement in db.query(V2EvidenceRequirement).filter_by(module_id=module.id, active=True, is_required=True):
        db.add(V2EvidenceRecord(student_id=student_id, requirement_id=requirement.id, source_ref="disposable-test-attempt"))
    assessments = db.query(ModuleAssessment).filter_by(certification_module_id=module.id, active=True).all()
    for assessment in assessments:
        if not assessment.config.get("required", True) or assessment.assessment_role == "practical" or assessment.assessment_key == leave_assessment:
            continue
        db.add(V2ModuleActivity(
            student_id=student_id, module_key=module_key, activity_type=assessment.assessment_role,
            ref_key=assessment.assessment_key, status="passed", passed=True,
        ))
    db.commit()
    return module


def _practical_submission(db, student_id, module_key, assessment, *, status="needs_review", decision=None):
    now = datetime.now(timezone.utc)
    run = LabRun(
        student_id=student_id, lab_template_id=assessment.lab_template_id,
        status="submitted" if status in {"needs_review", "passed"} else "in_progress",
        started_at=now, submitted_at=now if status in {"needs_review", "passed"} else None,
    )
    db.add(run)
    db.flush()
    detail = {"lab_run_id": run.id}
    if decision:
        detail.update({"review_decision": decision, "reviewed_at": now.isoformat(), "review_feedback": "Show the missing evidence"})
    record_activity(
        db, student_id=student_id, module_key=module_key, activity_type="practical",
        ref_key=assessment.assessment_key, status=status,
        passed=True if status == "passed" else False if status == "failed" else None,
        detail=detail,
    )
    db.commit()
    return run


def test_practical_first_then_last_checkpoint_grants_once(db, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, "continuation_order")
    stage = STAGE_KEYS[3]
    assessment = db.query(ModuleAssessment).filter_by(assessment_key="assess.nexus.beginner.s4.windows_observation").one()
    final_key = "assess.nexus.beginner.s4.clues"
    module = _automatic_evidence(db, student.id, stage, leave_assessment=final_key)
    assert not module_progress(db, student.id, stage)["continuation_eligible"]
    _practical_submission(db, student.id, stage, assessment)
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=module.id).count() == 0
    record_activity(db, student_id=student.id, module_key=stage, activity_type="module_quiz", ref_key=final_key, status="passed", passed=True, commit=True)
    progress = module_progress(db, student.id, stage)
    assert progress["continuation_granted"] and not progress["module_complete"]
    assert progress["can_continue"] and progress["continuation_status"] == "granted"
    assert progress["status"] == "awaiting_mentor_review"
    assert ensure_beginner_continuation_grant(db, student.id, stage) is False
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=module.id).count() == 1


def test_multiple_required_mentor_practicals_and_optional_work(db, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, "continuation_multiple")
    stage = STAGE_KEYS[3]
    module = _automatic_evidence(db, student.id, stage)
    required = db.query(ModuleAssessment).filter_by(assessment_key="assess.nexus.beginner.s4.windows_observation").one()
    template = LabTemplate(title="Disposable second mentor practical", lab_type="guided", required_evidence={"mentor_review_required": True})
    db.add(template)
    db.flush()
    second = ModuleAssessment(
        assessment_key="disposable.second_practical", certification_module_id=module.id,
        assessment_role="practical", title="Second practical", lab_template_id=template.id,
        config={"required": True},
    )
    optional = ModuleAssessment(
        assessment_key="disposable.optional_practical", certification_module_id=module.id,
        assessment_role="practical", title="Optional practical", lab_template_id=template.id,
        config={"required": False},
    )
    db.add_all([second, optional])
    db.commit()
    _practical_submission(db, student.id, stage, required)
    assert not module_progress(db, student.id, stage)["continuation_granted"]
    assert module_view(db, student.id, stage)["continue"]["route"].endswith("/disposable.second_practical")
    _practical_submission(db, student.id, stage, second)
    assert module_progress(db, student.id, stage)["continuation_granted"]
    assert not module_progress(db, student.id, stage)["module_complete"]


def test_rejected_stage_stays_separate_from_current_learning(db, monkeypatch, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, "continuation_current")
    enroll_v2(monkeypatch, student)
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    stage = STAGE_KEYS[0]
    module = _automatic_evidence(db, student.id, stage)
    assert module_progress(db, student.id, stage)["module_complete"]
    assert ensure_beginner_continuation_grant(db, student.id, stage)
    template = LabTemplate(title="Disposable correction practical", lab_type="guided", required_evidence={"mentor_review_required": True})
    db.add(template)
    db.flush()
    assessment = ModuleAssessment(
        assessment_key="disposable.stage1_correction", certification_module_id=module.id,
        assessment_role="practical", title="Correction practical", lab_template_id=template.id,
        config={"required": True},
    )
    db.add(assessment)
    db.commit()
    _practical_submission(db, student.id, stage, assessment)
    assert module_progress(db, student.id, stage)["status"] == "awaiting_mentor_review"
    assert entry_view(db, student.id)["current"]["module"]["key"] == STAGE_KEYS[1]
    assert module_view(db, student.id, stage)["continue"]["kind"] == "next_stage"
    _practical_submission(db, student.id, stage, assessment, status="failed", decision="reject")
    progress = module_progress(db, student.id, stage)
    assert not progress["module_complete"] and progress["continuation_granted"]
    assert progress["status"] == "needs_correction"
    assert module_view(db, student.id, stage)["continue"] == {
        "kind": "next_stage", "label": "Continue learning",
        "title": db.query(CertificationModule).filter_by(module_key=STAGE_KEYS[1]).one().title,
        "route": f"/learning-v2/modules/{STAGE_KEYS[1]}",
        "status": "available", "estimated_minutes": None,
    }
    entry = entry_view(db, student.id)
    assert entry["current"]["module"]["key"] == STAGE_KEYS[1]
    assert entry["corrections"][0]["module_key"] == stage
    assert entry["outstanding_corrections"] == entry["corrections"]
    client = make_client(router)
    headers = auth_headers(student)
    assert client.get(f"/api/v2/curriculum/modules/{STAGE_KEYS[1]}", headers=headers).status_code == 200
    stage2_check = db.query(ModuleAssessment).join(
        CertificationModule, CertificationModule.id == ModuleAssessment.certification_module_id,
    ).filter(CertificationModule.module_key == STAGE_KEYS[1], ModuleAssessment.assessment_role == "quick_check").first()
    assert client.get(f"/api/v2/curriculum/modules/{STAGE_KEYS[1]}/assessments/{stage2_check.assessment_key}", headers=headers).status_code == 200
    assert client.get(f"/api/v2/curriculum/modules/{STAGE_KEYS[2]}", headers=headers).status_code == 403


def test_backfill_dry_run_pending_rejected_prior_access_and_rerun(db, tmp_path):
    _load(db, tmp_path)
    pending = make_student(db, "backfill_pending")
    rejected = make_student(db, "backfill_rejected")
    pending_incomplete = make_student(db, "backfill_pending_incomplete")
    rejected_unproven = make_student(db, "backfill_rejected_unproven")
    reopened = make_student(db, "backfill_reopened_approval")
    reopened_rejection = make_student(db, "backfill_reopened_rejection")
    failed_only = make_student(db, "backfill_failed_only")
    prior_access = make_student(db, "backfill_prior_access")
    stage = STAGE_KEYS[3]
    assessment = db.query(ModuleAssessment).filter_by(assessment_key="assess.nexus.beginner.s4.windows_observation").one()
    module = _automatic_evidence(db, pending.id, stage)
    _automatic_evidence(db, rejected.id, stage)
    _automatic_evidence(db, rejected_unproven.id, stage)
    _automatic_evidence(db, reopened.id, stage)
    _automatic_evidence(db, reopened_rejection.id, stage)
    _practical_submission(db, pending.id, stage, assessment)
    _practical_submission(db, rejected.id, stage, assessment, status="failed", decision="reject")
    _practical_submission(db, pending_incomplete.id, stage, assessment)
    reopened_run = _practical_submission(db, reopened.id, stage, assessment, status="passed", decision="approve")
    reopened_run.status = "in_progress"
    reopened_run.submitted_at = None
    reopened_activity = record_activity(
        db, student_id=reopened.id, module_key=stage, activity_type="practical",
        ref_key=assessment.assessment_key, status="in_progress", allow_regression=True,
    )
    reopened_activity.passed = None
    db.commit()
    rejected_run = _practical_submission(
        db, reopened_rejection.id, stage, assessment, status="failed", decision="reject",
    )
    rejected_run.status = "in_progress"
    rejected_activity = record_activity(
        db, student_id=reopened_rejection.id, module_key=stage,
        activity_type="practical", ref_key=assessment.assessment_key,
        status="in_progress", allow_regression=True,
    )
    rejected_activity.passed = None
    db.commit()
    assert module_progress(db, reopened_rejection.id, stage)["status"] == "needs_correction"
    # Model historical pre-grant data. Ordinary application code never deletes grants.
    db.query(V2BeginnerContinuationGrant).filter(
        V2BeginnerContinuationGrant.student_id.in_((pending.id, rejected.id, reopened.id, reopened_rejection.id)),
    ).delete(synchronize_session=False)
    db.add_all([
        V2ModuleActivity(student_id=rejected_unproven.id, module_key=stage, activity_type="practical", ref_key=assessment.assessment_key, status="failed", passed=False, detail={"review_decision": "reject", "reviewed_at": datetime.now(timezone.utc).isoformat(), "lab_run_id": 999999}),
        V2ModuleActivity(student_id=failed_only.id, module_key=STAGE_KEYS[2], activity_type="lesson", ref_key="disposable.failed", status="failed"),
        V2ModuleActivity(student_id=prior_access.id, module_key=STAGE_KEYS[2], activity_type="lesson", ref_key="disposable.started", status="in_progress"),
    ])
    db.commit()
    assert ensure_beginner_continuation_grant(db, reopened.id, stage) is False
    assert ensure_beginner_continuation_grant(db, reopened_rejection.id, stage) is False
    assert ensure_beginner_continuation_grant(db, rejected.id, stage) is False
    before = db.query(V2BeginnerContinuationGrant).count()
    preview = backfill_beginner_continuation(db, dry_run=True)
    assert db.query(V2BeginnerContinuationGrant).count() == before
    assert preview["counts"]["requirements_satisfied"] >= 2
    assert preview["counts"]["backfill_reopened_approval"] >= 1
    assert preview["counts"]["backfill_prior_access"] >= 2
    assert any(row["student_id"] == failed_only.id for row in preview["exceptions"])
    assert any(row["student_id"] == rejected_unproven.id and row["module_key"] == stage for row in preview["exceptions"])
    applied = backfill_beginner_continuation(db, dry_run=False)
    assert applied["counts"] == preview["counts"]
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=pending.id, certification_module_id=module.id).one().grant_reason == "requirements_satisfied"
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=rejected.id, certification_module_id=module.id).one().grant_reason == "requirements_satisfied"
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=reopened.id, certification_module_id=module.id).one().grant_reason == "backfill_reopened_approval"
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=reopened_rejection.id, certification_module_id=module.id).one().grant_reason == "requirements_satisfied"
    assert module_progress(db, reopened.id, stage)["module_complete"] is False
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=pending_incomplete.id, certification_module_id=module.id).count() == 0
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=rejected_unproven.id, certification_module_id=module.id).count() == 0
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=failed_only.id).count() == 0
    assert stage_lock_reason(db, prior_access.id, STAGE_KEYS[2]) is None
    assert all(count == 0 for count in backfill_beginner_continuation(db, dry_run=False)["counts"].values())


def test_finished_later_stage_remains_review_destination_over_older_correction(db, monkeypatch, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, "continuation_review_destination")
    monkeypatch.setenv("V2_BEGINNER_PATH_ENABLED", "true")
    for key in STAGE_KEYS[:2]:
        module = db.query(CertificationModule).filter_by(module_key=key).one()
        assert create_beginner_continuation_grant(db, student.id, module.id, "backfill_prior_access")
    stage3 = _automatic_evidence(db, student.id, STAGE_KEYS[2])
    assert ensure_beginner_continuation_grant(db, student.id, STAGE_KEYS[2])
    template = LabTemplate(title="Disposable older correction", lab_type="guided", required_evidence={"mentor_review_required": True})
    db.add(template)
    db.flush()
    old_practical = ModuleAssessment(
        assessment_key="disposable.older_correction", certification_module_id=stage3.id,
        assessment_role="practical", title="Older correction", lab_template_id=template.id,
        config={"required": True},
    )
    db.add(old_practical)
    db.commit()
    _practical_submission(db, student.id, STAGE_KEYS[2], old_practical, status="failed", decision="reject")
    _automatic_evidence(db, student.id, STAGE_KEYS[3])
    stage4_practical = db.query(ModuleAssessment).filter_by(assessment_key="assess.nexus.beginner.s4.windows_observation").one()
    _practical_submission(db, student.id, STAGE_KEYS[3], stage4_practical, status="passed", decision="approve")
    assert module_progress(db, student.id, STAGE_KEYS[3])["module_complete"]
    entry = entry_view(db, student.id)
    assert entry["current"]["module"]["key"] == STAGE_KEYS[3]
    assert entry["corrections"][0]["module_key"] == STAGE_KEYS[2]


def test_backfill_mastered_stage_without_mentor_practical(db, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, "backfill_mastered")
    module = _automatic_evidence(db, student.id, STAGE_KEYS[0])
    before = module_progress(db, student.id, STAGE_KEYS[0])
    assert before["module_complete"] and not before["continuation_granted"]
    assert backfill_beginner_continuation(db, dry_run=True)["counts"]["backfill_mastered"] >= 1
    assert db.query(V2BeginnerContinuationGrant).count() == 0
    backfill_beginner_continuation(db, dry_run=False)
    grant = db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=module.id).one()
    assert grant.grant_reason == "backfill_mastered"
    assert module_progress(db, student.id, STAGE_KEYS[0])["module_complete"] is True


def test_concurrent_grant_inserts_keep_one_row_and_transactions_usable(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent-continuation.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as session:
        student = Student(name="Concurrent", email="concurrent@local.test", username="concurrent", password_hash="test")
        cert = Certification(cert_key="continuation-test", name="Continuation test")
        session.add_all([student, cert])
        session.flush()
        version = CertificationVersion(certification_id=cert.id, version_key="continuation-test-v1", label="Test", exam_codes=[])
        session.add(version)
        session.flush()
        module = CertificationModule(certification_version_id=version.id, module_key=STAGE_KEYS[0], title="Test")
        session.add(module)
        session.commit()
        student_id, module_id = student.id, module.id

    barrier = Barrier(2)

    def attempt():
        with Session() as session:
            barrier.wait(timeout=10)
            created = create_beginner_continuation_grant(session, student_id, module_id, "requirements_satisfied")
            session.commit()
            assert session.query(V2BeginnerContinuationGrant).count() == 1
            return created

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    with Session() as session:
        assert session.query(V2BeginnerContinuationGrant).count() == 1
    assert sorted(results) == [False, True]
    engine.dispose()


def test_duplicate_insert_savepoint_preserves_unrelated_write(db, monkeypatch, tmp_path):
    _load(db, tmp_path)
    student = make_student(db, "continuation_savepoint")
    module = db.query(CertificationModule).filter_by(module_key=STAGE_KEYS[0]).one()
    assert create_beginner_continuation_grant(db, student.id, module.id, "requirements_satisfied")
    db.commit()
    student.name = "Unrelated successful update"
    actual_has = continuation_service.has_beginner_continuation_grant
    first = True

    def raced_check(session, student_id, module_id):
        nonlocal first
        if first:
            first = False
            return False
        return actual_has(session, student_id, module_id)

    monkeypatch.setattr(continuation_service, "has_beginner_continuation_grant", raced_check)
    assert create_beginner_continuation_grant(db, student.id, module.id, "requirements_satisfied") is False
    db.commit()
    db.expire_all()
    assert db.get(Student, student.id).name == "Unrelated successful update"
    assert db.query(V2BeginnerContinuationGrant).filter_by(student_id=student.id, certification_module_id=module.id).count() == 1
