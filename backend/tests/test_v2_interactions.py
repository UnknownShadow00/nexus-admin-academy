"""Native V2 interaction grading, evidence, history and abuse boundaries."""

import copy
import yaml

import pytest
from sqlalchemy import event

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import CertificationModule, InterviewPrompt, LearningResourceLink, LessonV2Meta, ModuleAssessment
from app.models.student import Student
from app.models.v2_evidence import V2EvidenceRecord, V2EvidenceRequirement
from app.models.v2_interaction import V2InteractionAttempt, V2InteractionDefinition
from app.routers.v2_curriculum import router
from app.services.student_deletion import delete_student_owned_data, student_owned_row_counts
from app.services.v2_content_loader import load_module
from app.services.v2_interaction_loader import DEFAULT_PILOT_PATH, load_interactions
from app.services.v2_interaction_service import InteractionValidationError, interaction_list, validate_definition
from app.services.v2_progress_service import module_progress, record_activity


MODULE = "module.aplus.core1.ip_configuration"
ROOT = "/api/v2/curriculum/modules"


@pytest.fixture
def pilot(db, monkeypatch):
    load_module(db, commit=True)
    summary = load_interactions(db, commit=True)
    assert summary["created"] == 6
    student = make_student(db, username="interaction_pilot")
    enroll_v2(monkeypatch, student)
    return student, make_client(router)


def _url(key):
    return f"{ROOT}/{MODULE}/interactions/interaction.pilot.{key}"


def _version_id(client, student, url):
    result = client.get(url, headers=auth_headers(student))
    assert result.status_code == 200
    return result.json()["data"]["interaction"]["version_id"]


@pytest.mark.parametrize("key,correct,wrong", [
    ("hardware-match", {"matches": {"ram": "memory", "rj45": "ethernet", "usb-c": "reversible"}}, {"matches": {"ram": "ethernet", "rj45": "memory", "usb-c": "reversible"}}),
    ("ethernet-port", {"choice_id": "ethernet"}, {"choice_id": "hdmi"}),
    ("troubleshooting-order", {"order": ["ask", "check", "test"]}, {"order": ["test", "check", "ask"]}),
    ("ipconfig-output", {"choice_id": "dhcp"}, {"choice_id": "normal"}),
    ("safe-network-step", {"choice_id": "ask-check"}, {"choice_id": "wipe"}),
])
def test_each_structured_type_grades_wrong_then_correct_and_allows_retry(pilot, db, key, correct, wrong):
    student, client = pilot
    url = _url(key)
    before = client.get(url, headers=auth_headers(student))
    assert before.status_code == 200
    assert before.json()["data"]["progress"]["status"] == "not_started"
    assert "correct_choice_id" not in str(before.json()["data"]["interaction"])
    version_id = before.json()["data"]["interaction"]["version_id"]
    failed = client.post(url + "/submit", json={"version_id": version_id, "response": wrong}, headers=auth_headers(student))
    assert failed.status_code == 200
    assert failed.json()["data"]["submission_result"]["passed"] is False
    assert failed.json()["data"]["progress"]["status"] == "in_progress"
    passed = client.post(url + "/submit", json={"version_id": version_id, "response": correct}, headers=auth_headers(student))
    assert passed.status_code == 200
    assert passed.json()["data"]["submission_result"]["passed"] is True
    assert passed.json()["data"]["interaction"]["lesson_key"] == before.json()["data"]["interaction"]["lesson_key"]
    assert passed.json()["data"]["submission_result"]["next_action"] == "Return to the module for your next step"
    if key == "hardware-match":
        assert "RAM → Short-term working memory" in passed.json()["data"]["submission_result"]["correct_answer"]
    if key == "troubleshooting-order":
        assert passed.json()["data"]["submission_result"]["correct_answer"][0] == "Ask the user what changed and what they see."
    assert passed.json()["data"]["progress"]["status"] == "passed"
    assert [row.attempt_number for row in db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key=f"interaction.pilot.{key}").order_by(V2InteractionAttempt.attempt_number)] == [1, 2]
    assert db.get(Student, student.id).total_xp == 0


