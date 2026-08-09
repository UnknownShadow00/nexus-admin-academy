"""Stable, source-independent explanation overrides for reviewed questions."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "question_explanations.json"


def question_signature(
    question_text: str,
    options: list[str],
    correct_answers: list[str],
) -> str:
    normalized = json.dumps(
        {
            "question": " ".join((question_text or "").split()).casefold(),
            "options": [" ".join((option or "").split()).casefold() for option in options],
            "correct_answers": sorted(answer.strip().upper() for answer in correct_answers),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_question_explanations() -> dict[str, str]:
    if not CATALOG_PATH.exists():
        return {}
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    entries = raw.get("explanations", {}) if isinstance(raw, dict) else {}
    return {
        signature: explanation.strip()
        for signature, explanation in entries.items()
        if isinstance(signature, str)
        and isinstance(explanation, str)
        and explanation.strip()
    }


def catalog_explanation(
    question_text: str,
    options: list[str],
    correct_answers: list[str],
) -> str | None:
    signature = question_signature(question_text, options, correct_answers)
    return load_question_explanations().get(signature)
