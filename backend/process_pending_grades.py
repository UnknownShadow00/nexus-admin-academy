"""Phase 1C pending-grade worker — one batch pass.

Not part of ``seed.py`` and not run by CI. Intended to be invoked periodically
by the existing self-hosted deployment (a systemd timer or a cron line, e.g.
every 2 minutes):

    */2 * * * *  cd /opt/.../backend && ./.venv/bin/python process_pending_grades.py --limit 25

It is safe to run concurrently with the API and with itself: due jobs receive
a ten-minute lease and unique claim token before processing. Stale processing
jobs are reclaimed after a crash/restart, and a late worker whose token has
been superseded discards its provider response. AI grade rows remain
append-only and unique per job/attempt number. When AI grading is disabled or
unreachable, work routes to mentor review — the student submission is retained.
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