def test_typed_answer_uses_narrow_authored_normalization(pilot, db):
    student, client = pilot
    url = _url("ipconfig-command")
    public = client.get(url, headers=auth_headers(student)).json()["data"]["interaction"]
    assert "accepted_answers" not in str(public)
    for answer, expected in (("  IPCONFIG   ", True), ("ipconfig.exe", True), ("ip config", False)):
        result = client.post(url + "/submit", json={"version_id": public["version_id"], "response": {"answer": answer}}, headers=auth_headers(student))
        assert result.status_code == 200
        assert result.json()["data"]["submission_result"]["passed"] is expected
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.ipconfig-command").count() == 3


def test_authored_scored_threshold_is_applied_on_the_server(pilot, db):
    student, client = pilot
    definition = db.query(V2InteractionDefinition).filter_by(interaction_key="interaction.pilot.hardware-match").one()
    definition.pass_percent = 33
    db.commit()
    result = client.post(
        _url("hardware-match") + "/submit",
        json={"version_id": definition.id, "response": {"matches": {"ram": "memory", "rj45": "reversible", "usb-c": "ethernet"}}},
        headers=auth_headers(student),
    )
    assert result.status_code == 200
    assert result.json()["data"]["submission_result"]["score"] == 33
    assert result.json()["data"]["submission_result"]["passed"] is True
    assert result.json()["data"]["submission_result"]["correct"] is False


def test_required_interaction_blocks_then_records_one_trusted_evidence(pilot, db):
    student, client = pilot
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    for link in db.query(LearningResourceLink).filter_by(certification_module_id=module.id):
        link.is_required = False
    lesson_ids = [row.id for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
    for link in db.query(LearningResourceLink).filter(LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids)):
        link.is_required = False
    for assessment in db.query(ModuleAssessment).filter_by(certification_module_id=module.id):
        assessment.active = False
    for prompt in db.query(InterviewPrompt).filter_by(certification_module_id=module.id):
        prompt.active = False
    db.commit()
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    response = {"matches": {"ram": "memory", "rj45": "ethernet", "usb-c": "reversible"}}
    url = _url("hardware-match") + "/submit"
    version_id = _version_id(client, student, _url("hardware-match"))
    first = client.post(url, json={"version_id": version_id, "response": response}, headers=auth_headers(student))
    assert first.status_code == 200
    requirement = db.query(V2EvidenceRequirement).filter_by(module_id=module.id, ref_key="interaction.pilot.hardware-match").one()
    record = db.query(V2EvidenceRecord).filter_by(student_id=student.id, requirement_id=requirement.id).one()
    assert record.source_ref == f"v2-interaction-attempt:{first.json()['data']['submission_result']['attempt_id']}"
    assert module_progress(db, student.id, MODULE)["module_complete"] is True
    second = client.post(url, json={"version_id": version_id, "response": response}, headers=auth_headers(student))
    assert second.status_code == 200
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id, requirement_id=requirement.id).count() == 1
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.hardware-match").count() == 2
    optional = db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.ethernet-port").count()
    assert optional == 0  # optional practice does not block mastery


@pytest.mark.parametrize("payload", [
    {"response": {"choice_id": "ethernet"}, "passed": True},
    {"response": {"choice_id": "ethernet"}, "score": 100},
    {"response": {"choice_id": "ethernet"}, "evidence_record": True},
    {"response": {"choice_id": "ethernet"}, "version": 1},
    {"response": {"choice_id": "ethernet", "passed": True}},
    {"response": {"choice_id": "ethernet", "correct_choice_id": "ethernet"}},
    {"response": {"choice_id": "ethernet", "attempt_id": 999}},
])
def test_forged_scores_evidence_version_and_attempt_fields_are_rejected(pilot, db, payload):
    student, client = pilot
    version_id = _version_id(client, student, _url("ethernet-port"))
    response = client.post(_url("ethernet-port") + "/submit", json={"version_id": version_id, **payload}, headers=auth_headers(student))
    assert response.status_code == 422
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id).count() == 0
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id).count() == 0


