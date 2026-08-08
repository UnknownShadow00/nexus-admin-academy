import io

import openpyxl
import pytest

from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
from app.routers import admin_question_import
from app.services.admin_auth import verify_admin
from app.services import question_importer
from app.services.question_importer import (
    ImportFileError,
    compute_fingerprint,
    confirm_import,
    parse_csv_file,
    parse_xlsx_file,
    preview_rows,
    sanitize_text,
)
from conftest import make_client

CSV_HEADER = (
    "quiz_title,question_type,question_text,option_a,option_b,option_c,option_d,"
    "option_e,option_f,option_g,option_h,correct_answers,explanation,difficulty,tags,source,published\n"
)


def admin_client():
    client = make_client(admin_question_import.router)
    client.app.dependency_overrides[verify_admin] = lambda: True
    return client


def _csv_row(
    quiz_title="Networking Basics",
    qtype="single",
    text="What port does HTTPS use?",
    a="443",
    b="80",
    c="21",
    d="25",
    e="",
    correct="A",
    explanation="HTTPS uses 443.",
):
    return f'{quiz_title},{qtype},"{text}",{a},{b},{c},{d},{e},,,,{correct},{explanation},2,networking,manual,false\n'


def test_parse_csv_file_basic():
    content = (CSV_HEADER + _csv_row()).encode("utf-8")
    rows = parse_csv_file(content)
    assert len(rows) == 1
    assert rows[0]["question_text"] == "What port does HTTPS use?"


def test_parse_csv_file_too_large_is_rejected():
    huge = b"a" * (question_importer.MAX_FILE_SIZE_BYTES + 1)
    with pytest.raises(ImportFileError):
        parse_csv_file(huge)


def test_sanitize_text_neutralizes_formula_injection():
    assert sanitize_text("=cmd|' /C calc'!A0").startswith("'=")
    assert sanitize_text("  normal text  ") == "normal text"


def test_xlsx_formula_cell_is_never_executed():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["question_text", "option_a", "option_b"])
    ws.append(["=1+1", "Yes", "No"])  # formula string, never computed by Excel/LibreOffice
    buf = io.BytesIO()
    wb.save(buf)

    rows = parse_xlsx_file(buf.getvalue())
    assert len(rows) == 1
    # data_only=True reads the *cached* result; since this workbook was never
    # opened/recalculated by a spreadsheet engine, there is no cached value —
    # openpyxl returns None rather than evaluating "=1+1" itself.
    assert rows[0]["question_text"] != 2
    assert rows[0]["question_text"] != "2"


def test_preview_rows_splits_valid_and_invalid(db):
    content = CSV_HEADER + _csv_row() + _csv_row(text="Missing answer key", correct="")
    rows = parse_csv_file(content.encode("utf-8"))
    results = preview_rows(db, rows)
    assert results[0].valid is True
    assert results[1].valid is False
    assert any("correct answer" in msg.lower() for msg in results[1].errors)


def test_confirm_import_creates_quiz_and_questions(db):
    content = CSV_HEADER + _csv_row()
    rows = parse_csv_file(content.encode("utf-8"))

    summary = confirm_import(db, rows, duplicate_policy="skip", source_filename="test.csv")

    assert summary["created"] == 1
    assert summary["skipped_invalid"] == 0
    quiz = db.query(Quiz).filter(Quiz.title == "Networking Basics").first()
    assert quiz is not None
    question = db.query(Question).filter(Question.quiz_id == quiz.id).first()
    assert question.question_text == "What port does HTTPS use?"
    assert question.import_filename == "test.csv"
    assert question.imported_at is not None
    assert question.fingerprint == compute_fingerprint("Networking Basics", "What port does HTTPS use?", ["443", "80", "21", "25"])


def test_confirm_import_restores_curated_explanation_when_source_is_blank(db, monkeypatch):
    monkeypatch.setattr(
        question_importer,
        "catalog_explanation",
        lambda *_args: "HTTPS uses TLS on port 443; port 80 is ordinary HTTP.",
    )
    rows = parse_csv_file(
        (CSV_HEADER + _csv_row(explanation="")).encode("utf-8")
    )

    confirm_import(db, rows, duplicate_policy="skip", source_filename="reviewed.csv")

    assert db.query(Question).one().explanation == (
        "HTTPS uses TLS on port 443; port 80 is ordinary HTTP."
    )


def test_confirm_import_handles_true_false_two_option_question(db):
    """A question with only 2 options (e.g. true/false) must import cleanly —
    option_b/c/d are not NOT-NULL-required at the DB level, only option_a is;
    the shared validator enforces the real "at least 2" floor."""
    content = (
        CSV_HEADER
        + 'True/False Quiz,single,Is TCP connection-oriented?,True,False,,,,,,,A,TCP is connection-oriented.,1,networking,manual,false\n'
    )
    rows = parse_csv_file(content.encode("utf-8"))

    summary = confirm_import(db, rows, duplicate_policy="skip", source_filename="tf.csv")

    assert summary["created"] == 1
    assert summary["skipped_invalid"] == 0
    question = db.query(Question).filter(Question.question_text == "Is TCP connection-oriented?").first()
    assert question is not None
    assert question.option_a == "True"
    assert question.option_b == "False"
    assert question.option_c is None
    assert question.option_d is None


def test_confirm_import_skips_invalid_rows_without_failing_whole_batch(db):
    content = CSV_HEADER + _csv_row() + _csv_row(text="No answer here", correct="")
    rows = parse_csv_file(content.encode("utf-8"))

    summary = confirm_import(db, rows, duplicate_policy="skip", source_filename="test.csv")

    assert summary["created"] == 1
    assert summary["skipped_invalid"] == 1


