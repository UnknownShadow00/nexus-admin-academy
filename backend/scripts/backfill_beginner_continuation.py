"""Run from backend/: python -m scripts.backfill_beginner_continuation --dry-run"""

import argparse
import json

import app.models  # noqa: F401 - register SQLAlchemy mappings
from app.database import SessionLocal
from app.services.v2_continuation_backfill import backfill_beginner_continuation


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill beginner continuation grants")
    parser.add_argument("--dry-run", action="store_true", help="Report proposed grants without mutation")
    parser.add_argument("--apply", action="store_true", help="Write grants to the configured database")
    args = parser.parse_args()
    if args.dry_run == args.apply:
        parser.error("Specify exactly one of --dry-run or --apply")
    with SessionLocal() as db:
        result = backfill_beginner_continuation(db, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
