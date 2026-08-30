"""Phase 1C pending-grade worker — one batch pass.

Not part of ``seed.py`` and not run by CI. Intended to be invoked periodically
by the existing self-hosted deployment (a systemd timer or a cron line, e.g.
every 2 minutes):

    */2 * * * *  cd /opt/.../backend && ./.venv/bin/python process_pending_grades.py --limit 25

It is safe to run concurrently with the API and with itself: due jobs are
claimed via a status transition before processing, ai_grades rows are
append-only, and Phase 1C awards no XP / completes no activity, so a double
run cannot double-count anything. When AI grading is disabled or unreachable,
jobs simply stay pending / route to mentor review — nothing is lost.
"""

import argparse
import sys

sys.path.insert(0, ".")

from app.database import SessionLocal  # noqa: E402
from app.services.grading_config import load_grading_config  # noqa: E402
from app.services.grading_queue import run_pending_batch  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Process one batch of pending AI grading jobs.")
    parser.add_argument("--limit", type=int, default=25, help="max jobs this pass (default 25)")
    args = parser.parse_args()

    cfg = load_grading_config()
    print(
        f"AI grading: enabled={cfg.enabled} configured={cfg.configured} "
        f"model={cfg.model or '(unset)'} confidence_threshold={cfg.confidence_threshold}"
    )

    db = SessionLocal()
    try:
        counts = run_pending_batch(db, limit=args.limit)
    finally:
        db.close()

    print("batch result:", counts)


if __name__ == "__main__":
    main()
