"""Canonical question validation shared by manual authoring, the ExamCompass
importer, and the CSV/XLSX importer. Operates on a plain-dict question payload
so every entry point (a Question ORM row, a spreadsheet row, an admin form
submission) can be normalized through the exact same rules.

Nothing here writes to the database. Callers decide what to do with the
result: block a save, save as draft, or publish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

LETTERS = "ABCDEFGH"
MAX_OPTIONS = len(LETTERS)

QUESTION_TYPE_SINGLE = "single"
QUESTION_TYPE_MULTI = "multi"
QUESTION_TYPE_TRUE_FALSE = "true_false"
SUPPORTED_QUESTION_TYPES = {QUESTION_TYPE_SINGLE, QUESTION_TYPE_MULTI, QUESTION_TYPE_TRUE_FALSE}

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

    question_text = str(payload.get("question_text") or "").strip()
    if not question_text:
        errors.append(ValidationIssue("question_text", "Question text is missing.", "error"))

    declared_type = payload.get("question_type")
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
