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

from app.models.certification import (
    CertificationObjective,
    CertificationVersion,
    QuestionObjective,
    QuestionV2Meta,
)
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
from app.services.question_explanation_catalog import catalog_explanation
from app.services.verified_question_corrections import correction_for

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
    # --- Nexus V2 additive metadata (Phase 1A). All optional; files that omit
    # these columns import exactly as before. ---
    "certification",
    "certification_version",
    "domain",
    "module",
    "objective_code",
    "importance",
    "source_name",
    "source_url",
    "permission_status",
    # --- Nexus V2 free-form question grading metadata (Phase 1B). Only used
    # when question_type is short_answer / free_response; blank for MCQ rows.
    # Deterministic grading only — no AI. ---
    "acceptable_answers",
    "expected_concepts",
    "rubric",
    "rubric_version",
    "answer_match_mode",
    "min_concepts_for_pass",
    "partial_credit",
]

V2_IMPORTANCE_ALIASES = {"know_it": "working_knowledge"}
DEFAULT_PERMISSION_STATUS = "unknown"

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


def _structured_cell(value) -> str:
    """Control-char-stripped text for a cell that holds JSON / pipe-delimited
    structure. The formula-injection guard in sanitize_text() would corrupt a
    leading '[' -> "'[" ... actually only '=+-@'; but a pipe list like
    "-1|0|1" would gain a quote. Structured cells are parsed by the validator
    and never re-emitted into a spreadsheet, so we skip the '@=+-' prefixing
    and only remove control characters."""
    text = "" if value is None else str(value)
    return _CONTROL_CHARS_RE.sub("", text).strip()


def objective_codes(value) -> list[str]:
    """Return unique objective codes in authored order.

    The first value remains the primary compatibility objective; no later
    value is discarded.
    """
    if value in (None, ""):
        return []
    values = value if isinstance(value, (list, tuple)) else str(value).split(",")
    return list(dict.fromkeys(sanitize_text(item) for item in values if sanitize_text(item)))


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
    importance_raw = sanitize_text(row.get("importance")).lower()
    importance = V2_IMPORTANCE_ALIASES.get(importance_raw, importance_raw) or None
    permission_status = sanitize_text(row.get("permission_status")).lower() or DEFAULT_PERMISSION_STATUS
    objectives = objective_codes(row.get("objective_code"))
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
        # --- Nexus V2 additive metadata (Phase 1A) ---
        "certification": sanitize_text(row.get("certification")) or None,
        "certification_version": sanitize_text(row.get("certification_version")) or None,
        "domain": sanitize_text(row.get("domain")) or None,
        "module": sanitize_text(row.get("module")) or None,
        "objective_code": objectives[0] if objectives else None,
        "objective_codes": objectives,
        "importance": importance,
        "source_name": sanitize_text(row.get("source_name")) or None,
        "source_url": sanitize_text(row.get("source_url")) or None,
        "permission_status": permission_status,
        # --- V2 free-form grading metadata (Phase 1B). Raw structure; the
        # validator parses + normalizes it. ---
        "acceptable_answers": _structured_cell(row.get("acceptable_answers")) or None,
        "expected_concepts": _structured_cell(row.get("expected_concepts")) or None,
        "rubric": _structured_cell(row.get("rubric")) or None,
        "rubric_version": sanitize_text(row.get("rubric_version")) or None,
        "answer_match_mode": sanitize_text(row.get("answer_match_mode")).lower() or None,
        "min_concepts_for_pass": sanitize_text(row.get("min_concepts_for_pass")) or None,
        "partial_credit": sanitize_text(row.get("partial_credit")) or None,
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
        objective_errors = _objective_validation_errors(db, payload)
        fingerprint = None
        is_duplicate = False
        existing_id = None
        if result.valid and not objective_errors:
            fingerprint = compute_fingerprint(
                payload["quiz_title"], payload["question_text"], [o.text for o in result.normalized_options]
            )
            existing_id = existing_fingerprints.get(fingerprint)
            is_duplicate = existing_id is not None
        previewed.append(
            PreviewRow(
                row_number=row_number,
                payload=payload,
                valid=result.valid and not objective_errors,
                errors=[i.message for i in result.errors] + objective_errors,
                warnings=[i.message for i in result.warnings],
                info=[i.message for i in result.info],
                fingerprint=fingerprint,
                is_duplicate=is_duplicate,
                existing_question_id=existing_id,
            )
        )
    return previewed


