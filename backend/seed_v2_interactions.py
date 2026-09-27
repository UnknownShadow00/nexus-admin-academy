"""Opt-in V2 pilot interaction loader; run only against a migrated development DB.

Usage from backend/: python seed_v2_interactions.py [--dry-run]
Requires the V2 certification/lesson foundation to have been loaded already.
"""

import argparse

from app.database import SessionLocal
from app.services.v2_interaction_loader import load_interactions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            summary = load_interactions(db)
            if args.dry_run:
                db.rollback()
            else:
                db.commit()
        except Exception:
            db.rollback()
            raise
    print({**summary, "dry_run": args.dry_run})


if __name__ == "__main__":
    main()
