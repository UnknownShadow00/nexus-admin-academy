"""Audit and repair student-owned rows whose student no longer exists.

Dry-run is the default. Pass ``--confirm`` to apply the reported actions in a
single transaction. The script prints table-level counts only; it never emits
student names, emails, usernames, or row contents.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import DATABASE_URL  # noqa: E402


SET_NULL_TABLES = {"evidence_artifacts"}


@dataclass(frozen=True)
class OrphanSummary:
    table: str
    count: int
    action: str


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _student_reference_tables(connection: sqlite3.Connection) -> list[str]:
    tables: list[str] = []
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    for (table,) in rows:
        columns = {
            row[1] for row in connection.execute(f"PRAGMA table_info({_quote(table)})")
        }
        if table != "students" and "student_id" in columns:
            tables.append(table)
    return tables


def find_orphans(connection: sqlite3.Connection) -> list[OrphanSummary]:
    summaries: list[OrphanSummary] = []
    for table in _student_reference_tables(connection):
        quoted = _quote(table)
        count = connection.execute(
            f"SELECT COUNT(*) FROM {quoted} AS child "
            "WHERE child.student_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM students WHERE students.id=child.student_id)"
        ).fetchone()[0]
        if count:
            summaries.append(
                OrphanSummary(
                    table=table,
                    count=count,
                    action="set_null" if table in SET_NULL_TABLES else "delete",
                )
            )
    return summaries


def repair_orphans(
    connection: sqlite3.Connection, *, confirm: bool = False
) -> list[OrphanSummary]:
    summaries = find_orphans(connection)
    if not confirm or not summaries:
        return summaries

    if connection.in_transaction:
        connection.rollback()
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("BEGIN IMMEDIATE")
        for summary in summaries:
            quoted = _quote(summary.table)
            predicate = (
                "student_id IS NOT NULL AND NOT EXISTS "
                "(SELECT 1 FROM students WHERE students.id="
                f"{quoted}.student_id)"
            )
            if summary.action == "set_null":
                cursor = connection.execute(
                    f"UPDATE {quoted} SET student_id=NULL WHERE {predicate}"
                )
            else:
                cursor = connection.execute(f"DELETE FROM {quoted} WHERE {predicate}")
            if cursor.rowcount != summary.count:
                raise RuntimeError(
                    f"{summary.table}: expected {summary.count} rows, changed {cursor.rowcount}"
                )

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                f"foreign-key verification still reports {len(violations)} violation(s)"
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"database integrity check failed: {integrity}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return summaries


def _database_path() -> Path:
    url = make_url(DATABASE_URL)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RuntimeError("This repair script requires the deployed SQLite database")
    return Path(url.database).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="apply the reported repair in one transaction (default: dry-run)",
    )
    args = parser.parse_args()

    connection = sqlite3.connect(_database_path(), timeout=30)
    try:
        summaries = repair_orphans(connection, confirm=args.confirm)
        mode = "APPLIED" if args.confirm else "DRY-RUN"
        print(f"Mode: {mode}")
        if not summaries:
            print("No orphaned student rows found.")
        for item in summaries:
            print(f"{item.table}: {item.count} row(s), action={item.action}")
        print(f"Total affected rows: {sum(item.count for item in summaries)}")
        print(f"Integrity check: {connection.execute('PRAGMA integrity_check').fetchone()[0]}")
        print(
            "Foreign-key violations: "
            f"{len(connection.execute('PRAGMA foreign_key_check').fetchall())}"
        )
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