def _objective_validation_errors(db: Session, payload: dict) -> list[str]:
    codes = payload.get("objective_codes") or []
    version_key = payload.get("certification_version")
    if not codes:
        return []
    version = (
        db.query(CertificationVersion).filter_by(version_key=version_key).one_or_none()
        if version_key
        else None
    )
    # Preserve legacy single-objective imports whose hierarchy is not loaded.
    # Multi-objective rows cannot be losslessly persisted without a resolved
    # version and therefore fail explicitly.
    if version is None:
        return (
            [f"Multiple objectives require a loaded certification version; {version_key!r} was not found."]
            if len(codes) > 1
            else []
        )
    found = {
        code
        for (code,) in db.query(CertificationObjective.objective_code).filter(
            CertificationObjective.certification_version_id == version.id,
            CertificationObjective.objective_code.in_(codes),
        )
    }
    missing = [code for code in codes if code not in found]
    return [
        f"Objective {code!r} is not defined for certification version {version_key!r}."
        for code in missing
    ]


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
    unchanged = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    quizzes_by_title: dict[str, Quiz] = {}
    touched_quiz_ids: set[int] = set()

    # Resolve the V2 certification-version FK when the version_key names a
    # loaded version. An unknown/blank key is fine — the string metadata is
    # still recorded and the FK stays NULL.
    version_id_by_key = {
        key: vid
        for key, vid in db.query(CertificationVersion.version_key, CertificationVersion.id)
    }

    try:
        for row in raw_rows:
            payload = row_to_payload(row)
            result = validate_question(payload)
            if not result.valid or _objective_validation_errors(db, payload):
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
                content_changed = _apply_question_fields(
                    existing, payload, result, fingerprint, now, source_filename,
                    stamp_import=False,
                )
                db.flush()
                meta_changed = _upsert_question_v2_meta(
                    db, existing.id, payload, version_id_by_key, result
                )
                if content_changed or meta_changed:
                    # Only re-stamp import provenance when something actually
                    # changed — an unchanged re-import must stay a true no-op.
                    existing.imported_at = now
                    existing.import_filename = source_filename
                    updated += 1
                    touched_quiz_ids.add(existing.quiz_id)
                else:
                    unchanged += 1
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
            _apply_question_fields(
                question, payload, result, fingerprint, now, source_filename,
                stamp_import=True,
            )
            db.add(question)
            db.flush()
            _upsert_question_v2_meta(db, question.id, payload, version_id_by_key, result)
            created += 1

        for quiz_id in touched_quiz_ids:
            quiz = db.get(Quiz, quiz_id)
            if quiz is None:
                continue
            questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
            quiz.question_count = len(questions)
            # Any changed bank must pass editorial review again. A separate,
            # hash-bound content approval may promote it immediately after
            # import, but the importer itself never carries approval forward.
            quiz.editorial_status = EDITORIAL_STATUS_UNREVIEWED
            quiz.answer_keys_validated = False
            quiz.explanations_complete = False

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
        "quiz_ids": sorted(touched_quiz_ids),
    }


def _diff_set(row, fields: dict) -> bool:
    """Assign only attributes that differ; return True if anything changed.
    Keeps a re-import that carries identical data a true no-op (the ORM row
    never goes dirty, so ``updated_at`` / import stamps don't move)."""
    changed = False
    for key, value in fields.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    return changed