def test_wrong_module_unpublished_and_nonpilot_are_unavailable(pilot, db):
    student, client = pilot
    url = _url("ethernet-port")
    version_id = _version_id(client, student, url)
    wrong_module = url.replace(MODULE, "module.aplus.core1.network_services_troubleshooting")
    assert client.get(wrong_module, headers=auth_headers(student)).status_code == 404
    assert client.post(wrong_module + "/submit", json={"version_id": version_id, "response": {"choice_id": "ethernet"}}, headers=auth_headers(student)).status_code == 404
    row = db.query(V2InteractionDefinition).filter_by(interaction_key="interaction.pilot.ethernet-port").one()
    row.status = "retired"
    db.commit()
    assert client.get(url, headers=auth_headers(student)).status_code == 404
    assert client.post(url + "/submit", json={"version_id": version_id, "response": {"choice_id": "ethernet"}}, headers=auth_headers(student)).status_code == 404
    row.status = "draft"
    db.commit()
    assert client.get(url, headers=auth_headers(student)).status_code == 404
    assert client.post(url + "/submit", json={"version_id": version_id, "response": {"choice_id": "ethernet"}}, headers=auth_headers(student)).status_code == 404
    legacy = make_student(db, username="interaction_legacy")
    assert client.get(_url("hardware-match"), headers=auth_headers(legacy)).status_code == 404
    assert client.post(_url("hardware-match") + "/submit", json={"version_id": version_id, "response": {"matches": {}}}, headers=auth_headers(legacy)).status_code == 404


def test_old_attempt_survives_new_version_and_loader_rejects_mutation(pilot, db, tmp_path):
    student, client = pilot
    url = _url("ipconfig-command")
    version_id = _version_id(client, student, url)
    assert client.post(url + "/submit", json={"version_id": version_id, "response": {"answer": "ipconfig"}}, headers=auth_headers(student)).status_code == 200
    old = db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.ipconfig-command").one()
    snapshot = copy.deepcopy(old.definition_snapshot)
    manifest = yaml.safe_load(open(DEFAULT_PILOT_PATH, encoding="utf-8"))
    item = next(row for row in manifest["interactions"] if row["key"] == "interaction.pilot.ipconfig-command")
    item["version"] = 2
    item["config"]["accepted_answers"] = ["ipconfig /all"]
    item["title"] = "Recall the detailed Windows network command"
    path = tmp_path / "version2.yaml"
    path.write_text(yaml.safe_dump({"interactions": [item]}), encoding="utf-8")
    load_interactions(db, str(path), commit=True)
    assert db.get(V2InteractionAttempt, old.id).definition_snapshot == snapshot
    assert db.get(V2InteractionAttempt, old.id).version == 1
    assert db.query(V2InteractionDefinition).filter_by(interaction_key=item["key"], version=1).one().status == "retired"
    assert client.get(url, headers=auth_headers(student)).json()["data"]["interaction"]["version"] == 2
    new_version_id = _version_id(client, student, url)
    assert client.post(url + "/submit", json={"version_id": new_version_id, "response": {"answer": "ipconfig /all"}}, headers=auth_headers(student)).status_code == 200
    assert [row.version for row in db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key=item["key"]).order_by(V2InteractionAttempt.attempt_number)] == [1, 2]
    mutated = copy.deepcopy(item)
    mutated["config"]["accepted_answers"] = ["hostname"]
    path.write_text(yaml.safe_dump({"interactions": [mutated]}), encoding="utf-8")
    with pytest.raises(InteractionValidationError, match="author a new version"):
        load_interactions(db, str(path))


