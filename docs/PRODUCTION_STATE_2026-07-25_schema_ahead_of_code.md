# Production state: schema ahead of deployed code (2026-07-25)

This records a deliberate, temporary, and safe state created while working
`fix/question-bank-integrity-and-import`: two additive migrations from that
unmerged branch have already been applied to the production database, while
`nexus-admin-academy.service` is still running the old (pre-branch) code from
`main` at commit `5795adc`. This document is the audit trail for that state
until the branch is merged and deployed, at which point code catches up to
schema and this file can be archived.

## 1. Backup

Ran the sanctioned backup script (`scripts/backup_sqlite.sh`), which uses
SQLite's online-backup API against the live writer:

```
$ bash scripts/backup_sqlite.sh
Sat Jul 25 02:42:55 AM UTC 2026: backup ok — /home/nexus/backups/nexus/nexus-2026-07-25.db.gz (438357 bytes), uploads synced
```

Independently verified (not just trusting the script's own size guard) by
decompressing to a scratch path and checking it opens, passes
`PRAGMA integrity_check`, and contains the expected data:

```
integrity_check: ('ok',)
students: 8
questions: 967
quizzes: 104
quiz_attempts: 2
q648 present: True
```

Question/quiz/attempt counts match the read-only audit run earlier in this
work (`docs/QUESTION_BANK_AUDIT.md`, 967 questions). `uploads/` was synced by
the same script run. Backup location: `~/backups/nexus/nexus-2026-07-25.db.gz`
(14-day retention, per the existing script).

## 2. Exact current Alembic revision

```
$ ./.venv/bin/alembic current
6736e5d5172a (head)

$ sqlite3 (via python) SELECT version_num FROM alembic_version;
6736e5d5172a
```

Single head, no branch divergence. This is the production database's actual
applied revision, confirmed by reading `alembic_version` directly, not just
trusting the tool's cached state.

Pre-branch (deployed) code is pinned to revision `0035_service_desk_browser_mvp`
(the head as of `main`@`5795adc`, before this branch added anything).

## 3. Migration compatibility with the currently-running old backend

Two migrations were applied, in order:

| Revision | Change |
|---|---|
| `274729e5d444` | `flashcard_reviews`: add `last_wrong_answer TEXT NULL` |
| `6736e5d5172a` | `questions`: add `difficulty INTEGER NULL`, `tags JSON NULL`, `source TEXT NULL`, `fingerprint VARCHAR(64) NULL` (+ index), `imported_at DATETIME NULL`, `import_filename TEXT NULL`, `flagged_for_review BOOLEAN NOT NULL DEFAULT 0` (+ index), `flag_reason TEXT NULL` |

Both are:

- **Additive only** — `ALTER TABLE ADD COLUMN` / `CREATE INDEX`. No column was
  renamed, retyped, or dropped; no existing constraint was changed.
- **Nullable, or defaulted** — every new column is `NULL`-able except
  `flagged_for_review`, which is `NOT NULL` but carries `server_default '0'`,
  so SQLite backfills every existing row without error and every future
  `INSERT` that doesn't mention the column gets `0` automatically.
- **Reversible** — each migration's `downgrade()` drops exactly what its
  `upgrade()` added (verified by reading both files; not executed against
  production, since re-running migrations was explicitly out of scope for
  this pass).
- **Compatible with the old, still-running code**: confirmed by diffing the
  pre-branch model definitions
  (`git show 5795adc:backend/app/models/flashcard.py`,
  `git show 5795adc:backend/app/models/quiz.py`) against the new schema, and
  by confirming there is no raw SQL / `SELECT *` anywhere in the old backend
  (`git grep` for `SELECT \*` / `execute("SELECT` returned nothing). SQLAlchemy's
  ORM only ever selects, inserts, and updates the columns a model class
  declares — it never does `SELECT *`. The old code's `Question` and
  `FlashcardReview` classes don't declare any of the 9 new columns, so:
  - Old-code reads never request them.
  - Old-code writes never populate them — they receive their column default
    (`NULL`, or `0` for `flagged_for_review`) automatically.
  - Nothing in the new columns can be seen, touched, or broken by code that
    doesn't know they exist.

Net effect: the live schema is a strict superset of what the running process
expects. This is the standard "expand" half of an expand/contract migration
strategy — safe by construction, not just by luck.

## 4. Production health and database integrity

```
$ systemctl is-active nexus-admin-academy.service
active
$ systemctl show nexus-admin-academy.service --property=ActiveEnterTimestamp,MainPID
ActiveEnterTimestamp=Fri 2026-07-24 23:08:19 UTC
MainPID=860437

$ curl -s http://localhost:8000/health
{"success":true,"data":{"ok":true,"timestamp":"2026-07-25T02:43:40.538628+00:00"}}

$ PRAGMA integrity_check;   -- on the live file, read-only connection
('ok',)
$ PRAGMA foreign_key_check; -- 0 violations
```

Service has been up and stable since before the migrations were applied
(`23:08:19` vs. migrations applied `~02:0x`), has not restarted, and is
answering health checks normally. No corruption, no orphaned foreign keys.

## 5. Current state, recorded plainly

| | |
|---|---|
| Deployed/running code | `main` @ `5795adc` (pre-branch) |
| Production DB schema | `fix/question-bank-integrity-and-import` @ `6736e5d5172a` (branch head as of this record) |
| Production question/flashcard **content** | Unchanged — both migrations are schema-only, zero rows were written, updated, or deleted by them |
| Risk while in this state | None identified — see §3. The old code simply doesn't know the new columns exist |
| Exit condition | Deploy this branch's code (restart the service) once it's reviewed/merged — **not done as part of this record**, requires separate explicit approval |

No migrations were run and no production question data was modified while
producing this record, per explicit instruction.
