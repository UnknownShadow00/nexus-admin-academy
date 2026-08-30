"""Deterministic, no-AI grading for V2 short-answer and free-response questions
(Phase 1B).

Design rules (content standard §8, PRD §12):

* Grade order is deterministic FIRST. This module is that first step.
* It is honest about its limits: when it cannot confidently decide, it returns
  ``status = "needs_review"`` — a state suitable for later AI or mentor
  grading — instead of guessing a confident pass/fail on ambiguous prose.
* It never calls a model, never touches the database, and is a pure function
  of its inputs, so its output is reproducible and testable.

Return shape (both graders):

    {
      "status": "graded" | "needs_review",
      "score": float in [0, 1],            # provisional if needs_review
      "passed": bool | None,               # None when needs_review
      "method": "<how it was decided>",
      "matched": [...],                    # matched answers / concepts
      "missing": [...],                    # missing concepts (free-response)
      "rubric_version": str | None,
      "detail": "<human-readable one-liner>",
    }
"""

from __future__ import annotations

import re
import unicodedata

from app.models.certification import GRADE_STATUS_GRADED, GRADE_STATUS_NEEDS_REVIEW

_PUNCT_EDGE = re.compile(r"^[\s\.,;:!?\"'`)\]}]+|[\s\.,;:!?\"'`([{]+$")
_WS = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Lower-case, strip accents, collapse whitespace, trim edge punctuation."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = _WS.sub(" ", text)
    text = _PUNCT_EDGE.sub("", text)
    return text.strip()


def _tokens(value: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", normalize_text(value)) if t]


def _contains_phrase(haystack_norm: str, needle: str) -> bool:
    """Whole-token substring match: the needle's tokens appear contiguously."""
    needle_norm = normalize_text(needle)
    if not needle_norm:
        return False
    # Word-boundary-aware contiguous match.
    pattern = r"(?<![a-z0-9])" + re.escape(needle_norm).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, haystack_norm) is not None


# --------------------------------------------------------------------------- #
# Short answer
# --------------------------------------------------------------------------- #

# A response longer than this many tokens is not a "short answer" — the
# deterministic exact/synonym check cannot be trusted to judge it, so it goes
# to review rather than being marked wrong.
_SHORT_ANSWER_MAX_TOKENS = 12


def grade_short_answer(
    response: str,
    acceptable_answers: list[str],
    *,
    match_mode: str = "normalized",
    rubric_version: str | None = None,
) -> dict:
    """Match a terse response against a curated accepted-answer list.

    ``normalized`` (default): case/space/accent/edge-punctuation-insensitive
    equality, OR the accepted answer appearing as a whole phrase inside a
    short response.
    ``exact``: byte-for-byte equality after ``strip()`` only.
    """
    accepted = [a for a in (acceptable_answers or []) if str(a).strip()]
    raw = (response or "").strip()

    if not accepted:
        return _result(
            GRADE_STATUS_NEEDS_REVIEW, 0.0, None, "no_acceptable_answers",
            detail="No acceptable answers configured; needs review.",
            rubric_version=rubric_version,
        )
    if not raw:
        return _result(
            GRADE_STATUS_GRADED, 0.0, False, "empty_response",
            detail="Empty response.", rubric_version=rubric_version,
        )

    if match_mode == "exact":
        hit = next((a for a in accepted if raw == str(a).strip()), None)
        if hit is not None:
            return _result(
                GRADE_STATUS_GRADED, 1.0, True, "exact_match",
                matched=[hit], detail=f"Exact match: {hit!r}.",
                rubric_version=rubric_version,
            )
        return _result(
            GRADE_STATUS_NEEDS_REVIEW, 0.0, None, "exact_no_match",
            detail="No exact match; needs review.", rubric_version=rubric_version,
        )

    response_norm = normalize_text(raw)
    for answer in accepted:
        if normalize_text(answer) == response_norm:
            return _result(
                GRADE_STATUS_GRADED, 1.0, True, "normalized_equal",
                matched=[answer], detail=f"Answer matches {answer!r}.",
                rubric_version=rubric_version,
            )

    if len(_tokens(raw)) <= _SHORT_ANSWER_MAX_TOKENS:
        for answer in accepted:
            if _contains_phrase(response_norm, answer):
                return _result(
                    GRADE_STATUS_GRADED, 1.0, True, "normalized_phrase",
                    matched=[answer],
                    detail=f"Response contains the accepted answer {answer!r}.",
                    rubric_version=rubric_version,
                )
        # Short, curated question, short response, still no match -> confident wrong.
        return _result(
            GRADE_STATUS_GRADED, 0.0, False, "short_no_match",
            detail="Short response did not match any accepted answer.",
            rubric_version=rubric_version,
        )

    # Long / rambling response to a short-answer question: don't guess.
    return _result(
        GRADE_STATUS_NEEDS_REVIEW, 0.0, None, "response_too_long_for_exact_match",
        detail="Response is longer than a short answer; needs review.",
        rubric_version=rubric_version,
    )


