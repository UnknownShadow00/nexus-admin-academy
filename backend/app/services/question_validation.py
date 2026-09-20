"""Canonical question validation shared by manual authoring, the ExamCompass
importer, and the CSV/XLSX importer. Operates on a plain-dict question payload
so every entry point (a Question ORM row, a spreadsheet row, an admin form
submission) can be normalized through the exact same rules.

Nothing here writes to the database. Callers decide what to do with the
result: block a save, save as draft, or publish.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.models.certification import (
    FREEFORM_CORRECT_ANSWER_SENTINEL,
    QUESTION_TYPE_FREE_RESPONSE,
    QUESTION_TYPE_SHORT_ANSWER,
    V2_FREEFORM_QUESTION_TYPES,
)

LETTERS = "ABCDEFGH"
MAX_OPTIONS = len(LETTERS)

QUESTION_TYPE_SINGLE = "single"
QUESTION_TYPE_MULTI = "multi"
QUESTION_TYPE_TRUE_FALSE = "true_false"
SUPPORTED_QUESTION_TYPES = {QUESTION_TYPE_SINGLE, QUESTION_TYPE_MULTI, QUESTION_TYPE_TRUE_FALSE}

# The MCQ types above are auto-graded. The V2 free-form types are graded
# deterministically-first (see app.services.deterministic_grader); this
# validator accepts them but routes them down a separate, options-free path.
ALL_QUESTION_TYPES = SUPPORTED_QUESTION_TYPES | V2_FREEFORM_QUESTION_TYPES
ANSWER_MATCH_MODES = {"normalized", "exact"}

# Nexus V2 additive metadata vocabularies (Phase 1A). Validated only when the
# corresponding key is present and non-blank in the payload — legacy imports
# that omit these columns are unaffected. short_answer / free_response question
# types are intentionally deferred to Phase 1B (see the Phase 1A note); this
# validator still only accepts the automatically graded types above.
V2_IMPORTANCE_VALUES = {"job_critical", "working_knowledge", "awareness"}
V2_IMPORTANCE_ALIASES = {"know_it": "working_knowledge"}
V2_PERMISSION_STATUS_VALUES = {"owned", "permitted", "requested", "unknown", "denied"}

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8,
}
_SELECT_N_PATTERN = re.compile(
    r"select\s+(\d+|one|two|three|four|five|six|seven|eight)\s+answers?", re.IGNORECASE
)


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: str  # "error" | "warning" | "info"

    def to_dict(self) -> dict:
        return {"field": self.field, "message": self.message, "severity": self.severity}


@dataclass
class NormalizedOption:
    label: str
    text: str


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    info: list[ValidationIssue] = field(default_factory=list)
    question_type: str | None = None
    normalized_options: list[NormalizedOption] = field(default_factory=list)
    normalized_correct_answers: list[str] = field(default_factory=list)
    # --- V2 free-form grading metadata (only populated for short_answer /
    # free_response). Deterministic-only; no AI. ---
    is_freeform: bool = False
    acceptable_answers: list[str] = field(default_factory=list)
    expected_concepts: list = field(default_factory=list)
    rubric: dict = field(default_factory=dict)
    rubric_version: str | None = None
    answer_match_mode: str = "normalized"
    min_concepts_for_pass: int | None = None
    partial_credit: bool = True

    @property
    def all_issues(self) -> list[ValidationIssue]:
        return [*self.errors, *self.warnings, *self.info]

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "question_type": self.question_type,
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "normalized_options": [{"label": o.label, "text": o.text} for o in self.normalized_options],
            "normalized_correct_answers": self.normalized_correct_answers,
            "is_freeform": self.is_freeform,
            "acceptable_answers": self.acceptable_answers,
            "expected_concepts": self.expected_concepts,
            "rubric": self.rubric,
            "rubric_version": self.rubric_version,
        }


def _extract_raw_options(payload: dict) -> list[str | None]:
    """Accept either payload["options"] (ordered list) or option_a..option_h keys."""
    if payload.get("options") is not None:
        return list(payload["options"])[:MAX_OPTIONS]
    return [payload.get(f"option_{letter.lower()}") for letter in LETTERS]


def _extract_raw_correct_answers(payload: dict) -> list[str]:
    """Accept a list, a comma/pipe-delimited string, or a single letter."""
    raw = payload.get("correct_answers")
    if raw is None:
        raw = payload.get("correct_answer")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        items = [str(item) for item in raw]
    else:
        items = re.split(r"[|,]", str(raw))
    return [item.strip().upper() for item in items if item.strip()]


def _parse_list_cell(raw) -> list:
    """Parse a spreadsheet cell holding a list: a JSON array, or a
    pipe-delimited string, or an already-parsed list. Returns [] for blank."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [x for x in raw]
    text = str(raw).strip()
    if not text:
        return []
    if text[0] in "[{":
        try:
            parsed = json.loads(text)
        except ValueError:
            return []  # caller treats empty result as "missing / unparseable"
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    return [part.strip() for part in text.split("|") if part.strip()]


