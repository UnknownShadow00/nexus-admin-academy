"""Exact, dependency-free constraint selection for small V2 question banks."""

from __future__ import annotations

import random
from functools import lru_cache


class ConstraintSelectionError(ValueError):
    """A blueprint cannot be satisfied by its eligible question bank."""


def _matches_category(item: dict, requirement: dict) -> bool:
    item_id = str(item.get("id") or "")
    tags = {str(value) for value in item.get("tags") or []}
    ids = {
        str(value)
        for field in ("question_ids", "pool")
        for value in requirement.get(field) or []
    }
    wanted_tags = {str(value) for value in requirement.get("tags_any") or []}
    return item_id in ids or bool(tags & wanted_tags)


def _matches_quota(item: dict, quota: dict) -> bool:
    objectives = {str(value) for value in item.get("objective_codes") or []}
    tags = {str(value) for value in item.get("tags") or []}
    wanted_objectives = {str(value) for value in quota.get("objective_codes") or []}
    wanted_tags = {str(value) for value in quota.get("tags_any") or []}
    return (not wanted_objectives or bool(objectives & wanted_objectives)) and (
        not wanted_tags or bool(tags & wanted_tags)
    )


def select_constrained(
    items: list[dict],
    quotas: list[dict],
    category_requirements: list[dict],
    *,
    excluded_ids: set[str] | None = None,
    rng=None,
) -> list[dict]:
    """Select one exact solution without retry-based randomness.

    Dynamic programming explores each question once and memoizes the remaining
    objective quota/category state. Randomness changes candidate order, not
    correctness: a satisfiable blueprint always yields a valid set.
    """
    if not quotas:
        raise ConstraintSelectionError("A constrained quiz needs at least one objective quota.")
    rng = rng or random.SystemRandom()
    excluded_ids = {str(value) for value in excluded_ids or set()}
    candidates = [
        item
        for item in items
        if str(item.get("id") or "") not in excluded_ids
        and not excluded_ids.intersection(str(tag) for tag in item.get("tags") or [])
    ]
    rng.shuffle(candidates)
    remaining_start = tuple(int(quota.get("count") or 0) for quota in quotas)
    minimums = tuple(int(row.get("minimum") or 0) for row in category_requirements)
    if any(value < 0 for value in (*remaining_start, *minimums)):
        raise ConstraintSelectionError("Quiz quota and category minimums cannot be negative.")
    total = sum(remaining_start)
    if total > len(candidates):
        raise ConstraintSelectionError(
            f"Blueprint needs {total} unique questions but only {len(candidates)} are eligible."
        )

    quota_matches = [
        tuple(index for index, quota in enumerate(quotas) if _matches_quota(item, quota))
        for item in candidates
    ]
    category_matches = [
        tuple(_matches_category(item, requirement) for requirement in category_requirements)
        for item in candidates
    ]

    @lru_cache(maxsize=None)
    def solve(index: int, remaining: tuple[int, ...], covered: tuple[int, ...]):
        slots_needed = sum(remaining)
        if slots_needed == 0:
            return () if all(value >= minimum for value, minimum in zip(covered, minimums)) else None
        if index >= len(candidates) or len(candidates) - index < slots_needed:
            return None
        # If a quota has fewer remaining matching candidates than required,
        # this state is impossible regardless of category overlap.
        for quota_index, required in enumerate(remaining):
            if required and sum(quota_index in matches for matches in quota_matches[index:]) < required:
                return None
        for category_index, minimum in enumerate(minimums):
            missing = max(0, minimum - covered[category_index])
            if missing and sum(matches[category_index] for matches in category_matches[index:]) < missing:
                return None

        assignments = [
            quota_index for quota_index in quota_matches[index] if remaining[quota_index] > 0
        ]
        rng.shuffle(assignments)
        for quota_index in assignments:
            next_remaining = list(remaining)
            next_remaining[quota_index] -= 1
            next_covered = tuple(
                min(minimums[cat], covered[cat] + int(category_matches[index][cat]))
                for cat in range(len(minimums))
            )
            tail = solve(index + 1, tuple(next_remaining), next_covered)
            if tail is not None:
                return ((index, quota_index), *tail)
        return solve(index + 1, remaining, covered)

    solution = solve(0, remaining_start, tuple(0 for _ in minimums))
    if solution is None:
        raise ConstraintSelectionError(
            "Blueprint cannot satisfy all objective quotas and category minimums with unique questions."
        )
    return [dict(candidates[index], quota_index=quota_index) for index, quota_index in solution]
