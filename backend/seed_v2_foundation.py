"""Opt-in runner for the Nexus V2 additive foundation (Phase 1A).

This is NOT part of ``seed.py`` / ``seed_curriculum.py`` and is NOT run by CI
or any deploy step. Run it by hand to populate the V2 certification hierarchy
from the YAML data files:

    ./.venv/bin/python seed_v2_foundation.py

It is idempotent — re-running makes no duplicate rows. It never modifies
``training_weeks``, progression, the 40% A+ unlock setting, or student data.
"""

import sys

sys.path.insert(0, ".")

from app.database import SessionLocal  # noqa: E402
from app.services.v2_content_loader import (  # noqa: E402
    backfill_examcompass_permission,
    load_all,
    load_content,
)


def _print_summary(label: str, summary: dict) -> None:
    print(f"{label}:")
    for entity, counts in sorted(summary["by_entity"].items()):
        print(f"  {entity}: {counts}")
    print(
        f"  totals: created={summary['created']} "
        f"updated={summary['updated']} unchanged={summary['unchanged']}"
    )


def main() -> None:
    db = SessionLocal()
    try:
        _print_summary("V2 certification hierarchy loaded", load_all(db, commit=True))

        # Markdown lessons, data-driven resources, and Explain prompts. Safe to
        # re-run — every loader is keyed on a stable natural key.
        _print_summary("V2 content loaded", load_content(db, commit=True))

        # A module assessment may point at a lesson_key that only exists once
        # lessons have been loaded; re-run the hierarchy loader so those refs
        # resolve in a single seed pass. Idempotent — reports mostly unchanged.
        _print_summary("V2 assessment refs resolved", load_all(db, commit=True))

        examcompass = backfill_examcompass_permission(db, commit=True)
        print(
            f"ExamCompass provenance backfill: matched={examcompass['matched']} "
            f"updated={examcompass['updated']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
