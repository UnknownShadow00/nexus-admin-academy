# Phase 11 — Database, Migrations & Seeds

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`
**Method:** Read-only inspection of the seeded local DB (mirrors production seeds) + migration/seed
source. No writes to any DB.

## Schema health — excellent
- **55 tables, 55 FKs, 121 indexes.** `PRAGMA integrity_check` = **ok**; `foreign_key_check` = **0
  violations**; `alembic_version` = `0035_service_desk_browser_mvp` (= head).
- **Every one of the 55 FKs has an explicit `ON DELETE` action (0 without)** — cascades/SET NULL
  are deliberate, no dangling-reference risk. FK enforcement is on at runtime (`PRAGMA
  foreign_keys=ON`).
- **39 unique constraints** across models provide duplicate-content protection (e.g.,
  `uq_lessons_module_order`; module `code` unique; the old `uq_student_quiz` was intentionally
  dropped in TB-06 so every quiz attempt is its own row).

## Migrations
- **47 files, single linear head, all define `downgrade`.** **5 have stub (`pass`) downgrades** —
  `0018_stub`, `0019_stub`, `0020_add_quiz_status`, `0021_add_ticket_workflow_guidance`,
  `0022_add_curriculum_exam_code` — so those steps are **not cleanly reversible**. All are additive
  (columns/data), so forward migration is safe; only rollback is limited. Low risk; note for the
  release runbook (don't rely on `downgrade` past 0022).
- History is immutable and portable (SQLite ↔ Postgres via `JSON().with_variant(JSONB)`).

## Seeds
- `seed.py` + `seed_curriculum.py` are **idempotent** by design (get-or-create / `existing` checks;
  36 filter-guards in `seed.py`), and the release process verifies a fresh schema **plus a second
  seed pass** for zero duplicate creation. Idempotency/integrity tests exist
  (`test_orientation_seed`, `test_student_data_integrity`, `test_training_reference_seed`,
  `test_quiz_organization`). Stable matching keys (module codes, lesson order, `stable_id`) preserve
  student history.
- **Known observation #2 (MOD-001 prerequisite repair on full seed):** benign **self-heal** —
  running the ordinary seed reconciles a missing MOD-001 prerequisite (MOD-000 is created later in
  the same pass; a comment documents this). **Not a defect**; leave as-is. Impact: none to students.

## Immutable scenario versions / append-only events
- Service Desk scenario versions are **immutable**: `publish_definition` computes a
  `definition_hash` and refuses to overwrite a published version with a different checksum
  ("publish a new version number"). Attempts are immutable-versioned; events are append-only. This
  correctly preserves every historical attempt's scenario facts (as the plan requires).

## SQLite concurrency — the one real DB finding
`app/database.py` sets `foreign_keys=ON`, `check_same_thread=False`, `pool_pre_ping`,
`pool_recycle=300`, **but does NOT set `journal_mode=WAL` or a `busy_timeout`.** In default
(DELETE) journal mode, a writer blocks readers and concurrent writes can raise
`database is locked`. At the current scale (five students, largely sequential work) this is
**low impact**, but it's a cheap, high-value hardening:
- Set **`PRAGMA journal_mode=WAL`** (readers don't block the writer) and
  **`PRAGMA busy_timeout=5000`** (retry briefly instead of erroring) on connect.
- *Regression test:* two concurrent writes to different tables both succeed.

## When SQLite becomes a limitation (PostgreSQL trigger — not now)
SQLite is the right choice today. Migrate to the `docker-compose` PostgreSQL path when **any** of:
1. After enabling WAL+busy_timeout you still see `database is locked` under normal use.
2. You need **more than one backend worker/process** (uvicorn `--workers > 1`) or horizontal scaling.
3. Sustained **concurrent active users exceed ~20–50** (e.g., a live cohort all submitting at once).
4. You need **online/point-in-time backups** without file-copy locking, or replication/HA.
Until one of those is true, **do not migrate** — the portability is already in place, so the switch
is low-effort when actually needed.

## Backup/restore (map; detail in Phase 15)
`scripts/` holds backup tooling; `docs/DEPLOYMENT.md` documents backup/restore. Backup file
permissions and `.env` handling → Phase 15.

## Priorities
- **P2 (easy win):** enable WAL + `busy_timeout` on SQLite connect.
- P3: note the 5 stub downgrades in the release runbook.
- No P0/P1 database issues. Schema, seeds, and immutability guarantees are sound.
