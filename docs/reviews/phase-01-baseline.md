# Phase 1 — Baseline

**Date:** 2026-07-23 · **Reviewer:** Claude Code

## Git baseline
- Branch: `main`. HEAD / **review baseline commit: `15a94103d5b951913875cc5a054fda7b70bede32`** (`15a9410`, "Merge branch 'fix/service-desk-admin-actions'").
- The plan's "review-baseline commit" placeholder was never filled, and no separate baseline was supplied → **baseline = current HEAD** (`15a9410`). All phases are pinned to this commit.
- Worktree: effectively clean. Only untracked items are review artifacts I created: `NEXUS_REVIEW_PLAN.md`, `docs/reviews/`. No source files modified.

## Start commands
- **Backend:** `alembic upgrade head` → `python scripts/seed_users.py` → `python seed.py` → `python seed_curriculum.py` → `uvicorn app.main:app --reload` (from `backend/`). Local venv at `backend/.venv` (python3.11).
- **Frontend:** `npm run dev` (Vite). Build `npm run build`. Env needs `VITE_API_URL`.

## Dependencies / lock files
- Backend: `backend/requirements.txt` (prod), `backend/requirements-dev.txt` (dev; ExamCompass scraping/Chromium, Ruff). No `pyproject.toml`/poetry — pip + requirements only.
- Frontend: `frontend/package.json` + `frontend/package-lock.json` (npm).
- Root `package-lock.json` is a 104-byte stub (gitignored via `/package-lock.json`).

## Env templates
- `backend/.env.example`, `frontend/.env.example` (both tracked). Real `backend/.env` exists locally and is **gitignored** (contains `ADMIN_*`, `SEED_PASSWORD_*`).

## Migrations
- **47 migration files** in `backend/alembic/versions/`. Single head, no branching: **`0035_service_desk_browser_mvp`** (`alembic heads`/`current` both agree). Config `backend/alembic.ini`.
- History is linear and immutable per repo rules.

## Seeds and responsibilities
- `seed.py` — roles, gates, all weeks of curriculum content (idempotent).
- `seed_curriculum.py` — All Course Content video/quiz catalog (idempotent).
- `scripts/seed_users.py` — student/mentor accounts from `SEED_PASSWORD_*`.
- `seed_phase_a..g.py`, `seed_quiz_organization.py` — phased content seeds.
- Maintenance scripts: `purge_ghost_students.py`, `repair_orphaned_student_data.py`, `restore_study_tracker.py`, `calibrate_grader.py`, `validate_training_curriculum.py`, `day4_smoke_test.py`.

## Production deployment docs
- `docs/DEPLOYMENT.md` (deploy/backup/restore/health), `docs/AUTHORING_CONFIG_SECURITY.md`, guides (`MENTOR_GUIDE`, `STUDENT_GUIDE`, `MY_TRAINING`, `SERVICE_DESK_*`). `README.md` for local setup.

## Test suites
- **Backend: 40 test files, 238 tests — all pass in ~45s** (`pytest -q`, this session). Covers auth/JWT, admin session, gates 1–5 + graduation, onboarding, orientation seed, quizzes, tickets, labs, CLI labs, capstones, service desk foundation, security hardening (parts 9 etc.), student data integrity, study-tracker mapping, title matching, username case.
- **Frontend e2e (Playwright):** `frontend/tests/e2e/my-training.spec.js`, `service-desk.local.spec.js` (2 specs). Scripts: `cli:validate`, `cli:sanity`, `test:e2e`.

## Major architectural directories
- Backend: `app/{main.py, config.py, database.py, models(30), routers(28), schemas, services(37), utils, data}`.
- Frontend: `src/{App.jsx, components, features(cli-labs), pages, services/api.js, hooks, utils, styles.css}`.
- Infra: `docker-compose.yml` (Postgres path), `scripts/` (backup tooling), `content-pack/` (gitignored deploy artifact).

## Dead / duplicate / generated / suspicious files
- **Stray local test DBs (gitignored, untracked):** `backend/phase2_check.db`, `phase2_check2.db`, `phase2_check3.db`, `phase2_local.db`, plus active `backend/nexus.db`. Cleanup candidates; not tracked so harmless to repo.
- Empty root `nexus.log` (gitignored). `pytest-cache-files-*/`, `.tmp/`, `.ruff_cache/`, `.pytest_cache/` — all gitignored.
- **Deferred-feature code present:** `services/guacamole_service.py`, `services/proxmox_service.py` + their tests, despite Guacamole/Proxmox/VM being explicitly deferred. Candidate dead/premature code → Phase 12.

## Secrets in tracked files
- **None found.** `git grep` for credential-assignment patterns returned only **test-fixture passwords** (e.g., `password="pass123"`, `"BrowserFlow!2026"` in e2e). No real secrets/keys committed. `.env` variants are gitignored (`!.env.example` kept).

## Inability to run / discrepancies to carry forward
- Cannot run `alembic current` against production (no DB access) — verified locally instead (head `0035`).
- **README says "24-week curriculum" / "six-role ladder"; plan says "25 weeks, 296 activities."** Likely Week 0 orientation + 24 weeks = 25. Reconcile against live/DB in Phase 5.
- **Deployment reality vs. docs:** production is behind **Cloudflare** (bot 403s) and login cites **Render** backend, while docs describe self-hosted systemd/nginx/SQLite. Reconcile in Phase 16.
- No repository state modified to ease the review (per instruction).
