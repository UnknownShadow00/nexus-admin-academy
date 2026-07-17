"""One-off cleanup for phantom students created by the removed seed_students() (TB-01).

Deletes students that match ALL of:
  - name in the known phantom set (Alex, Jordan, Sam, Taylor, Riley)
  - email ending in @nexus.local
  - no password hash (they were created credential-less)

Also removes their dependent rows (XP ledger, login streaks, squad activity)
so leaderboard/cohort stats are clean. Prints counts; requires --yes to act.

Usage:
    python scripts/purge_ghost_students.py          # dry run, prints what would be deleted
    python scripts/purge_ghost_students.py --yes    # actually delete
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.models.xp_ledger import XPLedger  # noqa: E402
from app.models.login_streak import LoginStreak  # noqa: E402
from app.models.squad_activity import SquadActivity  # noqa: E402

PHANTOM_NAMES = {"Alex", "Jordan", "Sam", "Taylor", "Riley"}


def find_ghosts(db):
    candidates = (
        db.query(Student)
        .filter(Student.name.in_(PHANTOM_NAMES))
        .filter(Student.email.like("%@nexus.local"))
        .all()
    )
    # Only credential-less rows qualify — never touch a real account.
    return [s for s in candidates if not getattr(s, "password_hash", None)]


def main() -> int:
    apply_changes = "--yes" in sys.argv
    db = SessionLocal()
    try:
        ghosts = find_ghosts(db)
        if not ghosts:
            print("No phantom students found. Nothing to do.")
            return 0

        print(f"Found {len(ghosts)} phantom student(s):")
        for s in ghosts:
            print(f"  id={s.id} name={s.name} email={s.email}")

        if not apply_changes:
            print("\nDry run. Re-run with --yes to delete these rows and their XP/streak/squad data.")
            return 0

        ids = [s.id for s in ghosts]
        xp = db.query(XPLedger).filter(XPLedger.student_id.in_(ids)).delete(synchronize_session=False)
        streaks = db.query(LoginStreak).filter(LoginStreak.student_id.in_(ids)).delete(synchronize_session=False)
        squad = db.query(SquadActivity).filter(SquadActivity.student_id.in_(ids)).delete(synchronize_session=False)
        for s in ghosts:
            db.delete(s)
        db.commit()
        print(f"Deleted {len(ghosts)} students, {xp} XP rows, {streaks} streak rows, {squad} squad rows.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
