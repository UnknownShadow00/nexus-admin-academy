"""Phase 1B — Nexus V2 content + assessment foundation.

Covers the Markdown lesson loader, data-driven resources, module assessments,
objective coverage, the deterministic (no-AI) grader for short_answer /
free_response, interview/Explain prompt storage, the extended question
importer, and guards that none of this disturbs the V1 week / 40%-gate system.
"""

import os
import textwrap

import pytest

from app.models.certification import (
    GRADE_STATUS_GRADED,
    GRADE_STATUS_NEEDS_REVIEW,
    InterviewPrompt,
    LearningResource,
    LearningResourceLink,
    LessonObjective,
    LessonRelationship,
    LessonV2Meta,
    ModuleAssessment,
    QuestionV2Meta,
)
from app.models.quiz import Question
from app.models.training import TrainingWeek
from app.services import a_plus_access
from app.services.deterministic_grader import grade_free_response, grade_short_answer
from app.services.objective_coverage import certification_version_coverage
from app.services.question_importer import confirm_import
from app.services.v2_content_loader import (
    DEFAULT_CONTENT_DIR,
    ContentValidationError,
    load_all,
    load_content,
    load_interview_prompts,
    load_resources,
)
from app.services.v2_lesson_loader import load_lessons

CURRICULUM_DIR = os.path.join(DEFAULT_CONTENT_DIR, "curriculum")
RESOURCES_DIR = os.path.join(DEFAULT_CONTENT_DIR, "resources")
PROMPTS_DIR = os.path.join(DEFAULT_CONTENT_DIR, "interview-prompts")

LESSON_KEY = "lesson.aplus.core1.networking_fundamentals.tcp_udp_ports"


