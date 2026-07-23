# Phase 15 — Testing & Release Process

**Date:** 2026-07-23 · **Reviewer:** Claude Code · Baseline `15a9410`

## Test inventory
- **Backend: 40 files, ~228 test functions, 238 collected — all pass (~45s).**
- **Frontend e2e (Playwright): 6 tests** covering real journeys: My Training desktop+mobile,
  admin Weekly Training, capstone role-gating, **"a disposable beginner completes Week 0 with a
  shared quiz and persistent progress"**, Service Desk beta render (desktop+mobile), admin
  controls + replay. Plus `cli:validate` / `cli:sanity` for the CLI engine.

## Well covered
- **Security regressions:** 28 tests (`test_security_hardening`, `test_security_part9`) — cookies,
  CSRF, ownership, upload stamping, admin session tokens.
- **Progression/gating:** gates 1–5 + graduation + `week_prerequisite_gating` + `week_plan` (~40 tests).
- **Service Desk:** 20 tests (`test_service_desk_foundation`) + e2e render.
- **Core content:** training service, quizzes, labs, tickets (hints/params), onboarding, orientation
  seed, cli labs, username case, TB01–TB06 regressions, student-data integrity.
- **Seed idempotency / fresh install:** README documents a fresh-schema pass **plus a second seed
  pass** for zero duplicates; integrity tests back this. Fresh install is verified to match seeds.

## Coverage gaps
1. **No dedicated tests for several live endpoints:** `search` (which has the **known
   gating-bypass bug** from Phase 6/10 — untested), `flashcards`/FSRS (drives Daily Review),
   `evidence_validator` edge cases beyond one upload test, `resources`, `commands`. These are the
   highest-value additions.
2. **Migrations are not tested both directions.** No upgrade→downgrade round-trip test; the **5
   stub downgrades** (Phase 11) are unverified. At minimum, assert `upgrade head` on a fresh DB in CI.
3. **e2e depends on a running server**, and `service-desk.local.spec.js` is a `.local` spec — it
   won't run in a standard headless CI without setup.

## The big process gap: no CI
**`.github/workflows/` is absent.** The 238 backend tests, 6 e2e tests, `npm audit`,
`cli:validate/sanity`, and `alembic upgrade head` all rely on **manual** execution. For an
owner-operated program this is the single most impactful reliability improvement: a regression can
merge unnoticed. Recommend a minimal GitHub Actions (or equivalent) pipeline running on push/PR:
`pytest -q`, `alembic upgrade head` on a fresh DB, `npm ci && npm run build && npm run cli:validate
&& npm run cli:sanity && npm audit --audit-level=high`, and (nightly) the Playwright e2e against a
throwaway instance. Add `ruff check` + `pip-audit` (Phase 10/12).

## Release workflow (as practiced, from DEPLOYMENT.md + deploy history)
Branch → conventional commit → **backup** (timestamped SQLite copy + integrity check) → `alembic
upgrade head` → **seed** (idempotent) → frontend `npm run build` → backend restart (systemd) →
**`/health` check** → **post-deployment smoke checklist** → release tag. `docs/DEPLOYMENT.md`
covers required config, self-hosted + Docker paths, SQLite/PostgreSQL backup+restore, the smoke
checklist, and Service Desk beta. This is a solid, documented process.

Caveats:
- **Docs describe self-hosted systemd/nginx/SQLite; production actually runs on Render behind
  Cloudflare** (Phases 0/13) — the release doc and reality diverge. Reconcile in Phase 16.
- Cleanup of smoke-test artifacts was reliable in the last deploy (test student created + deleted
  with zero-orphan verification) — good, and mirrors this review's Phase 16 obligation.

## Recommended simpler, repeatable release checklist
1. `git switch -c release/<date>` off a green `main`.
2. CI green (tests + build + audit + `alembic upgrade head`).
3. **Backup** DB (timestamp) + verify integrity.
4. Merge; `alembic upgrade head`; run idempotent seeds.
5. Build frontend; deploy; restart backend.
6. `GET /health` == 200; run the smoke checklist (login, Week 0 flow, one quiz, gating, admin).
7. Tag release; record commit + backup name.
8. Rollback plan: restore backup + redeploy previous tag (document the 5 non-reversible migrations
   so rollback uses backup-restore, not `downgrade`, past 0022).

## Priorities
- **P1 (process):** add CI (tests/build/audit/migrate) on push/PR.
- P2: tests for search (+gating), flashcards, evidence validator; migration upgrade smoke test.
- P2: reconcile release docs with actual hosting.
