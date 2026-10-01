"""Phase 1: viewing, checks and trusted evidence have distinct meanings."""

from datetime import date, timedelta

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import (
    CertificationModule, InterviewPrompt, LearningResource, LearningResourceLink,
    LessonV2Meta, ModuleAssessment, StudentResourceActivity,
)
from app.models.flashcard import FlashcardReview
from app.models.quiz import Question
from app.models.v2_evidence import V2EvidenceRecord, V2EvidenceRequirement
from app.routers.v2_curriculum import router
from app.services.v2_content_loader import load_module
from app.services.v2_curriculum_service import entry_view, resource_activity
from app.services.v2_progress_service import module_progress, record_activity, record_trusted_evidence


MODULE = "module.aplus.core1.network_services_troubleshooting"


def _foundation(db, monkeypatch):
    load_module(db, commit=True)
    student = make_student(db, username="v2_evidence_student")
    enroll_v2(monkeypatch, student)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    lesson_ids = [row.id for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
    links = db.query(LearningResourceLink).filter(
        (LearningResourceLink.certification_module_id == module.id)
        | (LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids))
    ).all()
    video = next(db.get(LearningResource, link.resource_id) for link in links if db.get(LearningResource, link.resource_id).resource_type == "video")
    for link in links:
        link.is_required = link.resource_id == video.id
    assessment = db.query(ModuleAssessment).filter_by(certification_module_id=module.id, assessment_role="module_quiz").first()
    for item in db.query(ModuleAssessment).filter_by(certification_module_id=module.id):
        item.active = item.id == assessment.id
    for prompt in db.query(InterviewPrompt).filter_by(certification_module_id=module.id):
        prompt.active = False
    db.commit()
    return student, module, video, assessment, make_client(router)


def _pass_check(db, student, assessment):
    record_activity(
        db, student_id=student.id, module_key=MODULE,
        activity_type="module_quiz", ref_key=assessment.assessment_key,
        status="passed", passed=True, commit=True,
    )


def test_opened_watched_failed_and_passed_check_are_distinct(db, monkeypatch):
    student, _module, video, assessment, _client = _foundation(db, monkeypatch)
    assert module_progress(db, student.id, MODULE)["status"] == "not_started"
    resource_activity(db, student.id, MODULE, video.resource_key, opened=True)
    opened = module_progress(db, student.id, MODULE)
    assert opened["status"] == "in_progress"
    assert opened["module_complete"] is False
    resource_activity(db, student.id, MODULE, video.resource_key, watched=True)
    watched = module_progress(db, student.id, MODULE)
    assert watched["status"] == "check_required"
    assert watched["evidence"]["watched"] is True
    assert watched["module_complete"] is False
    record_activity(
        db, student_id=student.id, module_key=MODULE,
        activity_type="module_quiz", ref_key=assessment.assessment_key,
        status="failed", passed=False, commit=True,
    )
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    _pass_check(db, student, assessment)
    complete = module_progress(db, student.id, MODULE)
    assert complete["status"] == "mastered"
    assert complete["module_complete"] is True
    assert complete["evidence"]["check_passed"] is True


def test_optional_resource_and_passed_check_do_not_replace_required_video(db, monkeypatch):
    student, _module, video, assessment, _client = _foundation(db, monkeypatch)
    _pass_check(db, student, assessment)
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    resource_activity(db, student.id, MODULE, video.resource_key, opened=True)
    resource_activity(db, student.id, MODULE, video.resource_key, watched=True)
    complete = module_progress(db, student.id, MODULE)
    assert complete["module_complete"] is True
    assert complete["resources"]["exposed"] < complete["resources"]["total"]