def test_confirm_import_duplicate_policy_skip(db):
    content = CSV_HEADER + _csv_row()
    rows = parse_csv_file(content.encode("utf-8"))
    confirm_import(db, rows, duplicate_policy="skip", source_filename="first.csv")

    summary = confirm_import(db, rows, duplicate_policy="skip", source_filename="second.csv")
    assert summary["created"] == 0
    assert summary["skipped_duplicates"] == 1
    assert db.query(Question).count() == 1


def test_confirm_import_duplicate_policy_update_draft(db):
    content = CSV_HEADER + _csv_row(explanation="Original explanation")
    rows = parse_csv_file(content.encode("utf-8"))
    confirm_import(db, rows, duplicate_policy="skip", source_filename="first.csv")

    updated_rows = parse_csv_file((CSV_HEADER + _csv_row(explanation="Updated explanation")).encode("utf-8"))
    summary = confirm_import(db, updated_rows, duplicate_policy="update_draft", source_filename="second.csv")

    assert summary["updated"] == 1
    question = db.query(Question).first()
    assert question.explanation == "Updated explanation"
    assert question.import_filename == "second.csv"


def test_confirm_import_never_overwrites_published_question(db):
    content = CSV_HEADER + _csv_row(explanation="Original explanation")
    rows = parse_csv_file(content.encode("utf-8"))
    confirm_import(db, rows, duplicate_policy="skip", source_filename="first.csv")

    quiz = db.query(Quiz).first()
    quiz.status = QUIZ_STATUS_PUBLISHED
    db.commit()

    updated_rows = parse_csv_file((CSV_HEADER + _csv_row(explanation="Attempted overwrite")).encode("utf-8"))
    summary = confirm_import(db, updated_rows, duplicate_policy="update_draft", source_filename="second.csv")

    assert summary["updated"] == 0
    assert summary["skipped_duplicates"] == 1
    question = db.query(Question).first()
    assert question.explanation == "Original explanation"


def test_confirm_import_rolls_back_entire_batch_on_unexpected_failure(db, monkeypatch):
    content = CSV_HEADER + _csv_row(quiz_title="Batch A", text="Question one") + _csv_row(
        quiz_title="Batch A", text="Question two"
    )
    rows = parse_csv_file(content.encode("utf-8"))

    call_count = {"n": 0}
    original = question_importer.compute_fingerprint

    def _boom(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated failure mid-batch")
        return original(*args, **kwargs)

    monkeypatch.setattr(question_importer, "compute_fingerprint", _boom)

    with pytest.raises(RuntimeError):
        confirm_import(db, rows, duplicate_policy="skip", source_filename="fails.csv")

    # First row's Question/Quiz were added to the session before the failure,
    # but nothing was ever committed, so the rollback must discard all of it.
    assert db.query(Question).count() == 0
    assert db.query(Quiz).count() == 0


def test_preview_endpoint_via_http(db_session_override=None):
    client = admin_client()
    content = (CSV_HEADER + _csv_row() + _csv_row(text="Bad row", correct="")).encode("utf-8")
    res = client.post(
        "/api/admin/quiz/import/preview",
        files={"file": ("questions.csv", content, "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["valid_count"] == 1
    assert data["invalid_count"] == 1
    assert data["total_rows"] == 2


def test_confirm_endpoint_via_http_end_to_end():
    client = admin_client()
    content = (CSV_HEADER + _csv_row()).encode("utf-8")
    preview_res = client.post(
        "/api/admin/quiz/import/preview",
        files={"file": ("questions.csv", content, "text/csv")},
    )
    valid_rows = [row["raw_row"] for row in preview_res.json()["data"]["valid_rows"]]

    confirm_res = client.post(
        "/api/admin/quiz/import/confirm",
        json={"rows": valid_rows, "duplicate_policy": "skip", "source_filename": "questions.csv"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["data"]["created"] == 1


def test_xlsm_upload_is_rejected():
    client = admin_client()
    res = client.post(
        "/api/admin/quiz/import/preview",
        files={"file": ("macro.xlsm", b"fake content", "application/vnd.ms-excel.sheet.macroEnabled.12")},
    )
    assert res.status_code == 400


def test_template_download():
    client = admin_client()
    res = client.get("/api/admin/quiz/import/template")
    assert res.status_code == 200
    assert "quiz_title" in res.text
    assert "correct_answers" in res.text


def test_imported_quiz_organization_panel_can_be_saved(db):
    """A quiz created by the CSV/XLSX importer must be editable afterward —
    its source_type ("spreadsheet_import") has to be a value the admin
    quiz-update schema actually accepts."""
    from app.routers import admin_quiz

    client = make_client(admin_question_import.router, admin_quiz.router)
    client.app.dependency_overrides[verify_admin] = lambda: True

    content = CSV_HEADER + 'Org Panel Quiz,single,Pick one?,Yes,No,,,,,,,A,exp,,,,false\n'
    rows = parse_csv_file(content.encode("utf-8"))
    summary = confirm_import(db, rows, duplicate_policy="skip", source_filename="org.csv")
    quiz_id = summary["quiz_ids"][0]

    res = client.patch(
        f"/api/admin/quizzes/{quiz_id}",
        json={"editorial_status": "validated", "answer_keys_validated": True, "source_type": "spreadsheet_import"},
    )
    assert res.status_code == 200, res.text
