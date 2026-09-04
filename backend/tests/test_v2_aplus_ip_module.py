"""Nexus V2 Phase 2A — the first end-to-end A+ curriculum MVP module:
``module.aplus.core1.ip_configuration`` ("IP Configuration & Basic
Connectivity Troubleshooting").

Covers the Phase 2A verification matrix: idempotent load, Markdown lessons,
resource mapping, objective mapping (no invented codes), question import,
module-quiz wiring, short-answer + free-response grading, practical + Service
Desk mapping, student-progress recording, mentor weakness data, the
data-driven maintenance proofs, and the guarantee that no legacy progression
table or existing student is touched.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import auth_headers, enroll_v2, make_client, make_student

from app.models.certification import (
    CertificationModule,
    CertificationObjective,
    LearningResource,
    LearningResourceLink,
    LessonObjective,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
)
from app.models.lab import LabTemplate
from app.models.quiz import Question, Quiz
from app.models.student import Student
from app.models.training import TrainingWeek
from app.models.v2_progress import V2ModuleActivity
from app.services.deterministic_grader import grade_free_response, grade_short_answer
from app.services.objective_coverage import certification_version_coverage
from app.services.v2_content_loader import (
    DEFAULT_QUESTIONS_DIR,
    load_all,
    load_content,
    load_module,
    load_question_banks,
)
from app.services.v2_mentor_service import module_report
from app.services.v2_progress_service import module_progress, record_activity

MODULE_KEY = "module.aplus.core1.ip_configuration"
VERSION_KEY = "comptia_aplus_220-1201"
QUIZ_TITLE = "A+ IP Configuration & Basic Connectivity — Module Bank"
LAB_TITLE = "A+ Practical — Inspect Windows IP Configuration"
LESSON_KEYS = [
    "lesson.aplus.core1.ip_configuration.ipv4_basics",
    "lesson.aplus.core1.ip_configuration.dhcp_and_apipa",
    "lesson.aplus.core1.ip_configuration.default_gateway",
    "lesson.aplus.core1.ip_configuration.dns_basics",
    "lesson.aplus.core1.ip_configuration.windows_commands",
]
# Objectives this module intentionally maps to. All exist in
# content/objectives/comptia-a-plus-220-1201.yaml.
MODULE_OBJECTIVES = {"2.5", "5.7", "5.1"}


@pytest.fixture()
def loaded(db):
    """Full V2 load in ONE call — hierarchy, objectives, lessons, question
    banks, labs, resources, prompts, and reconverged module-assessment refs."""
    load_module(db, commit=True)
    return db


def _module(db) -> CertificationModule:
    return (
        db.query(CertificationModule)
        .filter(CertificationModule.module_key == MODULE_KEY)
        .one()
    )


# --------------------------------------------------------------------------- #
# Load + structure
# --------------------------------------------------------------------------- #

def test_module_and_lessons_created(loaded):
    module = _module(loaded)
    assert module.title == "IP Configuration & Basic Connectivity Troubleshooting"
    metas = (
        loaded.query(LessonV2Meta)
        .filter(LessonV2Meta.certification_module_id == module.id)
        .all()
    )
    assert {m.lesson_key for m in metas} == set(LESSON_KEYS)
    # Every lesson stored its Markdown body + a content hash.
    for meta in metas:
        assert meta.content_body and "## 1. What is this?" in meta.content_body
        assert meta.content_hash
        assert meta.importance == "job_critical"
        assert meta.learning_relationship == "new"


def test_load_is_idempotent(db):
    load_all(db)
    c1 = load_content(db)
    load_all(db)
    a3 = load_all(db)
    c3 = load_content(db)
    # Hierarchy fully stable after the first resolving pass.
    assert a3["created"] == 0 and a3["updated"] == 0
    # Nothing re-created or changed on a clean rerun — questions included, now
    # that the importer detects unchanged rows.
    assert c3["created"] == 0 and c3["updated"] == 0
    for entity in ("lesson", "resource", "resource_link", "interview_prompt", "lab_template", "question"):
        assert c3["by_entity"].get(entity, {}).get("created", 0) == 0
        assert c3["by_entity"].get(entity, {}).get("updated", 0) == 0
    assert c3["by_entity"]["question"]["unchanged"] == 500
    assert db.query(Question).filter(Question.quiz_id == _quiz_id(db)).count() == 40
    assert c1["by_entity"]["question"]["created"] == 500


def _quiz_id(db) -> int:
    return db.query(Quiz).filter(Quiz.title == QUIZ_TITLE).one().id


def test_load_module_is_one_call_and_resolves_all_refs(db):
    """A curriculum author loads the whole module with one call and every
    engine reference this loader is responsible for resolves — no manual
    two-pass sequence."""
    out = load_module(db, commit=True)
    # This module's quick_check / module_quiz / practical refs all resolved.
    unresolved = out["references"]["content_engine_unresolved"]
    assert not [k for k in unresolved if k.startswith("assess.aplus.ipcfg.")]
    mq = db.query(ModuleAssessment).filter(
        ModuleAssessment.assessment_key == "assess.aplus.ipcfg.module_quiz"
    ).one()
    assert mq.quiz_id is not None
    practical = db.query(ModuleAssessment).filter(
        ModuleAssessment.assessment_key == "assess.aplus.ipcfg.practical"
    ).one()
    assert practical.lab_template_id is not None
    # A second call changes nothing.
    again = load_module(db, commit=True)
    assert again["created"] == 0 and again["updated"] == 0


def test_question_sync_detects_real_changes(db, tmp_path):
    """The importer reports created → unchanged → updated correctly and never
    creates a duplicate row for an unchanged or edited question."""
    from app.services.question_importer import confirm_import, parse_csv_file

    load_all(db)
    src = Path(DEFAULT_QUESTIONS_DIR, "aplus-ip-configuration.csv")
    rows = parse_csv_file(src.read_bytes())

    r1 = confirm_import(db, rows, duplicate_policy="update_draft", source_filename="x.csv")
    assert r1["created"] == 40 and r1["updated"] == 0 and r1["unchanged"] == 0
    quiz_id = _quiz_id(db)
    assert db.query(Question).filter(Question.quiz_id == quiz_id).count() == 40

    # Re-import the identical rows: everything unchanged, nothing re-stamped.
    stamp_before = {
        q.id: q.imported_at
        for q in db.query(Question).filter(Question.quiz_id == quiz_id)
    }
    r2 = confirm_import(db, rows, duplicate_policy="update_draft", source_filename="x.csv")
    assert r2["created"] == 0 and r2["updated"] == 0 and r2["unchanged"] == 40
    stamp_after = {
        q.id: q.imported_at
        for q in db.query(Question).filter(Question.quiz_id == quiz_id)
    }
    assert stamp_before == stamp_after  # no provenance churn on a no-op

    # Edit one explanation -> exactly one 'updated', still 40 rows.
    edited = [dict(r) for r in rows]
    target_text = "What does DNS do?"
    hit = next(r for r in edited if r["question_text"] == target_text)
    hit["explanation"] = "DNS maps names to IP addresses; edited for the change-detection test."
    r3 = confirm_import(db, edited, duplicate_policy="update_draft", source_filename="x.csv")
    assert r3["created"] == 0 and r3["updated"] == 1 and r3["unchanged"] == 39
    assert db.query(Question).filter(Question.quiz_id == quiz_id).count() == 40

    # Edit only the objective metadata of one row -> 'updated' via the V2-meta
    # path. Build on the previous edit so only this one row is newly different.
    edited2 = [dict(r) for r in edited]
    hit2 = next(r for r in edited2 if r["question_text"] == "What is the role of the default gateway?")
    assert hit2["objective_code"] == "2.5"
    hit2["objective_code"] = "5.7"
    r4 = confirm_import(db, edited2, duplicate_policy="update_draft", source_filename="x.csv")
    assert r4["updated"] == 1 and r4["unchanged"] == 39 and r4["created"] == 0
    changed = db.query(Question).filter(Question.question_text == "What is the role of the default gateway?").one()
    assert changed.v2_meta.objective_code == "5.7"

    # Add a brand-new row -> exactly one 'created', the rest unchanged.
    plus = [dict(r) for r in edited2]
    new = {k: "" for k in plus[0].keys()}
    new.update(
        quiz_title=QUIZ_TITLE, question_type="single",
        question_text="Change-detection probe: which command renews a DHCP lease?",
        option_a="ipconfig /release", option_b="ipconfig /renew",
        option_c="ping", option_d="nslookup",
        correct_answers="B", explanation="ipconfig /renew requests a new lease.",
        difficulty="1", tags="dhcp", source="Nexus curriculum team", published="false",
        certification="comptia_aplus", certification_version=VERSION_KEY, domain="2.0",
        module=MODULE_KEY, objective_code="5.7", importance="job_critical",
        source_name="Nexus curriculum team", permission_status="owned",
    )
    plus.append(new)
    r5 = confirm_import(db, plus, duplicate_policy="update_draft", source_filename="x.csv")
    assert r5["created"] == 1 and r5["updated"] == 0 and r5["unchanged"] == 40
    assert db.query(Question).filter(Question.quiz_id == quiz_id).count() == 41

    # No duplicate fingerprints anywhere in the bank.
    fps = [f for (f,) in db.query(Question.fingerprint).filter(Question.quiz_id == quiz_id)]
    assert len(fps) == len(set(fps))


def test_bank_has_no_duplicate_fingerprints(loaded):
    quiz_id = _quiz_id(loaded)
    fps = [f for (f,) in loaded.query(Question.fingerprint).filter(Question.quiz_id == quiz_id)]
    assert len(fps) == 40
    assert len(set(fps)) == 40


def test_legacy_derived_questions_carry_provenance(loaded):
    """Questions adapted from seeded Nexus quizzes name their origin and keep
    an accurate permission state (owned — they are Nexus-authored seeds)."""
    reused = (
        loaded.query(QuestionV2Meta)
        .join(Question, Question.id == QuestionV2Meta.question_id)
        .filter(
            Question.quiz_id == _quiz_id(loaded),
            QuestionV2Meta.source_name.like("%adapted from seed%"),
        )
        .all()
    )
    assert len(reused) == 6
    for m in reused:
        assert "nexus-authored:" in m.source_name
        assert m.permission_status == "owned"
        assert m.objective_code in MODULE_OBJECTIVES
        assert m.module == MODULE_KEY


def test_resources_map_to_lessons_and_module(loaded):
    module = _module(loaded)
    meta_ids = {
        m.id
        for m in loaded.query(LessonV2Meta).filter(
            LessonV2Meta.certification_module_id == module.id
        )
    }
    links = (
        loaded.query(LearningResourceLink)
        .join(LearningResource, LearningResource.id == LearningResourceLink.resource_id)
        .filter(LearningResource.resource_key.like("res.aplus.ipcfg.%"))
        .all()
    )
    assert links, "expected ip_configuration resources to be linked"
    lesson_linked = [ln for ln in links if ln.lesson_v2_meta_id in meta_ids]
    module_linked = [ln for ln in links if ln.certification_module_id == module.id]
    assert lesson_linked and module_linked
    # Every ipcfg resource is permitted (linked, not rehosted).
    for r in loaded.query(LearningResource).filter(
        LearningResource.resource_key.like("res.aplus.ipcfg.%")
    ):
        assert r.permission_status == "permitted"
        assert r.url and r.provider


# --------------------------------------------------------------------------- #
# Objective mapping
# --------------------------------------------------------------------------- #

def test_lesson_objectives_use_only_real_codes(loaded):
    module = _module(loaded)
    rows = (
        loaded.query(CertificationObjective.objective_code)
        .join(LessonObjective, LessonObjective.objective_id == CertificationObjective.id)
        .join(LessonV2Meta, LessonV2Meta.id == LessonObjective.lesson_v2_meta_id)
        .filter(LessonV2Meta.certification_module_id == module.id)
        .all()
    )
    codes = {c for (c,) in rows}
    assert codes == MODULE_OBJECTIVES
    # All map inside the module's own certification version.
    real = {
        c
        for (c,) in loaded.query(CertificationObjective.objective_code)
        .join(
            CertificationModule,
            CertificationModule.certification_version_id
            == CertificationObjective.certification_version_id,
        )
        .filter(CertificationModule.module_key == MODULE_KEY)
    }
    assert MODULE_OBJECTIVES <= real


def test_objective_coverage_includes_completed_core1_catalog(loaded):
    cov = certification_version_coverage(loaded, VERSION_KEY)
    covered = {c["objective_code"] for c in cov["covered"]}
    # This module's three objectives are covered...
    assert MODULE_OBJECTIVES <= covered
    # Module 10 closes the remaining Core 1 lesson coverage.
    assert {c["objective_code"] for c in cov["uncovered"]} == set()
    assert cov["coverage_percent"] == 100


# --------------------------------------------------------------------------- #
# Question bank
# --------------------------------------------------------------------------- #

def test_question_bank_breakdown(loaded):
    quiz = loaded.query(Quiz).filter(Quiz.title == QUIZ_TITLE).one()
    metas = (
        loaded.query(QuestionV2Meta)
        .join(Question, Question.id == QuestionV2Meta.question_id)
        .filter(Question.quiz_id == quiz.id)
        .all()
    )
    assert len(metas) == 40
    by_type: dict[str, int] = {}
    for m in metas:
        by_type[m.question_type or "mcq"] = by_type.get(m.question_type or "mcq", 0) + 1
    assert by_type["short_answer"] >= 5
    assert by_type["free_response"] >= 2
    # Every question carries the full V2 metadata set.
    for m in metas:
        assert m.certification == "comptia_aplus"
        assert m.certification_version == VERSION_KEY
        assert m.domain == "2.0"
        assert m.module == MODULE_KEY
        assert m.objective_code in MODULE_OBJECTIVES
        assert m.importance in {"job_critical", "working_knowledge", "awareness"}
        assert m.permission_status == "owned"
    # The quiz is a draft, invisible to students until a mentor validates it.
    assert quiz.status == "draft"
    assert quiz.answer_keys_validated is False
    assert quiz.show_in_practice_library is False


def test_module_quiz_and_quick_checks_wired(loaded):
    module = _module(loaded)
    quiz_id = loaded.query(Quiz).filter(Quiz.title == QUIZ_TITLE).one().id
    mq = loaded.query(ModuleAssessment).filter(
        ModuleAssessment.assessment_key == "assess.aplus.ipcfg.module_quiz"
    ).one()
    assert mq.assessment_role == "module_quiz"
    assert mq.quiz_id == quiz_id
    assert mq.displayed_count == 12
    assert mq.pass_percent == 70
    # 5 quick checks, each bound to its lesson and the same bank.
    qcs = loaded.query(ModuleAssessment).filter(
        ModuleAssessment.certification_module_id == module.id,
        ModuleAssessment.assessment_role == "quick_check",
    ).all()
    assert len(qcs) == 5
    for qc in qcs:
        assert qc.quiz_id == quiz_id
        assert qc.lesson_v2_meta_id is not None
        assert 3 <= qc.displayed_count <= 5


def test_practical_and_service_desk_mapping(loaded):
    practical = loaded.query(ModuleAssessment).filter(
        ModuleAssessment.assessment_key == "assess.aplus.ipcfg.practical"
    ).one()
    lab = loaded.query(LabTemplate).filter(LabTemplate.title == LAB_TITLE).one()
    assert practical.lab_template_id == lab.id
    assert lab.lab_type == "guided"
    assert lab.proxmox_template_vmid is None  # no VM provisioned in 2A
    assert "diagnostic_questions" in lab.success_criteria

    sd = loaded.query(ModuleAssessment).filter(
        ModuleAssessment.assessment_key == "assess.aplus.ipcfg.service_desk"
    ).one()
    assert sd.assessment_role == "service_desk"
    assert sd.title  # row exists and is visible even though inc2503 isn't seeded here
    assert sd.service_desk_scenario_id is None


# --------------------------------------------------------------------------- #
# Grading (Phase 1B deterministic, Phase 1C pending path)
# --------------------------------------------------------------------------- #

def test_short_answer_grading_from_stored_metadata(loaded):
    meta = (
        loaded.query(QuestionV2Meta)
        .filter(QuestionV2Meta.question_type == "short_answer")
        .join(Question, Question.id == QuestionV2Meta.question_id)
        .filter(Question.question_text.like("%displays the computer's current IPv4%"))
        .one()
    )
    assert "ipconfig" in meta.acceptable_answers
    ok = grade_short_answer("ipconfig", meta.acceptable_answers, match_mode=meta.answer_match_mode)
    assert ok["status"] == "graded" and ok["passed"] is True
    # Case / spacing tolerance.
    assert grade_short_answer("  IPConfig ", meta.acceptable_answers)["passed"] is True
    # A confidently wrong short answer.
    assert grade_short_answer("nslookup", meta.acceptable_answers)["passed"] is False


def test_free_response_pending_path(loaded):
    meta = (
        loaded.query(QuestionV2Meta)
        .filter(QuestionV2Meta.question_type == "free_response")
        .join(Question, Question.id == QuestionV2Meta.question_id)
        .filter(Question.question_text.like("%169.254.x.x address%"))
        .one()
    )
    assert meta.rubric_version == "ipcfg-2026-08-a"
    # A vague answer the deterministic grader must NOT confidently pass/fail.
    vague = grade_free_response(
        "I think the network is broken and I would reboot the computer.",
        meta.expected_concepts,
        rubric=meta.rubric,
        rubric_version=meta.rubric_version,
        min_concepts_for_pass=meta.min_concepts_for_pass,
        partial_credit=meta.partial_credit,
    )
    assert vague["status"] == "needs_review"
    # A thorough answer clears the concept threshold deterministically.
    strong = grade_free_response(
        "That is an APIPA address, which means the PC got no DHCP reply. I would "
        "check the network connection and link light, run ipconfig /release and "
        "ipconfig /renew, then compare a working neighbour to decide if the "
        "switch port or the DHCP server is at fault, and finally verify the PC "
        "gets a real address and can reach the gateway.",
        meta.expected_concepts,
        rubric=meta.rubric,
        rubric_version=meta.rubric_version,
        min_concepts_for_pass=meta.min_concepts_for_pass,
        partial_credit=meta.partial_credit,
    )
    assert strong["status"] == "graded" and strong["passed"] is True


# --------------------------------------------------------------------------- #
# Student progress + mentor data
# --------------------------------------------------------------------------- #

def test_progress_and_mentor_report(loaded):
    student = make_student(loaded, username="ip_dev_student")
    for key in LESSON_KEYS:
        record_activity(
            loaded, student_id=student.id, module_key=MODULE_KEY,
            activity_type="lesson", ref_key=key, status="completed",
        )
    # Resource completion (where supported).
    res_key = (
        loaded.query(LearningResource.resource_key)
        .filter(LearningResource.resource_key.like("res.aplus.ipcfg.%"))
        .first()[0]
    )
    record_activity(
        loaded, student_id=student.id, module_key=MODULE_KEY,
        activity_type="resource", ref_key=res_key, status="completed",
    )
    q_ids = [
        qid
        for (qid,) in loaded.query(Question.id)
        .join(QuestionV2Meta, QuestionV2Meta.question_id == Question.id)
        .filter(QuestionV2Meta.objective_code == "5.7")
        .limit(2)
    ]
    record_activity(
        loaded, student_id=student.id, module_key=MODULE_KEY,
        activity_type="module_quiz", ref_key="assess.aplus.ipcfg.module_quiz",
        status="failed", score=58, passed=False,
        detail={"missed_question_ids": q_ids},
    )
    record_activity(
        loaded, student_id=student.id, module_key=MODULE_KEY,
        activity_type="practical", ref_key="assess.aplus.ipcfg.practical",
        status="completed", passed=True,
    )
    record_activity(
        loaded, student_id=student.id, module_key=MODULE_KEY,
        activity_type="explain", ref_key="interview.aplus.ipcfg.what_does_dhcp_do",
        status="needs_review", detail={"rubric_version": "ipcfg-2026-08-a"},
    )
    loaded.commit()

    prog = module_progress(loaded, student.id, MODULE_KEY)
    # The IP lesson package remains draft and therefore is not student-visible.
    assert prog["lessons"] == {"total": 0, "completed": 0, "items": []}
    assert prog["resources"]["completed"] == 0
    assert prog["module_quiz"]["activity"]["score"] == 58
    assert prog["module_complete"] is False  # quiz not passed

    report = module_report(loaded, student.id, MODULE_KEY)
    assert report["module_quiz"]["passed"] is False
    assert {m["question_id"] for m in report["missed_questions"]} == set(q_ids)
    assert report["weak_objectives"][0]["objective_code"] == "5.7"
    assert report["weak_objectives"][0]["missed_count"] == 2
    assert report["weak_objectives"][0]["objective_text"]
    assert any(e["status"] == "needs_review" for e in report["explain_state"])
    assert report["practical"]["activity"]["status"] == "completed"


def test_upsert_activity_is_idempotent(loaded):
    student = make_student(loaded, username="ip_upsert")
    for _ in range(3):
        record_activity(
            loaded, student_id=student.id, module_key=MODULE_KEY,
            activity_type="lesson", ref_key=LESSON_KEYS[0], status="completed",
        )
    loaded.commit()
    rows = loaded.query(V2ModuleActivity).filter(
        V2ModuleActivity.student_id == student.id
    ).all()
    assert len(rows) == 1


# --------------------------------------------------------------------------- #
# No legacy / production side effects
# --------------------------------------------------------------------------- #

def test_loaders_touch_no_legacy_progression_or_students(db):
    load_all(db)
    load_content(db)
    load_all(db)
    db.commit()
    assert db.query(TrainingWeek).count() == 0
    assert db.query(Student).count() == 0  # no student created or migrated


def test_module_quiz_not_wired_to_trainingweek(loaded):
    quiz = loaded.query(Quiz).filter(Quiz.title == QUIZ_TITLE).one()
    assert quiz.week_number == 0  # not attached to any TrainingWeek
    assert quiz.quiz_purpose == "practice"


# --------------------------------------------------------------------------- #
# Data-driven maintenance proofs (no Python change required)
# --------------------------------------------------------------------------- #

def test_editing_markdown_updates_lesson(loaded, tmp_path):
    src = Path(
        "content/curriculum/comptia-a-plus/220-1201/ip-configuration"
    )
    dst = tmp_path / "curriculum"
    shutil.copytree(src.parents[3] / "curriculum", dst)
    target = (
        dst / "comptia-a-plus/220-1201/ip-configuration/01-ipv4-configuration-basics.md"
    )
    before = loaded.query(LessonV2Meta).filter(
        LessonV2Meta.lesson_key == LESSON_KEYS[0]
    ).one().content_hash

    text = target.read_text(encoding="utf-8")
    target.write_text(text + "\n\nAn extra clarifying sentence for maintenance.\n", encoding="utf-8")

    load_content(loaded, curriculum_dir=str(dst))
    loaded.commit()
    after = loaded.query(LessonV2Meta).filter(
        LessonV2Meta.lesson_key == LESSON_KEYS[0]
    ).one().content_hash
    assert after != before


def test_editing_resource_yaml_updates_resource(loaded, tmp_path):
    res_dir = tmp_path / "resources"
    res_dir.mkdir()
    src = Path("content/resources/comptia-a-plus.yaml")
    new_title = "Professor Messer — IPv4 and IPv6 (edited for test)"
    text = src.read_text(encoding="utf-8").replace(
        "Professor Messer — IPv4 and IPv6 (220-1201)", new_title
    )
    (res_dir / "comptia-a-plus.yaml").write_text(text, encoding="utf-8")

    from app.services.v2_content_loader import load_resources

    load_resources(loaded, str(res_dir / "comptia-a-plus.yaml"))
    loaded.commit()
    row = loaded.query(LearningResource).filter(
        LearningResource.resource_key == "res.aplus.ipcfg.messer.ipv4_ipv6"
    ).one()
    assert row.title == new_title


def test_adding_and_updating_a_question_via_csv(loaded, tmp_path):
    quiz_id = loaded.query(Quiz).filter(Quiz.title == QUIZ_TITLE).one().id
    before = loaded.query(Question).filter(Question.quiz_id == quiz_id).count()

    header = Path(DEFAULT_QUESTIONS_DIR, "aplus-ip-configuration.csv").read_text(
        encoding="utf-8"
    ).splitlines()[0]
    new_row = (
        f'{QUIZ_TITLE},single,"A brand-new maintenance question: which command '
        f'renews a DHCP lease?",ipconfig /release,ipconfig /renew,ping,nslookup,'
        f',,,,B,"ipconfig /renew requests a fresh lease.",1,"dhcp,maintenance",'
        f'Nexus curriculum team,false,comptia_aplus,{VERSION_KEY},2.0,{MODULE_KEY},'
        f'5.7,job_critical,Nexus curriculum team,,owned,,,,,,,'
    )
    qdir = tmp_path / "questions"
    qdir.mkdir()
    (qdir / "extra.csv").write_text(header + "\n" + new_row + "\n", encoding="utf-8")

    load_question_banks(loaded, str(qdir))
    loaded.commit()
    after = loaded.query(Question).filter(Question.quiz_id == quiz_id).count()
    assert after == before + 1
    added = (
        loaded.query(Question)
        .filter(Question.question_text.like("A brand-new maintenance question%"))
        .one()
    )
    assert added.explanation == "ipconfig /renew requests a fresh lease."

    # Re-running the unchanged CSV is a no-op (reported as unchanged).
    from app.services.v2_content_loader import LoadSummary

    noop = LoadSummary()
    load_question_banks(loaded, str(qdir), summary=noop)
    loaded.commit()
    assert noop.by_entity["question"]["updated"] == 0
    assert noop.by_entity["question"]["unchanged"] == 1

    # Update the same question's explanation via CSV — no code change, one update.
    updated_row = new_row.replace(
        "ipconfig /renew requests a fresh lease.",
        "Use ipconfig /renew to request a new DHCP lease without a reboot.",
    )
    (qdir / "extra.csv").write_text(header + "\n" + updated_row + "\n", encoding="utf-8")
    changed = LoadSummary()
    load_question_banks(loaded, str(qdir), summary=changed)
    loaded.commit()
    loaded.refresh(added)
    assert added.explanation.startswith("Use ipconfig /renew")
    assert changed.by_entity["question"]["updated"] == 1
    assert loaded.query(Question).filter(Question.quiz_id == quiz_id).count() == after


# --------------------------------------------------------------------------- #
# Router surface
# --------------------------------------------------------------------------- #

def test_student_progress_routes(loaded, monkeypatch):
    from app.routers.v2_progress import router as progress_router

    student = make_student(loaded, username="ip_router_student")
    enroll_v2(monkeypatch, student)
    client = make_client(progress_router)
    resp = client.post(
        "/api/v2/progress/activity",
        headers=auth_headers(student),
        json={
            "module_key": MODULE_KEY,
            "activity_type": "lesson",
            "ref_key": LESSON_KEYS[0],
            "status": "completed",
        },
    )
    assert resp.status_code == 404, resp.text

    got = client.get(
        f"/api/v2/progress/module/{MODULE_KEY}", headers=auth_headers(student)
    )
    assert got.status_code == 200
    assert got.json()["data"]["lessons"] == {"total": 0, "completed": 0, "items": []}

    # No generic student mutation surface remains, regardless of payload.
    bad = client.post(
        "/api/v2/progress/activity",
        headers=auth_headers(student),
        json={
            "module_key": MODULE_KEY,
            "activity_type": "not_a_real_type",
            "ref_key": "x",
        },
    )
    assert bad.status_code == 404


def test_admin_mentor_route(loaded, monkeypatch):
    from app.routers.admin_v2_mentor import router as mentor_router
    from app.services.admin_auth import verify_admin

    student = make_student(loaded, username="ip_mentor_target")
    monkeypatch.setenv("V2_CURRICULUM_ENABLED", "true")
    record_activity(
        loaded, student_id=student.id, module_key=MODULE_KEY,
        activity_type="lesson", ref_key=LESSON_KEYS[0], status="completed",
    )
    loaded.commit()

    client = make_client(mentor_router)
    client.app.dependency_overrides[verify_admin] = lambda: True
    resp = client.get(
        f"/api/admin/v2/mentor/module/{MODULE_KEY}/student/{student.id}"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["module_key"] == MODULE_KEY
    assert data["completion"]["lessons_completed"] == 0

    missing = client.get(
        f"/api/admin/v2/mentor/module/module.does.not.exist/student/{student.id}"
    )
    assert missing.status_code == 404