def test_submission_rejects_displayed_version_after_new_publication(pilot, db, tmp_path):
    student, client = pilot
    url = _url("ipconfig-command")
    shown = client.get(url, headers=auth_headers(student)).json()["data"]["interaction"]
    assert shown["version"] == 1
    manifest = yaml.safe_load(open(DEFAULT_PILOT_PATH, encoding="utf-8"))
    item = copy.deepcopy(next(row for row in manifest["interactions"] if row["key"] == shown["key"]))
    item["version"] = 2
    item["title"] = "Recall the detailed network command"
    item["config"]["accepted_answers"] = ["ipconfig /all"]
    path = tmp_path / "new-version.yaml"
    path.write_text(yaml.safe_dump({"interactions": [item]}), encoding="utf-8")
    load_interactions(db, str(path), commit=True)

    stale = client.post(url + "/submit", json={
        "version_id": shown["version_id"], "response": {"answer": "ipconfig"},
    }, headers=auth_headers(student))
    assert stale.status_code == 409
    assert "Reload" in stale.json()["detail"]
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key=shown["key"]).count() == 0

    current = client.get(url, headers=auth_headers(student)).json()["data"]["interaction"]
    assert current["version"] == 2
    assert current["version_id"] != shown["version_id"]
    graded = client.post(url + "/submit", json={
        "version_id": current["version_id"], "response": {"answer": "ipconfig /all"},
    }, headers=auth_headers(student))
    assert graded.status_code == 200
    attempt = db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key=shown["key"]).one()
    assert attempt.definition_id == current["version_id"]
    assert attempt.version == attempt.definition_snapshot["version"] == 2
    assert attempt.definition_snapshot["title"] == item["title"]
    assert attempt.definition_snapshot["config"]["accepted_answers"] == ["ipconfig /all"]
    assert attempt.response_snapshot == {"answer": "ipconfig /all"}


def test_version_binding_cannot_target_other_or_unpublished_interaction(pilot, db):
    student, client = pilot
    url = _url("ethernet-port")
    shown_id = _version_id(client, student, url)
    other_id = _version_id(client, student, _url("ipconfig-command"))
    payload = {"response": {"choice_id": "ethernet"}}
    assert client.post(url + "/submit", json={**payload, "version_id": other_id}, headers=auth_headers(student)).status_code == 409

    published = db.get(V2InteractionDefinition, shown_id)
    draft = V2InteractionDefinition(
        interaction_key=published.interaction_key, version=2,
        interaction_type=published.interaction_type, module_id=published.module_id,
        lesson_id=published.lesson_id, title="Hidden draft", instructions="Not visible",
        config=published.config, status="draft", required=False,
    )
    db.add(draft)
    db.commit()
    assert client.post(url + "/submit", json={**payload, "version_id": draft.id}, headers=auth_headers(student)).status_code == 409
    assert client.post(url + "/submit", json=payload, headers=auth_headers(student)).status_code == 422
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key=published.interaction_key).count() == 0
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id).count() == 0


def test_old_optional_pass_does_not_satisfy_new_required_version(pilot, db, tmp_path):
    student, client = pilot
    url = _url("ethernet-port")
    original_id = _version_id(client, student, url)
    old_pass = client.post(url + "/submit", json={
        "version_id": original_id, "response": {"choice_id": "ethernet"},
    }, headers=auth_headers(student))
    assert old_pass.status_code == 200
    assert old_pass.json()["data"]["progress"]["passed"] is True
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id).count() == 0

    manifest = yaml.safe_load(open(DEFAULT_PILOT_PATH, encoding="utf-8"))
    item = copy.deepcopy(next(row for row in manifest["interactions"] if row["key"] == "interaction.pilot.ethernet-port"))
    item["version"] = 2
    item["required"] = True
    item["title"] = "Required port identification"
    path = tmp_path / "required-version.yaml"
    path.write_text(yaml.safe_dump({"interactions": [item]}), encoding="utf-8")
    load_interactions(db, str(path), commit=True)

    current = client.get(url, headers=auth_headers(student)).json()["data"]
    assert current["interaction"]["version"] == 2
    assert current["progress"]["attempt_count"] == 1
    assert current["progress"]["best_score"] == 100
    assert current["progress"]["passed"] is False
    assert current["progress"]["status"] == "in_progress"
    module = client.get(f"{ROOT}/{MODULE}", headers=auth_headers(student)).json()["data"]
    listed = next(row for row in module["interactions"] if row["interaction"]["key"] == item["key"])
    assert listed["progress"]["passed"] is False

    new_pass = client.post(url + "/submit", json={
        "version_id": current["interaction"]["version_id"], "response": {"choice_id": "ethernet"},
    }, headers=auth_headers(student))
    assert new_pass.status_code == 200
    assert new_pass.json()["data"]["progress"]["passed"] is True
    assert new_pass.json()["data"]["progress"]["attempt_count"] == 2
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id).count() == 1


