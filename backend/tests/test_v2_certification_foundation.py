"""Phase 1A — Nexus V2 additive certification foundation.

Covers: certification/version/objective uniqueness, multi-version coexistence,
idempotent loading, lesson<->module<->objective mapping, multi-parent lesson
relationships, the extended importer (new metadata, permission_status
validation, ExamCompass provenance, backward compatibility), and a guard that
none of this disturbs the legacy week/40%-gate system.
"""

import os
import textwrap

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.certification import (
    Certification,
    CertificationModule,
    CertificationObjective,
    CertificationVersion,
    LessonObjective,
    LessonRelationship,
    LessonV2Meta,
    QuestionV2Meta,
    is_publishable_permission,
    normalize_importance,
)
from app.models.learning import Lesson, Module
from app.models.quiz import Question
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services import a_plus_access
from app.services.question_importer import confirm_import, parse_csv_file, preview_rows
from app.services.v2_content_loader import (
    DEFAULT_OBJECTIVES_DIR,
    backfill_examcompass_permission,
    load_all,
    load_objectives,
)


# --------------------------------------------------------------------------- #
# Hierarchy constraints
# --------------------------------------------------------------------------- #

def test_certification_cert_key_is_unique(db):
    db.add(Certification(cert_key="comptia_aplus", name="A+"))
    db.commit()
    db.add(Certification(cert_key="comptia_aplus", name="A+ dupe"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_version_key_unique_within_and_across_certifications(db):
    cert = Certification(cert_key="c1", name="C1")
    db.add(cert)
    db.flush()
    db.add(CertificationVersion(certification_id=cert.id, version_key="v-a", label="A"))
    db.commit()
    db.add(CertificationVersion(certification_id=cert.id, version_key="v-a", label="A again"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_objective_code_unique_within_a_version(db):
    cert = Certification(cert_key="c1", name="C1")
    db.add(cert)
    db.flush()
    version = CertificationVersion(certification_id=cert.id, version_key="v1", label="V1")
    db.add(version)
    db.flush()
    db.add(
        CertificationObjective(
            certification_version_id=version.id, objective_code="1.1", objective_text="First"
        )
    )
    db.commit()
    db.add(
        CertificationObjective(
            certification_version_id=version.id, objective_code="1.1", objective_text="Dup"
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_same_objective_code_coexists_across_versions(db):
    load_all(db)
    db.commit()

    v1201 = (
        db.query(CertificationVersion)
        .filter_by(version_key="comptia_aplus_220-1201")
        .one()
    )
    v1202 = (
        db.query(CertificationVersion)
        .filter_by(version_key="comptia_aplus_220-1202")
        .one()
    )
    assert v1201.id != v1202.id

    o1 = (
        db.query(CertificationObjective)
        .filter_by(certification_version_id=v1201.id, objective_code="1.1")
        .one()
    )
    o2 = (
        db.query(CertificationObjective)
        .filter_by(certification_version_id=v1202.id, objective_code="1.1")
        .one()
    )
    # Same code, different version, different text — both persist independently.
    assert "laptop hardware" in o1.objective_text.lower()
    assert "operating system" in o2.objective_text.lower()
    assert o1.id != o2.id


def test_exam_codes_are_stored_as_data_on_the_version(db):
    load_all(db)
    db.commit()
    v = db.query(CertificationVersion).filter_by(version_key="comptia_aplus_220-1201").one()
    assert v.exam_codes == ["220-1201"]


# --------------------------------------------------------------------------- #
# Idempotent loading
# --------------------------------------------------------------------------- #

def test_load_all_is_idempotent(db):
    first = load_all(db)
    db.commit()
    counts_after_first = {
        "certifications": db.query(Certification).count(),
        "versions": db.query(CertificationVersion).count(),
        "objectives": db.query(CertificationObjective).count(),
        "modules": db.query(CertificationModule).count(),
    }
    assert first["created"] > 0

    second = load_all(db)
    db.commit()
    counts_after_second = {
        "certifications": db.query(Certification).count(),
        "versions": db.query(CertificationVersion).count(),
        "objectives": db.query(CertificationObjective).count(),
        "modules": db.query(CertificationModule).count(),
    }

    assert counts_after_first == counts_after_second
    assert second["created"] == 0
    assert second["updated"] == 0
    assert second["unchanged"] > 0


def test_load_objectives_updates_in_place_without_duplicates(db, tmp_path):
    load_all(db)  # loads versions AND the real objective files
    db.commit()

    changed = tmp_path / "obj.yaml"
    changed.write_text(
        textwrap.dedent(
            """\
            version_key: comptia_aplus_220-1201
            source_name: "Test source"
            source_url: "https://example.test/objectives"
            objectives:
              - code: "1.1"
                domain_key: "1.0"
                text: "REPLACED TEXT for 1.1"
                subtopics: ["x"]
            """
        )
    )

    before = db.query(CertificationObjective).filter_by(objective_code="1.1").count()
    summary = load_objectives(db, str(changed))
    db.commit()
    after = db.query(CertificationObjective).filter_by(objective_code="1.1").count()

    assert before == after  # no new row for an existing code
    assert summary.updated == 1
    row = (
        db.query(CertificationObjective)
        .join(CertificationVersion)
        .filter(
            CertificationVersion.version_key == "comptia_aplus_220-1201",
            CertificationObjective.objective_code == "1.1",
        )
        .one()
    )
    assert row.objective_text == "REPLACED TEXT for 1.1"


def test_load_objectives_requires_a_loaded_version(db):
    with pytest.raises(ValueError):
        load_objectives(
            db, os.path.join(DEFAULT_OBJECTIVES_DIR, "comptia-a-plus-220-1201.yaml")
        )


def test_objectives_record_provenance(db):
    load_all(db)
    db.commit()
    obj = db.query(CertificationObjective).filter_by(objective_code="5.1").first()
    assert obj is not None
    assert obj.source_name
    assert obj.source_url and obj.source_url.startswith("http")


# --------------------------------------------------------------------------- #
# Lesson / module / objective mapping
# --------------------------------------------------------------------------- #

def _make_lesson(db, module, *, title, order):
    lesson = Lesson(module_id=module.id, title=title, lesson_order=order, outcomes=[])
    db.add(lesson)
    db.flush()
    return lesson


def _make_lesson_meta(db, *, key, module_id, version_id, lesson_id=None, relationship="new"):
    meta = LessonV2Meta(
        lesson_id=lesson_id,
        lesson_key=key,
        certification_version_id=version_id,
        certification_module_id=module_id,
        domain_key="2.0",
        title=key,
        importance="job_critical",
        learning_relationship=relationship,
    )
    db.add(meta)
    db.flush()
    return meta


def test_lesson_maps_to_v2_module_and_objectives(db):
    load_all(db)
    module = Module(code="MOD-TEST", title="Test module")
    db.add(module)
    db.flush()
    lesson = _make_lesson(db, module, title="DNS basics", order=1)

    version = (
        db.query(CertificationVersion)
        .filter_by(version_key="comptia_aplus_220-1201")
        .one()
    )
    cert_module = (
        db.query(CertificationModule)
        .filter_by(module_key="module.aplus.core1.networking_fundamentals")
        .one()
    )
    objective = (
        db.query(CertificationObjective)
        .filter_by(certification_version_id=version.id, objective_code="2.5")
        .one()
    )

    # A V2 lesson MAY bind 1:1 to an untouched legacy lessons row, but does not
    # have to. Objectives are linked through the companion meta row, never the
    # legacy lessons table.
    meta = _make_lesson_meta(
        db,
        key="lesson.aplus.dns_basics",
        module_id=cert_module.id,
        version_id=version.id,
        lesson_id=lesson.id,
    )
    db.add(LessonObjective(lesson_v2_meta_id=meta.id, objective_id=objective.id))
    db.commit()

    meta = db.query(LessonV2Meta).filter_by(lesson_key="lesson.aplus.dns_basics").one()
    assert meta.certification_module_id == cert_module.id
    assert meta.lesson.title == "DNS basics"  # 1:1 back-reference to the untouched lessons row
    linked = db.query(LessonObjective).filter_by(lesson_v2_meta_id=meta.id).all()
    assert [lo.objective_id for lo in linked] == [objective.id]


def test_lesson_can_build_on_multiple_earlier_lessons(db):
    load_all(db)
    version = (
        db.query(CertificationVersion).filter_by(version_key="comptia_aplus_220-1201").one()
    )
    cert_module = (
        db.query(CertificationModule)
        .filter_by(module_key="module.aplus.core1.networking_fundamentals")
        .one()
    )
    a = _make_lesson_meta(db, key="l.dns_basics", module_id=cert_module.id, version_id=version.id)
    b = _make_lesson_meta(db, key="l.dhcp_basics", module_id=cert_module.id, version_id=version.id)
    deep = _make_lesson_meta(
        db, key="l.dns_deep", module_id=cert_module.id, version_id=version.id, relationship="deep_dive"
    )

    db.add(
        LessonRelationship(
            from_lesson_meta_id=deep.id, to_lesson_meta_id=a.id, relationship_type="builds_on"
        )
    )
    db.add(
        LessonRelationship(
            from_lesson_meta_id=deep.id, to_lesson_meta_id=b.id, relationship_type="review_of"
        )
    )
    db.commit()

    edges = db.query(LessonRelationship).filter_by(from_lesson_meta_id=deep.id).all()
    assert {(e.to_lesson_meta_id, e.relationship_type) for e in edges} == {
        (a.id, "builds_on"),
        (b.id, "review_of"),
    }


def test_lesson_relationship_rejects_self_edge(db):
    load_all(db)
    version = (
        db.query(CertificationVersion).filter_by(version_key="comptia_aplus_220-1201").one()
    )
    cert_module = (
        db.query(CertificationModule)
        .filter_by(module_key="module.aplus.core1.networking_fundamentals")
        .one()
    )
    meta = _make_lesson_meta(db, key="l.solo", module_id=cert_module.id, version_id=version.id)
    db.add(
        LessonRelationship(
            from_lesson_meta_id=meta.id,
            to_lesson_meta_id=meta.id,
            relationship_type="builds_on",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


# --------------------------------------------------------------------------- #
# Importer — new metadata, validation, provenance, backward compatibility
# --------------------------------------------------------------------------- #

LEGACY_HEADER = (
    "quiz_title,question_type,question_text,option_a,option_b,option_c,option_d,"
    "option_e,option_f,option_g,option_h,correct_answers,explanation,difficulty,tags,source,published\n"
)


def _v2_row(**overrides):
    row = {
        "quiz_title": "A+ Core 1 — Networking",
        "question_type": "single",
        "question_text": "A workstation shows a 169.254.x.x address. What failed?",
        "option_a": "DHCP",
        "option_b": "DNS",
        "option_c": "NTP",
        "option_d": "SMTP",
        "correct_answers": "A",
        "explanation": "169.254.x.x is APIPA — the DHCP lease was not obtained.",
        "difficulty": "2",
        "tags": "networking,apipa",
        "source": "Nexus curriculum team",
        "published": "false",
        "certification": "comptia_aplus",
        "certification_version": "comptia_aplus_220-1201",
        "domain": "2.0",
        "module": "module.aplus.core1.networking_fundamentals",
        "objective_code": "5.7",
        "importance": "job_critical",
        "source_name": "Nexus curriculum team",
        "source_url": "",
        "permission_status": "owned",
    }
    row.update(overrides)
    return row


def test_importer_records_v2_metadata_and_resolves_version_fk(db):
    load_all(db)
    db.commit()

    summary = confirm_import(
        db, [_v2_row()], duplicate_policy="skip", source_filename="v2.csv"
    )
    assert summary["created"] == 1

    q = (
        db.query(Question)
        .filter(Question.question_text.like("A workstation shows a 169.254%"))
        .one()
    )
    meta = q.v2_meta
    assert meta is not None
    # The legacy questions row is not carrying any V2 columns.
    assert not hasattr(q, "v2_certification")
    assert meta.certification == "comptia_aplus"
    assert meta.certification_version == "comptia_aplus_220-1201"
    assert meta.domain == "2.0"
    assert meta.module == "module.aplus.core1.networking_fundamentals"
    assert meta.objective_code == "5.7"
    assert meta.importance == "job_critical"
    assert meta.permission_status == "owned"
    assert meta.source_name == "Nexus curriculum team"
    version = (
        db.query(CertificationVersion)
        .filter_by(version_key="comptia_aplus_220-1201")
        .one()
    )
    assert meta.certification_version_id == version.id


def test_importer_version_fk_is_null_for_unloaded_version(db):
    summary = confirm_import(
        db, [_v2_row()], duplicate_policy="skip", source_filename="v2.csv"
    )
    assert summary["created"] == 1
    meta = db.query(QuestionV2Meta).one()
    assert meta.certification_version == "comptia_aplus_220-1201"  # string still recorded
    assert meta.certification_version_id is None  # FK unresolved, non-fatal


def test_importer_defaults_permission_status_to_unknown(db):
    row = _v2_row()
    row.pop("permission_status")
    confirm_import(db, [row], duplicate_policy="skip", source_filename="v2.csv")
    meta = db.query(QuestionV2Meta).one()
    assert meta.permission_status == "unknown"


def test_importer_rejects_invalid_permission_status(db):
    row = _v2_row(permission_status="totally-made-up", question_text="Invalid perm status row?")
    previews = preview_rows(db, [row])
    assert previews[0].valid is False
    assert any("permission status" in e.lower() for e in previews[0].errors)

    summary = confirm_import(db, [row], duplicate_policy="skip", source_filename="v2.csv")
    assert summary["created"] == 0
    assert summary["skipped_invalid"] == 1
    assert db.query(QuestionV2Meta).count() == 0


def test_importer_rejects_invalid_importance(db):
    row = _v2_row(importance="super-important", question_text="Invalid importance row?")
    previews = preview_rows(db, [row])
    assert previews[0].valid is False
    assert any("importance" in e.lower() for e in previews[0].errors)


def test_importer_accepts_know_it_importance_alias(db):
    row = _v2_row(importance="know_it", question_text="Alias importance row?")
    confirm_import(db, [row], duplicate_policy="skip", source_filename="v2.csv")
    q = db.query(Question).filter(Question.question_text == "Alias importance row?").one()
    assert q.v2_meta.importance == "working_knowledge"


def test_examcompass_rows_can_be_marked_permitted_with_provenance(db):
    row = _v2_row(
        question_text="ExamCompass permitted row?",
        source="ExamCompass",
        source_name="ExamCompass",
        source_url="https://www.examcompass.com/comptia/a-plus-certification/free-a-plus-practice-tests",
        permission_status="permitted",
        certification_version="",
    )
    confirm_import(db, [row], duplicate_policy="skip", source_filename="examcompass.csv")
    q = db.query(Question).filter(Question.question_text == "ExamCompass permitted row?").one()
    assert q.v2_meta.permission_status == "permitted"
    assert q.v2_meta.source_name == "ExamCompass"
    assert q.source == "ExamCompass"  # exact original provenance preserved on the legacy row
    assert is_publishable_permission(q.v2_meta.permission_status) is True


def test_backfill_marks_existing_examcompass_questions_permitted(db):
    # A pre-existing question imported before V2 — no meta row at all.
    legacy_rows = [
        {
            "quiz_title": "Legacy ExamCompass quiz",
            "question_type": "single",
            "question_text": "Legacy examcompass question stem?",
            "option_a": "Yes",
            "option_b": "No",
            "correct_answers": "A",
            "explanation": "Because yes.",
            "difficulty": "1",
            "tags": "",
            "source": "examcompass.com scrape",
            "published": "false",
        }
    ]
    confirm_import(db, legacy_rows, duplicate_policy="skip", source_filename="legacy.csv")
    q = db.query(Question).filter(Question.question_text == "Legacy examcompass question stem?").one()
    assert q.v2_meta.permission_status == "unknown"  # imported, but unclassified

    # Also exercise the "no meta row at all" path with a bare ORM question.
    bare = Question(
        quiz_id=q.quiz_id,
        question_text="Bare examcompass question with no meta row?",
        option_a="A",
        option_b="B",
        correct_answer="A",
        explanation="x",
        source="from examcompass.com",
    )
    db.add(bare)
    db.commit()

    result = backfill_examcompass_permission(db, commit=True)
    assert result["updated"] == 2
    db.refresh(q)
    db.refresh(bare)
    assert q.v2_meta.permission_status == "permitted"
    assert q.v2_meta.source_name == "ExamCompass"
    assert bare.v2_meta.permission_status == "permitted"
    assert q.source == "examcompass.com scrape"  # legacy provenance untouched

    # Idempotent: a second run does not re-touch already-permitted rows.
    assert backfill_examcompass_permission(db, commit=True)["updated"] == 0


def test_legacy_import_without_v2_columns_still_works(db):
    csv_text = LEGACY_HEADER + (
        'Legacy quiz,single,"Legacy stem here?",A opt,B opt,C opt,D opt,,,,,'
        "A,Legacy explanation.,2,tag,manual,false\n"
    )
    rows = parse_csv_file(csv_text.encode("utf-8"))
    summary = confirm_import(db, rows, duplicate_policy="skip", source_filename="legacy.csv")
    assert summary["created"] == 1
    q = db.query(Question).filter(Question.question_text == "Legacy stem here?").one()
    # A legacy row with no V2 columns still gets a meta row, defaulted safely.
    assert q.v2_meta.permission_status == "unknown"
    assert q.v2_meta.certification is None
    assert q.v2_meta.certification_version_id is None


def test_new_template_header_round_trips_through_csv_parser(db):
    from app.services.question_importer import TEMPLATE_COLUMNS

    header = ",".join(TEMPLATE_COLUMNS) + "\n"
    values = _v2_row()
    line = ",".join(f'"{values[col]}"' if col in values else "" for col in TEMPLATE_COLUMNS) + "\n"
    rows = parse_csv_file((header + line).encode("utf-8"))
    assert rows[0]["certification_version"] == "comptia_aplus_220-1201"
    assert rows[0]["permission_status"] == "owned"


def test_fingerprint_dedup_preserved_with_v2_metadata(db):
    row = _v2_row()
    first = confirm_import(db, [row], duplicate_policy="skip", source_filename="a.csv")
    second = confirm_import(db, [row], duplicate_policy="skip", source_filename="b.csv")
    assert first["created"] == 1
    assert second["created"] == 0
    assert second["skipped_duplicates"] == 1


# --------------------------------------------------------------------------- #
# Guard: legacy week / 40% gate system is untouched
# --------------------------------------------------------------------------- #

def test_legacy_40_percent_gate_constant_unchanged():
    assert a_plus_access.DEFAULT_A_PLUS_UNLOCK_THRESHOLD_PCT == 40
    assert a_plus_access.A_PLUS_EXAM_CODES == ("220-1201", "220-1202")


def test_lessons_table_schema_unchanged():
    # Phase 1A adds NO columns to the legacy lessons table; V2 mapping lives in
    # the lesson_v2_meta companion table.
    lesson_cols = set(Lesson.__table__.columns.keys())
    for added in ("lesson_key", "certification_version_id", "certification_module_id", "importance"):
        assert added not in lesson_cols


def test_questions_table_schema_unchanged():
    # Phase 1A adds NO columns to the legacy questions table; V2 metadata +
    # provenance live in the question_v2_meta companion table. This is what
    # keeps historical data-migrations (which INSERT via the current ORM)
    # working against an un-upgraded schema.
    question_cols = set(Question.__table__.columns.keys())
    for added in ("permission_status", "v2_certification", "certification_version_id", "source_name"):
        assert added not in question_cols


def test_training_week_schema_unchanged():
    week_cols = set(TrainingWeek.__table__.columns.keys())
    assert "certification_version_id" not in week_cols
    assert week_cols == {
        "id",
        "week_number",
        "display_order",
        "title",
        "description",
        "learning_goals",
        "estimated_minutes",
        "is_active",
        "requires_previous_week",
        "created_at",
        "updated_at",
    }
    assert "activity_type" in TrainingWeekActivity.__table__.columns.keys()


def test_v2_load_and_import_create_no_training_week_rows(db):
    load_all(db)
    confirm_import(db, [_v2_row()], duplicate_policy="skip", source_filename="v2.csv")
    db.commit()
    assert db.query(TrainingWeek).count() == 0
    assert db.query(TrainingWeekActivity).count() == 0


def test_importance_and_permission_helpers():
    assert normalize_importance("know_it") == "working_knowledge"
    assert normalize_importance("  JOB_CRITICAL ") == "job_critical"
    assert normalize_importance("") is None
    assert is_publishable_permission("owned") is True
    assert is_publishable_permission("permitted") is True
    assert is_publishable_permission("requested") is False
    assert is_publishable_permission(None) is False