def _parse_object_cell(raw) -> tuple[dict, bool]:
    """Parse a cell holding a JSON object. Returns (obj, ok). Blank -> ({}, True)."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return {}, True
    if isinstance(raw, dict):
        return raw, True
    try:
        parsed = json.loads(str(raw))
    except ValueError:
        return {}, False
    return (parsed, True) if isinstance(parsed, dict) else ({}, False)


def _validate_additive_metadata(payload: dict, errors: list[ValidationIssue]) -> None:
    if "importance" in payload:
        importance_raw = str(payload.get("importance") or "").strip().lower()
        importance = V2_IMPORTANCE_ALIASES.get(importance_raw, importance_raw)
        if importance and importance not in V2_IMPORTANCE_VALUES:
            errors.append(
                ValidationIssue(
                    "importance",
                    f"Importance '{payload.get('importance')}' is not valid "
                    f"(expected one of {sorted(V2_IMPORTANCE_VALUES)}).",
                    "error",
                )
            )
    if "permission_status" in payload:
        permission_raw = str(payload.get("permission_status") or "").strip().lower()
        if permission_raw and permission_raw not in V2_PERMISSION_STATUS_VALUES:
            errors.append(
                ValidationIssue(
                    "permission_status",
                    f"Permission status '{payload.get('permission_status')}' is not valid "
                    f"(expected one of {sorted(V2_PERMISSION_STATUS_VALUES)}).",
                    "error",
                )
            )


def _validate_freeform(payload: dict, question_type: str) -> ValidationResult:
    """Validate a short_answer / free_response question. No options, no
    correct-answer letters. Grading data is stored for deterministic (and,
    later, AI/manual) grading — this function never judges a student answer."""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    question_text = str(payload.get("question_text") or "").strip()
    if not question_text:
        errors.append(ValidationIssue("question_text", "Question text is missing.", "error"))

    acceptable_answers = [str(a).strip() for a in _parse_list_cell(payload.get("acceptable_answers")) if str(a).strip()]
    expected_concepts = _parse_list_cell(payload.get("expected_concepts"))
    rubric, rubric_ok = _parse_object_cell(payload.get("rubric"))
    if not rubric_ok:
        errors.append(ValidationIssue("rubric", "Rubric must be a JSON object or left blank.", "error"))

    if question_type == QUESTION_TYPE_SHORT_ANSWER and not acceptable_answers:
        errors.append(
            ValidationIssue(
                "acceptable_answers",
                "A short_answer question needs at least one acceptable answer "
                "(JSON array or pipe-delimited).",
                "error",
            )
        )
    if question_type == QUESTION_TYPE_FREE_RESPONSE and not expected_concepts:
        errors.append(
            ValidationIssue(
                "expected_concepts",
                "A free_response question needs at least one expected concept "
                "(JSON array or pipe-delimited).",
                "error",
            )
        )

    match_mode = str(payload.get("answer_match_mode") or "normalized").strip().lower() or "normalized"
    if match_mode not in ANSWER_MATCH_MODES:
        errors.append(
            ValidationIssue(
                "answer_match_mode",
                f"answer_match_mode '{payload.get('answer_match_mode')}' is not valid "
                f"(expected one of {sorted(ANSWER_MATCH_MODES)}).",
                "error",
            )
        )
        match_mode = "normalized"

    min_concepts = payload.get("min_concepts_for_pass")
    min_concepts_int: int | None = None
    if min_concepts not in (None, ""):
        try:
            min_concepts_int = int(min_concepts)
        except (TypeError, ValueError):
            errors.append(
                ValidationIssue("min_concepts_for_pass", "Must be a whole number.", "error")
            )

    partial_credit = payload.get("partial_credit")
    partial_credit_bool = (
        True
        if partial_credit in (None, "")
        else str(partial_credit).strip().lower() in {"true", "yes", "y", "1"}
    )

    _validate_additive_metadata(payload, errors)

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        info=[],
        question_type=question_type,
        normalized_options=[],
        # The importer writes this sentinel into the legacy NOT NULL
        # questions.correct_answer; real grading data is the fields below.
        normalized_correct_answers=[FREEFORM_CORRECT_ANSWER_SENTINEL],
        is_freeform=True,
        acceptable_answers=acceptable_answers,
        expected_concepts=expected_concepts,
        rubric=rubric,
        rubric_version=str(payload.get("rubric_version") or "").strip() or None,
        answer_match_mode=match_mode,
        min_concepts_for_pass=min_concepts_int,
        partial_credit=partial_credit_bool,
    )


def _parse_select_n(question_text: str) -> int | None:
    match = _SELECT_N_PATTERN.search(question_text or "")
    if not match:
        return None
    token = match.group(1).lower()
    if token.isdigit():
        return int(token)
    return _WORD_NUMBERS.get(token)


def validate_question(payload: dict, *, require_explanation: bool = False) -> ValidationResult:
    """Validate + normalize a single question payload.

    ``payload`` fields (all optional except question_text / options /
    correct_answers):
      - question_text: str
      - options: list[str] OR option_a..option_h: str
      - correct_answers: list[str] OR "A,C,E" OR "A|C|E" OR correct_answer: "A"
      - question_type: "single" | "multi" | "true_false" (inferred if omitted)
      - explanation: str | None
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    info: list[ValidationIssue] = []

    declared_type = payload.get("question_type")
    if declared_type in V2_FREEFORM_QUESTION_TYPES:
        return _validate_freeform(payload, declared_type)

    question_text = str(payload.get("question_text") or "").strip()
    if not question_text:
        errors.append(ValidationIssue("question_text", "Question text is missing.", "error"))

    if declared_type is not None and declared_type not in SUPPORTED_QUESTION_TYPES:
        errors.append(
            ValidationIssue(
                "question_type",
                f"'{declared_type}' is not a supported question type "
                f"(expected one of {sorted(SUPPORTED_QUESTION_TYPES)}).",
                "error",
            )
        )
        declared_type = None

    raw_options = _extract_raw_options(payload)
    normalized_options: list[NormalizedOption] = []
    seen_text: dict[str, str] = {}  # casefolded text -> first label that used it
    raw_letters_kept: list[str] = []  # original letters that survived (for remapping correct answers)

    for idx, raw_text in enumerate(raw_options):
        original_letter = LETTERS[idx]
        text = (raw_text or "").strip()
        if not text:
            if raw_text is not None and raw_text != "":
                # whitespace-only, distinct from simply absent
                info.append(
                    ValidationIssue(
                        f"option_{original_letter.lower()}",
                        f"Option {original_letter} is blank and will not be imported.",
                        "info",
                    )
                )
            continue
        key = text.casefold()
        if key in seen_text:
            dup_of = seen_text[key]
            warnings.append(
                ValidationIssue(
                    f"option_{original_letter.lower()}",
                    f"Options {dup_of} and {original_letter} contain duplicate text.",
                    "warning",
                )
            )
        else:
            seen_text[key] = original_letter
        new_label = LETTERS[len(normalized_options)]
        normalized_options.append(NormalizedOption(label=new_label, text=text))
        raw_letters_kept.append(original_letter)

    if not normalized_options:
        errors.append(ValidationIssue("options", "This question has no valid (non-blank) options.", "error"))
    elif len(normalized_options) < 2:
        errors.append(
            ValidationIssue("options", "A choice-based question needs at least two valid options.", "error")
        )

    # Map original letters -> new (gap-free) labels for correct-answer remapping.
    original_to_new = dict(zip(raw_letters_kept, (opt.label for opt in normalized_options)))

    raw_correct = _extract_raw_correct_answers(payload)
    if not raw_correct:
        errors.append(ValidationIssue("correct_answers", "No correct answer is recorded for this question.", "error"))

    normalized_correct: list[str] = []
    seen_correct: set[str] = set()
    for letter in raw_correct:
        if letter in seen_correct:
            errors.append(
                ValidationIssue("correct_answers", f"Correct answer '{letter}' is listed more than once.", "error")
            )
            continue
        seen_correct.add(letter)
        if letter not in original_to_new:
            errors.append(
                ValidationIssue(
                    "correct_answers", f"Correct answer reference '{letter}' does not match a valid option.", "error"
                )
            )
            continue
        normalized_correct.append(original_to_new[letter])

    # Infer question type if not declared.
    question_type = declared_type
    if question_type is None:
        if len(normalized_options) == 2 and {o.text.strip().lower() for o in normalized_options} == {"true", "false"}:
            question_type = QUESTION_TYPE_TRUE_FALSE
        elif len(normalized_correct) > 1:
            question_type = QUESTION_TYPE_MULTI
        else:
            question_type = QUESTION_TYPE_SINGLE

    if question_type in (QUESTION_TYPE_SINGLE, QUESTION_TYPE_TRUE_FALSE) and len(normalized_correct) > 1:
        errors.append(
            ValidationIssue(
                "correct_answers",
                f"This is a single-choice question but {len(normalized_correct)} correct answers are stored.",
                "error",
            )
        )
    if question_type == QUESTION_TYPE_MULTI and len(normalized_correct) < 2:
        errors.append(
            ValidationIssue(
                "correct_answers",
                "Multi-select questions need at least two correct answers.",
                "error",
            )
        )

    select_n = _parse_select_n(question_text)
    if select_n is not None and normalized_correct and select_n != len(normalized_correct):
        errors.append(
            ValidationIssue(
                "question_text",
                f"This question says Select {select_n}, but {len(normalized_correct)} correct answer(s) are stored.",
                "error",
            )
        )

    explanation = str(payload.get("explanation") or "").strip()
    if require_explanation and not explanation:
        errors.append(
            ValidationIssue("explanation", "An explanation is required before this question can be published.", "error")
        )

    # --- V2 additive metadata validation (only when present) ---------------
    _validate_additive_metadata(payload, errors)

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        info=info,
        question_type=question_type,
        normalized_options=normalized_options,
        normalized_correct_answers=normalized_correct,
    )


def validate_question_row(question) -> ValidationResult:
    """Validate an existing `Question` ORM row (used by the audit and by
    publishing safeguards). Does not require an explanation by default —
    that's a publish-time policy decision made by the caller."""
    payload = {
        "question_text": question.question_text,
        "option_a": question.option_a,
        "option_b": question.option_b,
        "option_c": question.option_c,
        "option_d": question.option_d,
        "option_e": question.option_e,
        "option_f": question.option_f,
        "option_g": question.option_g,
        "option_h": question.option_h,
        "correct_answers": question.correct_answers or question.correct_answer,
        "explanation": question.explanation,
    }
    return validate_question(payload)