def test_hidden_lesson_does_not_leave_unreachable_required_interaction(pilot, db):
    student, client = pilot
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    lesson = db.query(LessonV2Meta).filter_by(
        certification_module_id=module.id,
        lesson_key="lesson.aplus.core1.ip_configuration.ipv4_basics",
    ).one()
    lesson_ids = [row.id for row in db.query(LessonV2Meta).filter_by(certification_module_id=module.id)]
    for link in db.query(LearningResourceLink).filter(
        (LearningResourceLink.certification_module_id == module.id)
        | (LearningResourceLink.lesson_v2_meta_id.in_(lesson_ids))
    ):
        link.is_required = False
    assessment = db.query(ModuleAssessment).filter_by(certification_module_id=module.id, assessment_role="module_quiz").first()
    for row in db.query(ModuleAssessment).filter_by(certification_module_id=module.id):
        row.active = row.id == assessment.id
    for prompt in db.query(InterviewPrompt).filter_by(certification_module_id=module.id):
        prompt.active = False
    db.commit()
    record_activity(
        db, student_id=student.id, module_key=MODULE,
        activity_type="module_quiz", ref_key=assessment.assessment_key,
        status="passed", passed=True, commit=True,
    )
    assert module_progress(db, student.id, MODULE)["module_complete"] is False
    lesson.status = "draft"
    db.commit()
    assert client.get(_url("hardware-match"), headers=auth_headers(student)).status_code == 404
    hidden = module_progress(db, student.id, MODULE)
    assert hidden["module_complete"] is True
    assert hidden["evidence"]["interaction_completed"] is False
    lesson.status = "ready"
    db.commit()
    assert module_progress(db, student.id, MODULE)["module_complete"] is False


def test_110_retries_keep_immutable_history_but_progress_is_bounded(pilot, db):
    student, client = pilot
    url = _url("ethernet-port")
    version_id = _version_id(client, student, url)
    headers = auth_headers(student)
    small_size = None
    module_url = f"{ROOT}/{MODULE}"
    lesson_url = f"{ROOT}/{MODULE}/lessons/lesson.aplus.core1.ip_configuration.ipv4_basics"
    module_small_size = lesson_small_size = None
    for number in range(1, 111):
        choice = "ethernet" if number == 50 else "hdmi"
        result = client.post(url + "/submit", json={
            "version_id": version_id, "response": {"choice_id": choice},
        }, headers=headers)
        assert result.status_code == 200
        if number == 10:
            small_size = len(result.content)
            module_small_size = len(client.get(module_url, headers=headers).content)
            lesson_small_size = len(client.get(lesson_url, headers=headers).content)
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.ethernet-port").count() == 110
    first = db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.ethernet-port", attempt_number=1).one()
    passing = db.query(V2InteractionAttempt).filter_by(student_id=student.id, interaction_key="interaction.pilot.ethernet-port", attempt_number=50).one()
    assert first.response_snapshot == {"choice_id": "hdmi"} and first.passed is False
    assert passing.response_snapshot == {"choice_id": "ethernet"} and passing.passed is True
    detail = client.get(url, headers=headers)
    progress = detail.json()["data"]["progress"]
    assert progress["attempt_count"] == 110
    assert progress["passed"] is True
    assert progress["status"] == "passed"
    assert progress["best_score"] == 100
    assert progress["best_result"]["passed"] is True
    assert progress["latest_result"]["passed"] is False
    assert progress["latest_attempt_at"] is not None
    assert [row["attempt_number"] for row in progress["recent_attempts"]] == [110, 109, 108, 107, 106]
    assert len(detail.content) < small_size + 1000

    module = client.get(module_url, headers=headers)
    lesson = client.get(lesson_url, headers=headers)
    assert module.status_code == lesson.status_code == 200
    assert len(module.content) < module_small_size + 1000
    assert len(lesson.content) < lesson_small_size + 1000
    for view in (module.json()["data"], lesson.json()["data"]):
        item = next(row for row in view["interactions"] if row["interaction"]["key"] == "interaction.pilot.ethernet-port")
        assert item["progress"]["attempt_count"] == 110
        assert "recent_attempts" not in item["progress"]

    statements = []
    def track_attempt_query(_connection, _cursor, statement, _parameters, _context, _executemany):
        if "v2_interaction_attempts" in statement.lower():
            statements.append(statement)
    event.listen(db.get_bind(), "before_cursor_execute", track_attempt_query)
    try:
        listed = interaction_list(db, student.id, MODULE)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", track_attempt_query)
    assert len(listed) == 6
    assert len(statements) == 1


