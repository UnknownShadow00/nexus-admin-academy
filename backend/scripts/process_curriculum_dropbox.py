#!/usr/bin/env python3
"""Owner CLI for the Nexus curriculum inbox."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.curriculum_intake import CurriculumIntakeProcessor  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or import packages from the curriculum dropbox.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate without changing approved/runtime content")
    mode.add_argument("--apply", action="store_true", help="validate, archive, integrate, and clean successful items")
    parser.add_argument(
        "--allow-changed",
        action="store_true",
        help="explicitly import a changed package while preserving approved history",
    )
    args = parser.parse_args()
    if args.allow_changed and not args.apply:
        parser.error("--allow-changed may only be used with --apply")
    processor = CurriculumIntakeProcessor(
        dropbox_dir=REPOSITORY_DIR / "references" / "curriculum-dropbox",
        approved_dir=REPOSITORY_DIR / "references" / "curriculum-approved",
        content_dir=BACKEND_DIR / "content",
        backend_dir=BACKEND_DIR,
    )
    results = processor.process(mode="apply" if args.apply else "check", allow_changed=args.allow_changed)
    print(json.dumps(results, indent=2))
    return 1 if any(row["status"] in {"INVALID", "CHANGED_REQUIRES_REVIEW"} for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
