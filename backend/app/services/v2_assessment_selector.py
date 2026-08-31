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
    return item_id in ids or bool(tags & ids) or bool(tags & wanted_tags)


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
    selection_requirements: dict | None = None,
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
    selection_requirements = selection_requirements or {}
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
    scenario_minimum = int(
        selection_requirements.get("scenario_application_or_reasoning_minimum") or 0
    )
    multi_minimum = int(selection_requirements.get("multi_select_minimum") or 0)
    max_same_category = int(
        selection_requirements.get("max_same_narrow_category") or 0
    )
    narrow_categories = tuple(
        sorted({str(item.get("category") or "") for item in candidates if item.get("category")})
    )

    def is_scenario(item: dict) -> bool:
        style = str(item.get("question_style") or "").casefold()
        return "scenario" in style or "reasoning" in style or "troubleshooting" in style

    scenario_matches = tuple(is_scenario(item) for item in candidates)
    multi_matches = tuple(
        str(item.get("question_type") or "").casefold() in {"multi", "multi_select", "multi-select"}
        for item in candidates
    )
    candidate_category_indexes = tuple(
        narrow_categories.index(str(item.get("category")))
        if item.get("category") in narrow_categories
        else None
        for item in candidates
    )

    @lru_cache(maxsize=None)
    def solve(
        index: int,
        remaining: tuple[int, ...],
        covered: tuple[int, ...],
        scenario_count: int,
        multi_count: int,
        narrow_counts: tuple[int, ...],
    ):
        slots_needed = sum(remaining)
        if slots_needed == 0:
            requirements_met = (
                scenario_count >= scenario_minimum
                and multi_count >= multi_minimum
                and all(value >= minimum for value, minimum in zip(covered, minimums))
            )
            return () if requirements_met else None
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
        if scenario_count + sum(scenario_matches[index:]) < scenario_minimum:
            return None
        if multi_count + sum(multi_matches[index:]) < multi_minimum:
            return None

        assignments = [
            quota_index for quota_index in quota_matches[index] if remaining[quota_index] > 0
        ]
        rng.shuffle(assignments)
        for quota_index in assignments:
            category_index = candidate_category_indexes[index]
            if (
                max_same_category
                and category_index is not None
                and narrow_counts[category_index] >= max_same_category
            ):
                continue
            next_remaining = list(remaining)
            next_remaining[quota_index] -= 1
            next_covered = tuple(
                min(minimums[cat], covered[cat] + int(category_matches[index][cat]))
                for cat in range(len(minimums))
            )
            next_narrow = list(narrow_counts)
            if category_index is not None:
                next_narrow[category_index] += 1
            tail = solve(
                index + 1,
                tuple(next_remaining),
                next_covered,
                scenario_count + int(scenario_matches[index]),
                multi_count + int(multi_matches[index]),
                tuple(next_narrow),
            )
            if tail is not None:
                return ((index, quota_index), *tail)
        return solve(
            index + 1,
            remaining,
            covered,
            scenario_count,
            multi_count,
            narrow_counts,
        )

    solution = solve(
        0,
        remaining_start,
        tuple(0 for _ in minimums),
        0,
        0,
        tuple(0 for _ in narrow_categories),
    )
    if solution is None:
        raise ConstraintSelectionError(
            "Blueprint cannot satisfy all objective quotas and category minimums with unique questions."
        )
    return [dict(candidates[index], quota_index=quota_index) for index, quota_index in solution]
