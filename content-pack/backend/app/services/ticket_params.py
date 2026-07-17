"""TB-05: deterministic per-student ticket parameter resolution.

Design (backlog TB-05): no new table. Ticket.parameters holds
    {"placeholders": {"USERNAME": ["mfields", "tnguyen", ...], ...}}
and the value for a student is options[student_id % len(options)] — stable,
storage-free, and different across a five-student cohort for any options
list of length ≥ 5 (or co-prime spread otherwise).

Anchors/model answers must be written parameter-aware ("the correct account"),
so substitution never changes scoring semantics — enforced by content review,
noted in the authoring guide.
"""
from __future__ import annotations

import re

_PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def resolve_parameters(parameters: dict | None, student_id: int) -> dict[str, str]:
    placeholders = (parameters or {}).get("placeholders") or {}
    resolved: dict[str, str] = {}
    for name, options in placeholders.items():
        if isinstance(options, list) and options:
            resolved[str(name)] = str(options[student_id % len(options)])
    return resolved


def substitute(text: str | None, values: dict[str, str]) -> str | None:
    if not text or not values:
        return text
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), text)


def substitute_list(items: list | None, values: dict[str, str]) -> list:
    return [substitute(str(item), values) for item in (items or [])]
