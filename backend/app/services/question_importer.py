"""CSV/XLSX question import: parsing, sanitizing, duplicate fingerprinting,
and the preview/confirm transaction. Validation itself is delegated entirely
to app.services.question_validation so authored, ExamCompass, and
spreadsheet-imported questions are all held to the same rules.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import openpyxl
from sqlalchemy.orm import Session

from app.models.quiz import (
    EDITORIAL_STATUS_UNREVIEWED,
    QUIZ_STATUS_DRAFT,
    QUIZ_STATUS_PUBLISHED,
    SOURCE_TYPE_MANUAL,
    SOURCE_TYPE_SPREADSHEET_IMPORT,
    Question,
    Quiz,
)
from app.services.question_validation import validate_question

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 2000

TEMPLATE_COLUMNS = [
    "quiz_title",
    "question_type",
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "option_f",
    "option_g",
    "option_h",
    "correct_answers",
    "explanation",
    "difficulty",
    "tags",
    "source",
    "published",
]

_FORMULA_LEAD_CHARS = ("=", "+", "-", "@")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class ImportFileError(ValueError):
    """Raised for file-level problems (too big, too many rows, bad format)."""


def sanitize_text(value) -> str:
    """Strip control characters and neutralize spreadsheet formula injection.
    Never executes anything — this only affects what gets stored/re-displayed."""
    text = "" if value is None else str(value)
    text = _CONTROL_CHARS_RE.sub("", text).strip()
    if text and text[0] in _FORMULA_LEAD_CHARS:
        text = f"'{text}"
    return text


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "y", "1"}


def compute_fingerprint(quiz_title: str, question_text: str, option_texts: list[str]) -> str:
    normalized = "|".join(
        [
            (quiz_title or "").strip().casefold(),
            (question_text or "").strip().casefold(),
            *[t.strip().casefold() for t in option_texts],
        ]
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_csv_file(data: bytes) -> list[dict]:
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ImportFileError(f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit.")
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(row) for row in reader]
    if len(rows) > MAX_ROWS:
        raise ImportFileError(f"File has {len(rows)} rows; the limit is {MAX_ROWS}.")
    return rows


def parse_xlsx_file(data: bytes) -> list[dict]:
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ImportFileError(f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit.")
    # data_only=True reads cached formula *results*, never evaluates formulas.
    # read_only=True avoids loading the full workbook (and any VBA project) into memory.
    workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    sheet = workbook.worksheets[0]
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header = [str(cell or "").strip() for cell in next(rows_iter)]
    except StopIteration:
        return []
    rows = []
    for raw_row in rows_iter:
        if raw_row is None or all(cell is None for cell in raw_row):
            continue
        rows.append({header[i]: raw_row[i] for i in range(min(len(header), len(raw_row)))})
        if len(rows) > MAX_ROWS:
            raise ImportFileError(f"File has more than {MAX_ROWS} rows.")
    return rows


def row_to_payload(row: dict) -> dict:
    options = [sanitize_text(row.get(f"option_{letter}")) for letter in "abcdefgh"]
    return {
        "quiz_title": sanitize_text(row.get("quiz_title")) or "Imported Questions",
        "question_type": sanitize_text(row.get("question_type")) or None,
        "question_text": sanitize_text(row.get("question_text")),
        "options": options,
        "correct_answers": sanitize_text(row.get("correct_answers")),
        "explanation": sanitize_text(row.get("explanation")),
        "difficulty": sanitize_text(row.get("difficulty")) or None,
        "tags": [t.strip() for t in sanitize_text(row.get("tags")).split(",") if t.strip()],
        "source": sanitize_text(row.get("source")) or None,
        "published": _truthy(row.get("published")),
    }


@dataclass
class PreviewRow:
    row_number: int
    payload: dict
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    fingerprint: str | None = None
    is_duplicate: bool = False
    existing_question_id: int | None = None


def preview_rows(db: Session, raw_rows: list[dict]) -> list[PreviewRow]:
    existing_fingerprints = {
        fp: qid for fp, qid in db.query(Question.fingerprint, Question.id).filter(Question.fingerprint.isnot(None))
    }
    previewed = []
    for idx, row in enumerate(raw_rows):
        row_number = idx + 2  # header is row 1
        payload = row_to_payload(row)
        result = validate_question(payload)
        fingerprint = None
        is_duplicate = False
        existing_id = None
        if result.valid:
            fingerprint = compute_fingerprint(
                payload["quiz_title"], payload["question_text"], [o.text for o in result.normalized_options]
            )
            existing_id = existing_fingerprints.get(fingerprint)
            is_duplicate = existing_id is not None
        previewed.append(
            PreviewRow(
                row_number=row_number,
                payload=payload,
                valid=result.valid,
                errors=[i.message for i in result.errors],
                warnings=[i.message for i in result.warnings],
                info=[i.message for i in result.info],
                fingerprint=fingerprint,
                is_duplicate=is_duplicate,
                existing_question_id=existing_id,
            )
        )
    return previewed


def confirm_import(
    db: Session,
    raw_rows: list[dict],
    *,
    duplicate_policy: str,
    source_filename: str,
) -> dict:
    """Re-validates every row from scratch (never trusts client-echoed
    validation state) and writes everything in one transaction. Any
    unexpected error rolls the whole import back."""
    if duplicate_policy not in {"skip", "update_draft"}:
        raise ValueError("duplicate_policy must be 'skip' or 'update_draft'")

    now = datetime.now(timezone.utc)
    created = 0
    updated = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    quizzes_by_title: dict[str, Quiz] = {}
    touched_quiz_ids: set[int] = set()

    try:
        for row in raw_rows:
            payload = row_to_payload(row)
            result = validate_question(payload)
            if not result.valid:
                skipped_invalid += 1
                continue

            option_texts = [o.text for o in result.normalized_options]
            fingerprint = compute_fingerprint(payload["quiz_title"], payload["question_text"], option_texts)
            existing = db.query(Question).filter(Question.fingerprint == fingerprint).first()

            if existing is not None:
                existing_quiz = db.get(Quiz, existing.quiz_id)
                if duplicate_policy == "skip":
                    skipped_duplicates += 1
                    continue
                if existing_quiz and existing_quiz.status == QUIZ_STATUS_PUBLISHED:
                    # Never silently overwrite a published question.
                    skipped_duplicates += 1
                    continue
                _apply_question_fields(existing, payload, result, fingerprint, now, source_filename)
                updated += 1
                touched_quiz_ids.add(existing.quiz_id)
                continue

            title = payload["quiz_title"]
            quiz = quizzes_by_title.get(title)
            if quiz is None:
                quiz = db.query(Quiz).filter(Quiz.title == title).first()
                if quiz is None:
                    quiz = Quiz(
                        title=title,
                        week_number=0,
                        status=QUIZ_STATUS_DRAFT,
                        editorial_status=EDITORIAL_STATUS_UNREVIEWED,
                        source_type=SOURCE_TYPE_SPREADSHEET_IMPORT,
                        quiz_purpose="practice",
                        # Matches the ExamCompass import convention: freshly
                        # imported, unreviewed content starts invisible to
                        # students. update_quiz() requires answer_keys_validated
                        # + editorial_status="validated" before any visibility
                        # flag (including practice library) can be enabled.
                        show_in_practice_library=False,
                        answer_keys_validated=False,
                    )
                    db.add(quiz)
                    db.flush()
                quizzes_by_title[title] = quiz
            touched_quiz_ids.add(quiz.id)

            question = Question(quiz_id=quiz.id, correct_answer=result.normalized_correct_answers[0])
            _apply_question_fields(question, payload, result, fingerprint, now, source_filename)
            db.add(question)
            created += 1

        for quiz_id in touched_quiz_ids:
            quiz = db.get(Quiz, quiz_id)
            if quiz is None:
                continue
            questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
            quiz.question_count = len(questions)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "created": created,
        "updated": updated,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
        "quiz_ids": sorted(touched_quiz_ids),
    }


def _apply_question_fields(question: Question, payload: dict, result, fingerprint: str, now, source_filename: str) -> None:
    options = result.normalized_options
    letters = "abcdefgh"
    for i, letter in enumerate(letters):
        setattr(question, f"option_{letter}", options[i].text if i < len(options) else None)
    question.question_text = payload["question_text"]
    question.correct_answer = result.normalized_correct_answers[0]
    question.correct_answers = (
        ",".join(result.normalized_correct_answers) if len(result.normalized_correct_answers) > 1 else None
    )
    question.explanation = payload["explanation"] or None
    question.difficulty = int(payload["difficulty"]) if str(payload["difficulty"] or "").isdigit() else None
    question.tags = payload["tags"] or None
    question.source = payload["source"] or SOURCE_TYPE_MANUAL
    question.fingerprint = fingerprint
    question.imported_at = now
    question.import_filename = source_filename
    question.flagged_for_review = False
    question.flag_reason = None