def test_draft_version_preserves_published_requirement_and_key_stays_in_module(pilot, db, tmp_path):
    student, client = pilot
    manifest = yaml.safe_load(open(DEFAULT_PILOT_PATH, encoding="utf-8"))
    item = copy.deepcopy(next(row for row in manifest["interactions"] if row["key"] == "interaction.pilot.hardware-match"))
    item["version"] = 2
    item["status"] = "draft"
    item["title"] = "Draft hardware matching revision"
    path = tmp_path / "draft.yaml"
    path.write_text(yaml.safe_dump({"interactions": [item]}), encoding="utf-8")
    load_interactions(db, str(path), commit=True)
    module = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    requirement = db.query(V2EvidenceRequirement).filter_by(module_id=module.id, ref_key=item["key"]).one()
    assert requirement.active is True
    assert requirement.is_required is True
    assert client.get(_url("hardware-match"), headers=auth_headers(student)).json()["data"]["interaction"]["version"] == 1
    db.add(CertificationModule(
        certification_version_id=module.certification_version_id,
        module_key="module.test.other", title="Other test module", active=True,
    ))
    db.commit()
    moved = copy.deepcopy(item)
    moved["version"] = 3
    moved["module_key"] = "module.test.other"
    path.write_text(yaml.safe_dump({"interactions": [moved]}), encoding="utf-8")
    with pytest.raises(InteractionValidationError, match="cannot move to another module"):
        load_interactions(db, str(path))


@pytest.mark.parametrize("change", [
    {"type": "matching", "config": {"pairs": [{"id": "one", "left": "One", "right_id": "same", "right": "A"}, {"id": "two", "left": "Two", "right_id": "same", "right": "B"}], "explanation": "x"}},
    {"type": "ordering", "config": {"steps": [{"id": "same", "text": "First"}, {"id": "same", "text": "Second"}], "explanation": "x"}},
    {"type": "typed_answer", "config": {"question": "Type it", "accepted_answers": [], "explanation": "x"}},
    {"type": "typed_answer", "config": {"question": "Type it", "accepted_answers": ["x" * 501], "explanation": "x"}},
    {"type": "image_identification", "config": {"image_url": "https://random.test/a.png", "image_alt": "Port", "question": "Which?", "choices": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "correct_choice_id": "a", "explanation": "x"}},
    {"type": "command_output", "config": {"command": "ipconfig", "output": "", "question": "What?", "choices": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "correct_choice_id": "a", "explanation": "x"}},
    {"type": "safe_action", "config": {"scenario": "What next?", "choices": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "correct_choice_id": "missing", "explanation": "x"}},
])
def test_invalid_authoring_fails_before_publication(change):
    doc = {"key": "interaction.invalid", "version": 1, "module_key": MODULE, "title": "Bad", "instructions": "Try", **change}
    with pytest.raises(InteractionValidationError):
        validate_definition(doc)


def test_student_deletion_removes_attempts_and_evidence_but_keeps_definition(pilot, db):
    student, client = pilot
    response = {"matches": {"ram": "memory", "rj45": "ethernet", "usb-c": "reversible"}}
    version_id = _version_id(client, student, _url("hardware-match"))
    assert client.post(_url("hardware-match") + "/submit", json={"version_id": version_id, "response": response}, headers=auth_headers(student)).status_code == 200
    definition_id = db.query(V2InteractionDefinition).filter_by(interaction_key="interaction.pilot.hardware-match").one().id
    assert student_owned_row_counts(db, student.id)["v2_interaction_attempts"] == 1
    delete_student_owned_data(db, student.id)
    db.delete(db.get(Student, student.id))
    db.commit()
    assert db.query(V2InteractionAttempt).filter_by(student_id=student.id).count() == 0
    assert db.query(V2EvidenceRecord).filter_by(student_id=student.id).count() == 0
    assert db.get(V2InteractionDefinition, definition_id) is not None