def test_required_interaction_and_apply_need_trusted_records(db, monkeypatch):
    student, module, video, assessment, _client = _foundation(db, monkeypatch)
    interaction = V2EvidenceRequirement(module_id=module.id, evidence_type="interaction", ref_key="match.parts")
    apply = V2EvidenceRequirement(module_id=module.id, evidence_type="apply", ref_key="lab.parts")
    db.add_all([interaction, apply])
    db.commit()
    resource_activity(db, student.id, MODULE, video.resource_key, opened=True)
    resource_activity(db, student.id, MODULE, video.resource_key, watched=True)
    _pass_check(db, student, assessment)
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    record_trusted_evidence(db, student_id=student.id, requirement_id=interaction.id, source_ref="interaction-attempt:1")
    db.commit()
    partial = module_progress(db, student.id, MODULE)
    assert partial["evidence"]["interaction_completed"] is True
    assert partial["module_complete"] is False
    record_trusted_evidence(db, student_id=student.id, requirement_id=apply.id, source_ref="lab-attempt:1")
    db.commit()
    assert module_progress(db, student.id, MODULE)["module_complete"] is True
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id).count() == 2


def test_original_teaching_plus_interaction_can_be_mastered_without_video(db, monkeypatch):
    student, module, _video, _assessment, _client = _foundation(db, monkeypatch)
    for link in db.query(LearningResourceLink).filter_by(certification_module_id=module.id):
        link.is_required = False
    lesson_ids = [row.id for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
    for link in db.query(LearningResourceLink).filter(LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids)):
        link.is_required = False
    for assessment in db.query(ModuleAssessment).filter_by(certification_module_id=module.id):
        assessment.active = False
    requirement = V2EvidenceRequirement(module_id=module.id, evidence_type="interaction", ref_key="match.parts")
    db.add(requirement)
    db.commit()
    assert MODULE in {item["module"]["key"] for item in entry_view(db, student.id)["modules"]}
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    record_trusted_evidence(db, student_id=student.id, requirement_id=requirement.id, source_ref="interaction-attempt:2")
    db.commit()
    assert module_progress(db, student.id, MODULE)["module_complete"] is True


def test_review_due_preserves_mastery(db, monkeypatch):
    student, _module, video, assessment, _client = _foundation(db, monkeypatch)
    resource_activity(db, student.id, MODULE, video.resource_key, opened=True)
    resource_activity(db, student.id, MODULE, video.resource_key, watched=True)
    _pass_check(db, student, assessment)
    question = db.query(Question).filter_by(quiz_id=assessment.quiz_id).first()
    db.add(FlashcardReview(student_id=student.id, question_id=question.id, due_date=date.today() - timedelta(days=1)))
    db.commit()
    progress = module_progress(db, student.id, MODULE)
    assert progress["review_due"] is True
    assert progress["status"] == "mastered"
    assert progress["module_complete"] is True


def test_old_completed_row_is_history_not_new_watch_or_mastery(db, monkeypatch):
    student, _module, video, assessment, _client = _foundation(db, monkeypatch)
    db.add(StudentResourceActivity(student_id=student.id, resource_id=video.id, completed=True))
    db.commit()
    _pass_check(db, student, assessment)
    progress = module_progress(db, student.id, MODULE)
    assert progress["module_complete"] is False
    assert progress["resources"]["required_exposed"] == 0
    old_video = next(row for row in progress["resources"]["items"] if row["resource_key"] == video.resource_key)
    assert old_video["evidence"]["historical_self_reported_complete"] is True
    assert old_video["evidence"]["watched_at"] is None
    assert db.query(StudentResourceActivity).filter_by(student_id=student.id, resource_id=video.id).one().completed is True


def test_lesson_completion_and_passive_viewing_never_master_module(db, monkeypatch):
    student, module, video, _assessment, client = _foundation(db, monkeypatch)
    for assessment in db.query(ModuleAssessment).filter_by(certification_module_id=module.id):
        assessment.active = False
    lesson = db.query(LessonV2Meta).filter_by(certification_module_id=module.id).first()
    db.commit()
    url = f"/api/v2/curriculum/modules/{MODULE}/lessons/{lesson.lesson_key}/complete"
    assert client.post(url, headers=auth_headers(student)).status_code == 200
    resource_activity(db, student.id, MODULE, video.resource_key, opened=True)
    resource_activity(db, student.id, MODULE, video.resource_key, watched=True)
    progress = module_progress(db, student.id, MODULE)
    assert progress["lessons"]["completed"] == 1
    assert progress["module_complete"] is False
    assert progress["next_action"] == "Ask your mentor to add a knowledge check"


