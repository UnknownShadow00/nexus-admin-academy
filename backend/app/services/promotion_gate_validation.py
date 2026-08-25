"""Static validation for the seeded PROMOTION_GATES config.

Catches config mistakes (unknown types, missing/invalid fields, retired
requirement types, unresolvable references, accidental duplicates) before a
bad row ever reaches the database. Run against seed.py's PROMOTION_GATES
during seeding and covered by a test that asserts zero issues on the real
config — see docs/PROGRESSION_CONTRACT.md for the full gate semantics this
protects.
"""

from collections import Counter

# Types the active evaluator dispatch (progression_service.check_promotion_eligibility)
# still recognizes for NEW seeded gate rows. min_verified_tickets_by_difficulty and
# practical_checkpoint are deliberately excluded: their evaluators remain wired for
# backward compatibility with stray historical rows, but new/seeded gates must never
# use them again (the legacy Ticket product has no student-facing path to earn new
# submissions, so a gate requiring one is permanently unsatisfiable).
ACTIVE_REQUIREMENT_TYPES = {
    "required_quiz",
    "min_completed_lessons",
    "min_mastery_by_domain",
    "min_service_desk_passes",
    "min_cli_labs",
    "no_unresolved_flags",
    "required_lab_pass",
}

RETIRED_REQUIREMENT_TYPES = {
    "min_verified_tickets_by_difficulty",
    "practical_checkpoint",
}

# Mirrors the alias map in progression_service._check_mastery_requirement, plus the
# raw domain ids that quiz seeding actually populates (1.0-5.0). A threshold key that
# resolves to neither can never match a real StudentDomainMastery row.
MASTERY_DOMAIN_ALIASES = {
    "hardware",
    "networking",
    "software_troubleshooting",
    "security",
    "procedures",
}
VALID_MASTERY_DOMAIN_IDS = {"1.0", "2.0", "3.0", "4.0", "5.0"}


def validate_promotion_gates_config(gates: list[dict], *, service_desk_pack_keys: set[str]) -> list[str]:
    """Return a list of human-readable issues; empty means the config is safe to seed.

    `gates` is the seed.py PROMOTION_GATES list-of-dicts shape:
    {"role": str, "requirement_type": str, "config": dict}.
    """
    issues: list[str] = []

    duplicate_counts = Counter((gate["role"], gate["requirement_type"]) for gate in gates)
    for (role, requirement_type), count in duplicate_counts.items():
        if count > 1:
            issues.append(
                f"{role}: requirement_type '{requirement_type}' appears {count} times "
                "(duplicate requirements can unintentionally double-count or mask config drift)"
            )

    for gate in gates:
        role = gate["role"]
        requirement_type = gate["requirement_type"]
        config = gate.get("config") or {}

        if requirement_type in RETIRED_REQUIREMENT_TYPES:
            issues.append(
                f"{role}: uses retired requirement_type '{requirement_type}' — "
                "the legacy Ticket product has no student-facing path to satisfy this"
            )
            continue
        if requirement_type not in ACTIVE_REQUIREMENT_TYPES:
            issues.append(f"{role}: unknown requirement_type '{requirement_type}'")
            continue

        if requirement_type == "required_quiz":
            week = config.get("week")
            if not isinstance(week, int) or week < 0:
                issues.append(f"{role}: required_quiz needs a non-negative integer 'week' (got {week!r})")

        elif requirement_type == "min_completed_lessons":
            codes = config.get("module_codes")
            if not codes or not isinstance(codes, list):
                issues.append(f"{role}: min_completed_lessons needs a non-empty 'module_codes' list")

        elif requirement_type == "min_mastery_by_domain":
            thresholds = config.get("thresholds")
            if not thresholds or not isinstance(thresholds, dict):
                issues.append(f"{role}: min_mastery_by_domain needs a non-empty 'thresholds' dict")
            else:
                for domain, required in thresholds.items():
                    resolved = str(domain).lower()
                    if resolved not in MASTERY_DOMAIN_ALIASES and resolved not in VALID_MASTERY_DOMAIN_IDS:
                        issues.append(
                            f"{role}: min_mastery_by_domain references unknown domain '{domain}' "
                            "(not a known alias or a seeded domain id) — this requirement can never be satisfied"
                        )
                    if not isinstance(required, int) or not (0 < required <= 100):
                        issues.append(
                            f"{role}: min_mastery_by_domain threshold for '{domain}' must be an int in (0, 100] "
                            f"(got {required!r})"
                        )

        elif requirement_type == "min_service_desk_passes":
            pack_key = config.get("pack_key")
            min_passed = config.get("min_passed")
            if pack_key not in service_desk_pack_keys:
                issues.append(
                    f"{role}: min_service_desk_passes references unknown pack_key {pack_key!r} "
                    f"(known packs: {sorted(service_desk_pack_keys)})"
                )
            if not isinstance(min_passed, int) or min_passed <= 0:
                issues.append(
                    f"{role}: min_service_desk_passes needs a positive integer 'min_passed' (got {min_passed!r})"
                )

        elif requirement_type == "min_cli_labs":
            min_completed = config.get("min_completed")
            if not isinstance(min_completed, int) or min_completed <= 0:
                issues.append(
                    f"{role}: min_cli_labs needs a positive integer 'min_completed' (got {min_completed!r})"
                )

        elif requirement_type == "no_unresolved_flags":
            if config:
                issues.append(f"{role}: no_unresolved_flags takes no config (got {config!r})")

        elif requirement_type == "required_lab_pass":
            lab_id = config.get("lab_id")
            min_score_pct = config.get("min_score_pct")
            if not isinstance(lab_id, int) or lab_id <= 0:
                issues.append(f"{role}: required_lab_pass needs a positive integer 'lab_id' (got {lab_id!r})")
            if not isinstance(min_score_pct, int) or not (0 < min_score_pct <= 100):
                issues.append(
                    f"{role}: required_lab_pass needs a 'min_score_pct' integer in (0, 100] (got {min_score_pct!r})"
                )

    return issues