def _upsert_question_v2_meta(
    db,
    question_id: int,
    payload: dict,
    version_id_by_key: dict[str, int] | None,
    result=None,
) -> bool:
    """Create/refresh the companion ``question_v2_meta`` row for one question.
    Returns True if the row was created or any field actually changed.

    The legacy ``questions`` row is never touched by V2 metadata — this keeps
    historical data-migrations that INSERT questions via the current ORM
    working against an un-upgraded schema.
    """
    version_key = payload.get("certification_version")
    version_id = (version_id_by_key or {}).get(version_key) if version_key else None

    meta = db.query(QuestionV2Meta).filter(QuestionV2Meta.question_id == question_id).one_or_none()
    is_new = meta is None
    if is_new:
        meta = QuestionV2Meta(question_id=question_id)
        db.add(meta)

    fields = {
        "certification": payload.get("certification"),
        "certification_version": version_key,
        "certification_version_id": version_id,
        "domain": payload.get("domain"),
        "module": payload.get("module"),
        "objective_code": payload.get("objective_code"),
        "importance": payload.get("importance"),
        "source_name": payload.get("source_name"),
        "source_url": payload.get("source_url"),
        "permission_status": payload.get("permission_status") or DEFAULT_PERMISSION_STATUS,
    }

    # --- V2 free-form grading metadata. Deterministic-only; NO AI. Populated
    # from the validation result so authoring/import share one normalizer. ---
    if result is not None and getattr(result, "is_freeform", False):
        fields.update(
            question_type=result.question_type,
            acceptable_answers=list(result.acceptable_answers),
            expected_concepts=list(result.expected_concepts),
            rubric=dict(result.rubric),
            rubric_version=result.rubric_version,
            answer_match_mode=result.answer_match_mode,
            min_concepts_for_pass=result.min_concepts_for_pass,
            partial_credit=result.partial_credit,
        )
    elif result is not None and result.question_type:
        fields["question_type"] = result.question_type

    changed = _diff_set(meta, fields)
    db.flush()

    codes = list(payload.get("objective_codes") or [])
    desired: list[tuple[int, int]] = []
    if version_id and codes:
        objective_by_code = {
            objective.objective_code: objective.id
            for objective in db.query(CertificationObjective).filter(
                CertificationObjective.certification_version_id == version_id,
                CertificationObjective.objective_code.in_(codes),
            )
        }
        desired = [(objective_by_code[code], position) for position, code in enumerate(codes)]

    existing = (
        db.query(QuestionObjective)
        .filter_by(question_v2_meta_id=meta.id)
        .order_by(QuestionObjective.position)
        .all()
    )
    if [(link.objective_id, link.position) for link in existing] != desired:
        for link in existing:
            db.delete(link)
        db.flush()
        for objective_id, position in desired:
            db.add(
                QuestionObjective(
                    question_v2_meta_id=meta.id,
                    objective_id=objective_id,
                    position=position,
                )
            )
        changed = True
    return is_new or changed


def _apply_question_fields(
    question: Question,
    payload: dict,
    result,
    fingerprint: str,
    now,
    source_filename: str,
    *,
    stamp_import: bool,
) -> bool:
    """Apply the legacy ``questions`` columns for one imported row.

    Returns True if any meaningful field (options / text / answer / explanation
    / difficulty / tags / source / fingerprint / review flags) differs from
    what is already stored. Volatile provenance stamps (``imported_at`` /
    ``import_filename``) are written here only for a brand-new row
    (``stamp_import=True``); for an existing row the caller stamps them only
    when this function (or the V2-meta upsert) reported a change, so an
    unchanged re-import stays a true no-op.
    """
    options = result.normalized_options
    letters = "abcdefgh"
    is_freeform = bool(getattr(result, "is_freeform", False))

    fields: dict = {}
    for i, letter in enumerate(letters):
        fields[f"option_{letter}"] = options[i].text if i < len(options) else None
    if is_freeform:
        # questions.option_a is NOT NULL. A free-form question has no options;
        # store an empty string. The real answer data is in question_v2_meta.
        fields["option_a"] = ""

    correction = correction_for(payload["question_text"])
    corrected_answers = [correction.correct_answer] if correction else result.normalized_correct_answers
    fields["question_text"] = payload["question_text"]
    fields["correct_answer"] = corrected_answers[0]
    fields["correct_answers"] = (
        ",".join(corrected_answers) if len(corrected_answers) > 1 else None
    )
    fields["explanation"] = (
        correction.explanation if correction else payload["explanation"]
    ) or catalog_explanation(
        payload["question_text"],
        [option.text for option in options] + [""] * (8 - len(options)),
        corrected_answers,
    )
    fields["difficulty"] = (
        int(payload["difficulty"]) if str(payload["difficulty"] or "").isdigit() else None
    )
    fields["tags"] = payload["tags"] or None
    fields["source"] = payload["source"] or SOURCE_TYPE_MANUAL
    fields["fingerprint"] = fingerprint
    fields["flagged_for_review"] = False
    fields["flag_reason"] = None

    changed = _diff_set(question, fields)

    if stamp_import or changed:
        question.imported_at = now
        question.import_filename = source_filename
    # V2 metadata is written separately into question_v2_meta by
    # _upsert_question_v2_meta — never onto this legacy row.
    return changed
