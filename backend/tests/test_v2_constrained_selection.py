"""Generic exact constraint selection for V2 assessment blueprints."""

from __future__ import annotations

import random

import pytest

from app.services.v2_assessment_selector import ConstraintSelectionError, select_constrained


def _bank():
    rows = []
    specs = {
        "4.1": (17, ["ticket_documentation", "asset_document_system"]),
        "4.2": (8, ["change_planning_scenario"]),
        "4.7": (9, ["customer_communication_scenario"]),
    }
    number = 1
    for objective, (count, categories) in specs.items():
        for index in range(count):
            rows.append(
                {
                    "id": f"Q{number:03d}",
                    "objective_codes": [objective],
                    "tags": [categories[index % len(categories)]],
                }
            )
            number += 1
    # One genuine cross-objective item must still occupy only one quiz slot.
    rows[1]["objective_codes"] = ["4.1", "4.7"]
    return rows


BLUEPRINT = [
    {"objective_codes": ["4.1"], "count": 5},
    {"objective_codes": ["4.2"], "count": 4},
    {"objective_codes": ["4.7"], "count": 3},
]
CATEGORIES = [
    {"category": "ticket_documentation", "minimum": 1, "tags_any": ["ticket_documentation"]},
    {"category": "asset_document_system", "minimum": 1, "tags_any": ["asset_document_system"]},
    {"category": "change_planning_scenario", "minimum": 1, "tags_any": ["change_planning_scenario"]},
    {"category": "customer_communication_scenario", "minimum": 1, "tags_any": ["customer_communication_scenario"]},
]


def _assert_constraints(selected, categories=CATEGORIES):
    assert len(selected) == 12
    assert len({row["id"] for row in selected}) == 12
    # The solver returns the quota assignment because a multi-objective item
    # may validly fill either one, but never both.
    assert {index: sum(row["quota_index"] == index for row in selected) for index in range(3)} == {
        0: 5,
        1: 4,
        2: 3,
    }
    for requirement in categories:
        assert sum(bool(set(row["tags"]) & set(requirement["tags_any"])) for row in selected) >= requirement["minimum"]


def test_objective_quotas_only_and_category_requirement():
    quota_only = select_constrained(_bank(), BLUEPRINT, [], rng=random.Random(1))
    assert len(quota_only) == 12
    selected = select_constrained(_bank(), BLUEPRINT, CATEGORIES[:1], rng=random.Random(2))
    _assert_constraints(selected, CATEGORIES[:1])


def test_module5_style_overlapping_constraints_always_satisfy_without_duplicates():
    for seed in range(20):
        selected = select_constrained(_bank(), BLUEPRINT, CATEGORIES, rng=random.Random(seed))
        _assert_constraints(selected)


def test_impossible_constraint_fails_clearly():
    impossible = [
        {"category": "missing", "minimum": 1, "tags_any": ["does-not-exist"]}
    ]
    with pytest.raises(ConstraintSelectionError, match="cannot satisfy"):
        select_constrained(_bank(), BLUEPRINT, impossible, rng=random.Random(0))


def test_no_duplicate_question_ids_are_selected():
    items = [
        {"id": f"Q{index:03d}", "objective_codes": ["4.1"], "tags": ["common"]}
        for index in range(1, 7)
    ]
    selected = select_constrained(
        items,
        [{"objective_codes": ["4.1"], "count": 5}],
        [{"category": "common", "minimum": 1, "tags_any": ["common"]}],
        rng=random.Random(2),
    )
    assert len({row["id"] for row in selected}) == 5


def test_exclusions_apply_to_authored_ids_and_tags():
    items = _bank()
    items[2]["tags"].append("exclude-me")
    selected = select_constrained(
        items,
        BLUEPRINT,
        CATEGORIES,
        excluded_ids={"Q001", "exclude-me"},
        rng=random.Random(3),
    )
    assert all(row["id"] != "Q001" for row in selected)
    assert all("exclude-me" not in row["tags"] for row in selected)