def _write(path: str, body: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(textwrap.dedent(body).lstrip())
    return path


GOOD_FRONTMATTER = """\
---
lesson_key: lesson.test.alpha
title: Alpha
certification_version: comptia_aplus_220-1201
domain: "2.0"
module: module.aplus.core1.networking_fundamentals
importance: job_critical
learning_relationship: new
objectives:
  - "2.1"
---

## 1. What is this?
Body text.
"""


# --------------------------------------------------------------------------- #
# Markdown lesson loader — idempotent sync
# --------------------------------------------------------------------------- #

def test_markdown_lesson_sync_is_idempotent_and_tracks_body_changes(db, tmp_path):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")
    lesson_path = _write(os.path.join(curriculum, "alpha.md"), GOOD_FRONTMATTER)

    s1 = load_lessons(db, curriculum)
    assert s1.as_dict()["by_entity"]["lesson"] == {"created": 1, "updated": 0, "unchanged": 0}
    meta = db.query(LessonV2Meta).filter_by(lesson_key="lesson.test.alpha").one()
    first_hash = meta.content_hash
    assert meta.certification_module_id is not None
    assert [lo.objective_id for lo in db.query(LessonObjective).filter_by(lesson_v2_meta_id=meta.id)]

    # Re-run, nothing changed on disk -> unchanged, no duplicate row.
    s2 = load_lessons(db, curriculum)
    assert s2.as_dict()["by_entity"]["lesson"]["unchanged"] == 1
    assert db.query(LessonV2Meta).filter_by(lesson_key="lesson.test.alpha").count() == 1

    # Edit the body -> updated, hash changes.
    _write(lesson_path, GOOD_FRONTMATTER + "\nAdded a sentence.\n")
    s3 = load_lessons(db, curriculum)
    assert s3.as_dict()["by_entity"]["lesson"]["updated"] == 1
    db.expire_all()
    assert db.query(LessonV2Meta).filter_by(lesson_key="lesson.test.alpha").one().content_hash != first_hash


def test_markdown_lesson_objective_set_change_is_synced(db, tmp_path):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")
    path = _write(os.path.join(curriculum, "alpha.md"), GOOD_FRONTMATTER)
    load_lessons(db, curriculum)
    meta = db.query(LessonV2Meta).filter_by(lesson_key="lesson.test.alpha").one()

    _write(path, GOOD_FRONTMATTER.replace('  - "2.1"', '  - "2.2"'))
    load_lessons(db, curriculum)
    db.expire_all()
    codes = {
        lo.objective_id
        for lo in db.query(LessonObjective).filter_by(lesson_v2_meta_id=meta.id)
    }
    assert len(codes) == 1  # replaced, not accumulated


def test_markdown_lesson_relationships_resolve_across_files(db, tmp_path):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")
    _write(os.path.join(curriculum, "a.md"), GOOD_FRONTMATTER)
    _write(
        os.path.join(curriculum, "b.md"),
        GOOD_FRONTMATTER.replace("lesson.test.alpha", "lesson.test.beta").replace("Alpha", "Beta")
        + "\nbuilds_on:\n  - lesson.test.alpha\n",
    )
    # (frontmatter edit above lands after the closing --- ; rewrite cleanly)
    _write(
        os.path.join(curriculum, "b.md"),
        """\
        ---
        lesson_key: lesson.test.beta
        title: Beta
        certification_version: comptia_aplus_220-1201
        domain: "2.0"
        module: module.aplus.core1.networking_fundamentals
        importance: working_knowledge
        learning_relationship: deep_dive
        builds_on:
          - lesson.test.alpha
        ---

        ## 1. What is this?
        Beta body.
        """,
    )
    load_lessons(db, curriculum)
    beta = db.query(LessonV2Meta).filter_by(lesson_key="lesson.test.beta").one()
    alpha = db.query(LessonV2Meta).filter_by(lesson_key="lesson.test.alpha").one()
    edges = db.query(LessonRelationship).filter_by(from_lesson_meta_id=beta.id).all()
    assert [(e.to_lesson_meta_id, e.relationship_type) for e in edges] == [(alpha.id, "builds_on")]


@pytest.mark.parametrize(
    "mutation,needle",
    [
        (lambda t: t.replace("importance: job_critical", "importance: super_important"), "importance"),
        (lambda t: t.replace('learning_relationship: new', 'learning_relationship: sideways'), "learning_relationship"),
        (lambda t: t.replace("title: Alpha\n", ""), "title"),
        (lambda t: t.replace('  - "2.1"', '  - "9.9"'), "9.9"),
        (lambda t: t.replace("module: module.aplus.core1.networking_fundamentals", "module: module.nope"), "module.nope"),
    ],
)
def test_markdown_validation_errors_name_file_and_field(db, tmp_path, mutation, needle):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")
    _write(os.path.join(curriculum, "broken.md"), mutation(GOOD_FRONTMATTER))
    with pytest.raises(ContentValidationError) as exc:
        load_lessons(db, curriculum)
    assert "broken.md" in str(exc.value)
    assert needle in str(exc.value)


def test_markdown_missing_frontmatter_is_rejected(db, tmp_path):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")
    _write(os.path.join(curriculum, "nofm.md"), "# Just a heading\nNo frontmatter here.\n")
    with pytest.raises(ContentValidationError) as exc:
        load_lessons(db, curriculum)
    assert "nofm.md" in str(exc.value)


# --------------------------------------------------------------------------- #
# Shipped fixture content loads end-to-end and is idempotent
# --------------------------------------------------------------------------- #

def test_shipped_content_loads_and_reruns_clean(db):
    load_all(db)
    load_content(db)
    first = load_content(db)  # second pass
    # Everything — lessons, resources, prompts, labs, AND question banks —
    # diff-and-set, so a clean rerun creates and updates nothing.
    assert first["created"] == 0
    assert first["updated"] == 0

    assert db.query(LessonV2Meta).filter_by(lesson_key=LESSON_KEY).count() == 1
    assert db.query(LearningResource).count() >= 2
    assert db.query(InterviewPrompt).count() >= 1


def test_resource_links_map_to_lessons_and_modules(db):
    load_all(db)
    load_content(db)
    res = db.query(LearningResource).filter_by(
        resource_key="res.aplus.core1.common_ports.reference_table"
    ).one()
    links = db.query(LearningResourceLink).filter_by(resource_id=res.id).all()
    assert any(link.lesson_v2_meta_id is not None for link in links)
    assert any(link.certification_module_id is not None for link in links)


def test_resource_sync_replaces_stale_links(db, tmp_path):
    load_all(db)
    load_content(db)  # lessons must exist for lesson_key links
    yaml_path = tmp_path / "r.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            f"""
            resources:
              - resource_key: res.test.one
                title: Test One
                resource_type: article
                url: https://example.test/one
                certification_version: comptia_aplus_220-1201
                permission_status: permitted
                links:
                  - lesson_key: {LESSON_KEY}
                    required: true
            """
        )
    )
    load_resources(db, str(yaml_path))
    res = db.query(LearningResource).filter_by(resource_key="res.test.one").one()
    assert db.query(LearningResourceLink).filter_by(resource_id=res.id).count() == 1

    yaml_path.write_text(
        textwrap.dedent(
            """
            resources:
              - resource_key: res.test.one
                title: Test One
                resource_type: article
                url: https://example.test/one
                certification_version: comptia_aplus_220-1201
                permission_status: permitted
                links:
                  - module_key: module.aplus.core1.networking_fundamentals
            """
        )
    )
    load_resources(db, str(yaml_path))
    db.expire_all()
    links = db.query(LearningResourceLink).filter_by(resource_id=res.id).all()
    assert len(links) == 1
    assert links[0].lesson_v2_meta_id is None
    assert links[0].certification_module_id is not None


def test_resource_bad_type_is_rejected_naming_file(db, tmp_path):
    load_all(db)
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text(
        "resources:\n  - resource_key: r.bad\n    resource_type: podcast\n    url: x\n"
    )
    with pytest.raises(ContentValidationError) as exc:
        load_resources(db, str(yaml_path))
    assert "bad.yaml" in str(exc.value) and "podcast" in str(exc.value)


# --------------------------------------------------------------------------- #
# Module assessments
# --------------------------------------------------------------------------- #

def test_module_assessments_load_with_roles_and_optional_lesson_ref(db):
    load_all(db)
    load_content(db)
    load_all(db)  # re-run so the quick_check assessment resolves its lesson_key
    rows = {
        a.assessment_key: a
        for a in db.query(ModuleAssessment).all()
    }
    assert rows["assess.aplus.core1.networking_fundamentals.quick_check"].assessment_role == "quick_check"
    assert rows["assess.aplus.core1.networking_fundamentals.quick_check"].lesson_v2_meta_id is not None
    assert rows["assess.aplus.core1.networking_fundamentals.module_quiz"].assessment_role == "module_quiz"
    # The networking_fundamentals fixture module wires only quick_check /
    # module_quiz / explain (the Phase 2A ip_configuration module adds
    # 'practical' and 'service_desk' roles elsewhere).
    nf_roles = {
        a.assessment_role
        for a in rows.values()
        if a.assessment_key.startswith("assess.aplus.core1.networking_fundamentals.")
    }
    assert nf_roles == {"quick_check", "module_quiz", "explain"}


def test_module_assessment_rejects_unknown_role(db, tmp_path):
    load_all(db)
    cert_yaml = tmp_path / "cert.yaml"
    cert_yaml.write_text(
        textwrap.dedent(
            """
            certification:
              cert_key: t_cert
              name: T
            versions:
              - version_key: t_v1
                label: T v1
                domains:
                  - { domain_key: "1.0", title: D, display_order: 1 }
                modules:
                  - module_key: t.mod
                    title: T Mod
                    certification_domain_key: "1.0"
                    assessments:
                      - assessment_key: t.assess
                        assessment_role: pop_quiz
            """
        )
    )
    from app.services.v2_content_loader import load_certifications

    with pytest.raises(ContentValidationError) as exc:
        load_certifications(db, str(cert_yaml))
    assert "pop_quiz" in str(exc.value)


# --------------------------------------------------------------------------- #
# Objective coverage
# --------------------------------------------------------------------------- #

def test_objective_coverage_counts_distinct_mapped_objectives(db, tmp_path):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")

    base = GOOD_FRONTMATTER
    _write(os.path.join(curriculum, "one.md"), base)
    # A second lesson mapping the SAME objective must not inflate coverage.
    _write(
        os.path.join(curriculum, "two.md"),
        base.replace("lesson.test.alpha", "lesson.test.two").replace("Alpha", "Two"),
    )
    load_lessons(db, curriculum)

    cov = certification_version_coverage(db, "comptia_aplus_220-1201")
    assert cov["covered_objectives"] == 1
    assert cov["uncovered_objectives"] == cov["total_objectives"] - 1
    assert 0 < cov["coverage_percent"] < 100
    assert all(entry["objective_code"] != "2.1" for entry in cov["uncovered"])


def test_objective_coverage_is_version_isolated(db, tmp_path):
    load_all(db)
    curriculum = str(tmp_path / "curriculum")
    _write(os.path.join(curriculum, "one.md"), GOOD_FRONTMATTER)
    load_lessons(db, curriculum)

    cov_1201 = certification_version_coverage(db, "comptia_aplus_220-1201")
    cov_1202 = certification_version_coverage(db, "comptia_aplus_220-1202")
    assert cov_1201["covered_objectives"] == 1
    assert cov_1202["covered_objectives"] == 0  # the lesson belongs to 1201 only


# --------------------------------------------------------------------------- #
# Deterministic grader (NO AI) — honest about ambiguity
# --------------------------------------------------------------------------- #

def test_short_answer_exact_and_synonym_match():
    r = grade_short_answer("443", ["443", "port 443"])
    assert r["status"] == GRADE_STATUS_GRADED and r["passed"] is True

    r = grade_short_answer("  Port 443 ", ["443", "port 443"])
    assert r["passed"] is True

    r = grade_short_answer("The answer is port 443.", ["port 443"])
    assert r["passed"] is True  # phrase contained in a short response


def test_short_answer_empty_is_graded_zero_but_wrong_is_confident():
    empty = grade_short_answer("", ["443"])
    assert empty["status"] == GRADE_STATUS_GRADED and empty["passed"] is False

    wrong = grade_short_answer("8080", ["443"])
    assert wrong["status"] == GRADE_STATUS_GRADED and wrong["passed"] is False


def test_short_answer_long_ramble_goes_to_review_not_wrong():
    rambly = "well it depends but usually i think the secure web port is the one that " \
             "browsers use when you see the padlock which is definitely not eighty"
    r = grade_short_answer(rambly, ["443"])
    assert r["status"] == GRADE_STATUS_NEEDS_REVIEW


def test_short_answer_without_key_needs_review():
    r = grade_short_answer("anything", [])
    assert r["status"] == GRADE_STATUS_NEEDS_REVIEW


def test_free_response_all_concepts_pass_partial_scores():
    concepts = ["connection-oriented", "retransmission", "low latency"]
    full = grade_free_response(
        "TCP is connection-oriented and uses retransmission; UDP favours low latency.",
        concepts,
    )
    assert full["status"] == GRADE_STATUS_GRADED and full["passed"] is True and full["score"] == 1.0

    partial = grade_free_response(
        "TCP is connection-oriented, that is the main idea here for this answer.",
        concepts,
    )
    assert partial["status"] == GRADE_STATUS_GRADED and partial["passed"] is False
    assert 0 < partial["score"] < 1


def test_free_response_unrecognised_prose_is_not_confidently_failed():
    # A plausible answer phrased entirely differently from the concept terms.
    r = grade_free_response(
        "One protocol sets up a handshake and re-sends what gets dropped; the other "
        "just fires packets and moves on, trading safety for speed.",
        ["connection-oriented", "retransmission", "low latency"],
    )
    assert r["status"] == GRADE_STATUS_NEEDS_REVIEW
    assert r["passed"] is None


def test_free_response_trivial_answer_is_graded_zero():
    r = grade_free_response("idk", ["connection-oriented", "retransmission"])
    assert r["status"] == GRADE_STATUS_GRADED and r["passed"] is False


def test_free_response_without_concepts_needs_review():
    r = grade_free_response("a full and thoughtful answer", [])
    assert r["status"] == GRADE_STATUS_NEEDS_REVIEW


# --------------------------------------------------------------------------- #
# Interview / Explain prompts
# --------------------------------------------------------------------------- #

def test_interview_prompt_stores_rubric_and_version(db):
    load_all(db)
    load_content(db)
    prompt = db.query(InterviewPrompt).filter_by(
        prompt_key="interview.aplus.core1.tcp_udp_ports.explain_difference"
    ).one()
    assert prompt.rubric_version == "2026-08-a"
    assert isinstance(prompt.rubric, dict) and prompt.rubric
    assert prompt.expected_concepts and prompt.objective_links


def test_interview_prompt_requires_prompt_text(db, tmp_path):
    load_all(db)
    yaml_path = tmp_path / "p.yaml"
    yaml_path.write_text("prompts:\n  - prompt_key: p.empty\n    prompt: '   '\n")
    with pytest.raises(ContentValidationError) as exc:
        load_interview_prompts(db, str(yaml_path))
    assert "p.empty" in str(exc.value)


# --------------------------------------------------------------------------- #
# Extended question importer — free-form types
# --------------------------------------------------------------------------- #

def _import(db, rows):
    return confirm_import(db, rows, duplicate_policy="skip", source_filename="t.csv")


def test_importer_creates_short_answer_question_with_grading_meta(db):
    rows = [
        {
            "quiz_title": "FF Quiz",
            "question_type": "short_answer",
            "question_text": "Default HTTPS port?",
            "acceptable_answers": '["443", "port 443"]',
            "rubric_version": "2026-08-a",
            "certification_version": "comptia_aplus_220-1201",
        }
    ]
    summary = _import(db, rows)
    assert summary["created"] == 1
    q = db.query(Question).filter_by(question_text="Default HTTPS port?").one()
    assert q.correct_answer == "-"
    assert q.option_a == ""
    meta = db.query(QuestionV2Meta).filter_by(question_id=q.id).one()
    assert meta.question_type == "short_answer"
    assert meta.acceptable_answers == ["443", "port 443"]
    assert meta.rubric_version == "2026-08-a"


def test_importer_free_response_requires_expected_concepts(db):
    rows = [
        {
            "quiz_title": "FF Quiz",
            "question_type": "free_response",
            "question_text": "Explain the difference between TCP and UDP.",
        }
    ]
    summary = _import(db, rows)
    assert summary["created"] == 0
    assert summary["skipped_invalid"] == 1


def test_importer_free_response_pipe_concepts(db):
    rows = [
        {
            "quiz_title": "FF Quiz",
            "question_type": "free_response",
            "question_text": "Explain DNS resolution.",
            "expected_concepts": "recursive resolver|root servers|caching",
        }
    ]
    assert _import(db, rows)["created"] == 1
    meta = (
        db.query(QuestionV2Meta)
        .join(Question, Question.id == QuestionV2Meta.question_id)
        .filter(Question.question_text == "Explain DNS resolution.")
        .one()
    )
    assert meta.expected_concepts == ["recursive resolver", "root servers", "caching"]


def test_importer_legacy_mcq_row_still_works(db):
    rows = [
        {
            "quiz_title": "MCQ Quiz",
            "question_text": "Pick the transport protocols.",
            "option_a": "TCP",
            "option_b": "UDP",
            "option_c": "HTTP",
            "correct_answers": "A|B",
            "question_type": "multi",
        }
    ]
    assert _import(db, rows)["created"] == 1
    q = db.query(Question).filter_by(question_text="Pick the transport protocols.").one()
    assert q.correct_answers == "A,B"
    assert db.query(QuestionV2Meta).filter_by(question_id=q.id).count() == 1  # meta row, MCQ type


# --------------------------------------------------------------------------- #
# Guards — V1 systems untouched
# --------------------------------------------------------------------------- #

def test_v1_forty_percent_gate_constant_unchanged():
    assert a_plus_access.DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT == 40


def test_v2_content_load_creates_no_training_weeks(db):
    load_all(db)
    load_content(db)
    assert db.query(TrainingWeek).count() == 0


def test_legacy_questions_table_columns_unchanged(db):
    cols = {c.name for c in Question.__table__.columns}
    for v2_col in ("acceptable_answers", "expected_concepts", "rubric", "certification_version"):
        assert v2_col not in cols  # V2 data lives in question_v2_meta only