def test_non_video_opening_satisfies_exposure_but_cannot_be_watched(db, monkeypatch):
    student, module, _video, _assessment, client = _foundation(db, monkeypatch)
    links = db.query(LearningResourceLink).filter_by(certification_module_id=module.id).all()
    non_video = next((db.get(LearningResource, link.resource_id) for link in links if db.get(LearningResource, link.resource_id).resource_type != "video"), None)
    if non_video is None:
        lesson_ids = [row.id for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
        non_video = next(db.get(LearningResource, link.resource_id) for link in db.query(LearningResourceLink).filter(LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids)) if db.get(LearningResource, link.resource_id).resource_type != "video")
    db.query(LearningResourceLink).filter_by(resource_id=non_video.id).update({"is_required": True})
    db.commit()
    url = f"/api/v2/curriculum/modules/{MODULE}/resources/{non_video.resource_key}/activity"
    assert client.post(url, json={"opened": True}, headers=auth_headers(student)).status_code == 200
    assert client.post(url, json={"watched": True}, headers=auth_headers(student)).status_code == 409
    item = next(row for row in module_progress(db, student.id, MODULE)["resources"]["items"] if row["resource_key"] == non_video.resource_key)
    assert item["exposure_satisfied"] is True
    assert item["status"] == "viewed"
    assert item["evidence"]["watched_at"] is None


def test_student_api_rejects_mastery_and_direct_check_evidence(db, monkeypatch):
    student, _module, video, assessment, client = _foundation(db, monkeypatch)
    url = f"/api/v2/curriculum/modules/{MODULE}/resources/{video.resource_key}/activity"
    assert client.post(url, json={"watched": True, "mastered": True}, headers=auth_headers(student)).status_code == 422
    assert client.post(url, json={"opened": True, "check_passed": True}, headers=auth_headers(student)).status_code == 422
    assert client.post(url, json={"completed": True}, headers=auth_headers(student)).status_code == 422
    assert client.post(url, json={"interaction_completed": True}, headers=auth_headers(student)).status_code == 422
    assert client.post(url, json={"apply_passed": True}, headers=auth_headers(student)).status_code == 422
    assert client.post(url, json={"opened": True, "source_ref": "forged"}, headers=auth_headers(student)).status_code == 422
    assert client.post(url, json={"watched": True}, headers=auth_headers(student)).status_code == 409
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    assert assessment.pass_percent == 70  # existing published meaning is unchanged


def test_legacy_student_stays_outside_v2_and_legacy_watch_table_is_unchanged(db, monkeypatch):
    _student, _module, _video, _assessment, client = _foundation(db, monkeypatch)
    legacy = make_student(db, username="legacy_evidence_student")
    assert client.get(f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(legacy)).status_code == 404
    from app.models.video_watch import VideoWatch
    assert db.query(VideoWatch).filter_by(student_id=legacy.id).count() == 0


def test_pilot_api_exposes_new_status_and_next_action(db, monkeypatch):
    student, _module, video, _assessment, client = _foundation(db, monkeypatch)
    url = f"/api/v2/curriculum/modules/{MODULE}/resources/{video.resource_key}/activity"
    assert client.post(url, json={"opened": True}, headers=auth_headers(student)).status_code == 200
    assert client.post(url, json={"watched": True}, headers=auth_headers(student)).status_code == 200
    result = client.get(f"/api/v2/curriculum/modules/{MODULE}", headers=auth_headers(student)).json()["data"]
    assert result["progress"]["status"] == "check_required"
    assert result["progress"]["next_action"] == "Check understanding"
    assert result["progress"]["module_complete"] is False
    from app.models.video_watch import VideoWatch
    assert db.query(VideoWatch).filter_by(student_id=student.id).count() == 0