# --------------------------------------------------------------------------- #
# Free response (scenario)
# --------------------------------------------------------------------------- #

_TRIVIAL_MAX_TOKENS = 3


def grade_free_response(
    response: str,
    expected_concepts: list,
    *,
    rubric: dict | None = None,
    rubric_version: str | None = None,
    min_concepts_for_pass: int | None = None,
    partial_credit: bool = True,
) -> dict:
    """Concept-coverage grading. Each expected concept may be a plain string or
    ``{"concept": str, "aliases": [str, ...], "weight": float}``. A concept is
    matched if the concept term or any alias appears (whole-phrase) in the
    normalized response.

    It NEVER emits a confident non-zero/zero pass on prose it cannot judge:

    * all concepts matched (>= threshold)      -> graded, pass
    * some matched, partial_credit on, >= 1     -> graded, partial score
    * some matched but below threshold, no PC   -> needs_review
    * none matched, non-trivial response        -> needs_review (could be phrased
                                                   differently — don't guess)
    * trivial/empty response                    -> graded, 0 (safe)
    """
    concepts = _normalize_concepts(expected_concepts)
    raw = (response or "").strip()

    if not concepts:
        return _result(
            GRADE_STATUS_NEEDS_REVIEW, 0.0, None, "no_expected_concepts",
            missing=[], detail="No expected concepts configured; needs review.",
            rubric_version=rubric_version,
        )

    if len(_tokens(raw)) <= _TRIVIAL_MAX_TOKENS:
        return _result(
            GRADE_STATUS_GRADED, 0.0, False, "trivial_response",
            missing=[c["concept"] for c in concepts],
            detail="Response too short to address the scenario.",
            rubric_version=rubric_version,
        )

    response_norm = normalize_text(raw)
    matched: list[str] = []
    missing: list[str] = []
    for concept in concepts:
        terms = [concept["concept"], *concept.get("aliases", [])]
        if any(_contains_phrase(response_norm, t) for t in terms if t):
            matched.append(concept["concept"])
        else:
            missing.append(concept["concept"])

    total = len(concepts)
    threshold = min_concepts_for_pass if min_concepts_for_pass is not None else total
    score = round(len(matched) / total, 4) if total else 0.0

    if len(matched) >= threshold:
        return _result(
            GRADE_STATUS_GRADED, 1.0 if len(matched) == total else score, True,
            "concepts_met_threshold", matched=matched, missing=missing,
            detail=f"Matched {len(matched)}/{total} expected concepts (threshold {threshold}).",
            rubric_version=rubric_version,
        )

    if matched and partial_credit:
        return _result(
            GRADE_STATUS_GRADED, score, False, "partial_concepts",
            matched=matched, missing=missing,
            detail=f"Partial: matched {len(matched)}/{total} concepts (below threshold {threshold}).",
            rubric_version=rubric_version,
        )

    if matched:  # below threshold and partial credit disabled
        return _result(
            GRADE_STATUS_NEEDS_REVIEW, score, None, "below_threshold_no_partial",
            matched=matched, missing=missing,
            detail="Some concepts present but below pass threshold; needs review.",
            rubric_version=rubric_version,
        )

    # Nothing matched, but the student clearly wrote something — do not
    # confidently fail prose the deterministic matcher may simply not
    # recognise. Hand it to AI/mentor later.
    return _result(
        GRADE_STATUS_NEEDS_REVIEW, 0.0, None, "no_concepts_matched_nontrivial",
        matched=[], missing=missing,
        detail="No expected concept matched a non-trivial response; needs review.",
        rubric_version=rubric_version,
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _normalize_concepts(expected_concepts) -> list[dict]:
    out: list[dict] = []
    for item in expected_concepts or []:
        if isinstance(item, str):
            if item.strip():
                out.append({"concept": item.strip(), "aliases": [], "weight": 1.0})
        elif isinstance(item, dict):
            concept = str(item.get("concept") or item.get("name") or "").strip()
            if not concept:
                continue
            aliases = [str(a).strip() for a in (item.get("aliases") or []) if str(a).strip()]
            weight = float(item.get("weight", 1.0) or 1.0)
            out.append({"concept": concept, "aliases": aliases, "weight": weight})
    return out


def _result(
    status: str,
    score: float,
    passed: bool | None,
    method: str,
    *,
    matched: list | None = None,
    missing: list | None = None,
    detail: str = "",
    rubric_version: str | None = None,
) -> dict:
    return {
        "status": status,
        "score": float(score),
        "passed": passed,
        "method": method,
        "matched": matched or [],
        "missing": missing or [],
        "rubric_version": rubric_version,
        "detail": detail,
    }
