# Nexus IT Academy — Repository Context

This file is a concise implementation guide for coding assistants. Use
`AGENTS.md` for repository workflow rules and `TASKS.md` for active work.

## Current system

- React 18 + Vite + Tailwind frontend in `frontend/`.
- FastAPI + SQLAlchemy + Alembic backend in `backend/`.
- SQLite is the active self-hosted production database; PostgreSQL is supported
  by `docker-compose.yml`.
- The active deployment uses a systemd backend, an nginx frontend container,
  Cloudflare HTTPS, persistent uploads, and local Ollama-compatible AI.
- Production and restore procedures are in `docs/DEPLOYMENT.md`.

## Production change rule

`backend/nexus.db` in this checkout is not a sandbox copy — it is the live
database for `nexus-admin-academy.service` (confirm with
`systemctl cat nexus-admin-academy.service`). The same applies to any other
file, service, or environment variable this checkout's systemd units read
directly, and to any remote host reachable from here that is designated
production.

**Unless explicitly authorized in the current conversation/turn, do NOT:**

- modify the production database
- run `seed.py` (or any seed module) against production
- run Alembic migrations against production
- deploy code
- restart production services
- modify production environment variables
- delete or modify production files
- create, delete, or reset production VMs
- perform any other destructive infrastructure action
- run a command whose target is ambiguous between dev/test and production —
  resolve the ambiguity (or ask) before running it, never guess

Read-only inspection (status checks, `SELECT`-only queries, log reads,
`systemctl status`) is always allowed.

**Before any explicitly-authorized production mutation**, work through this
in order and say so as you go:

1. Identify the exact production target (file path, host, service).
2. Take or verify the required backup.
3. State the intended mutation before running it.
4. Perform the minimum change needed — nothing bundled in.
5. Verify health/state afterward.
6. Report exactly what changed.

**Approval does not carry forward.** Authorization for one production
mutation, in one turn, is not standing permission for the next one — even a
related follow-up in the same session requires asking again.

## Repository map

```text
backend/app/
  main.py              application factory, middleware, router mounting
  config.py            environment loading and environment helpers
  database.py          SQLAlchemy engine/session configuration
  models/              persisted domain models
  routers/             HTTP endpoints and authorization boundaries
  schemas/             shared Pydantic request/response models
  services/            domain logic and external integrations
backend/alembic/        immutable migration history
backend/tests/          backend unit/integration/security tests
backend/seed*.py        idempotent curriculum and platform seeds
frontend/src/
  App.jsx               route table and role-specific navigation
  components/           shared UI and auth guards
  features/cli-labs/    networking simulator and lesson data
  pages/                student and admin route pages
  services/api.js       centralized HTTP client wrappers
references/lesson-drafts/ curriculum source material
scripts/                production backup tooling
tasks/loop-log.md       mandatory completion log
```

## Domain boundaries

- Learning content: modules, lessons, notes, quizzes, questions, curriculum
  videos, and video-watch state.
- Practice: support tickets/submissions/evidence, guided labs/runs/VM
  assignments, networking CLI labs, and capstones.
- Progression: roles, promotion gates, mastery, XP ledger, login streaks,
  onboarding, activity, and weekly leads.
- Operations: admin sessions, AI usage/rate limits, resources, command
  reference, integrations, and application settings.

Do not create a second model or service for an existing domain. Trace the
model, router, service, API wrapper, page, seed, migration, and tests before
changing a feature.

## Authentication and authorization

- Student authentication uses signed JWTs plus the student session cookie.
- Admin authentication uses a separate random, expiring server-side session.
- Admin routers require `verify_admin`; student routes resolve the current
  student and enforce ownership for student-specific records.
- Frontend guards are user experience controls, not security boundaries. Keep
  authorization on the backend.
- Never return ticket answer keys, scoring anchors, quiz answers, or another
  student's evidence through student endpoints.
- Never hardcode credentials. Seeded account passwords come from
  `SEED_PASSWORD_*` environment variables.

## Database and seed rules

- Never delete or rewrite historical Alembic migrations.
- Every schema change gets a new reversible migration. Review generated SQL
  and consider existing production data before applying it.
- Keep SQL portable across SQLite and PostgreSQL.
- `backend/seed.py` and `backend/seed_curriculum.py` are idempotent. Preserve
  stable matching keys and student history when changing content.
- Do not edit the production database directly for ordinary content changes.
- Do not touch uploads, local database files, backups, or `.env` files during
  repository maintenance.

## Frontend structure

Student primary navigation is intentionally limited to Today, Service Desk,
and Progress, plus a small secondary "Extra Practice" group for optional work.
Today (route `/`) surfaces the single next required activity across videos,
quizzes, and Service Desk scenarios, sourced from `training_service.py`'s
`next_activity`. My Training, Support Tickets, Guided Labs, Networking Labs,
Capstones, Command Library, and Terminal Practice live under Extra Practice —
optional and never competing with what Today points at.

Admin primary navigation is intentionally workflow-based: Dashboard, Learning
Content, Students, Assessments & Labs, and System. Small admin utilities belong
inside those groups instead of becoming new top-level tabs.

Preserve both desktop and mobile navigation behavior, keyboard access, route
guards, capstone role visibility, ticket-feedback indicators, and logout.

## API and service conventions

- Put frontend HTTP calls in `frontend/src/services/api.js`.
- Validate request bodies and files at the router boundary.
- Keep external integrations behind services with explicit timeouts and clear
  disabled/unavailable behavior.
- AI input is untrusted. Preserve prompt-injection delimiters, budgets, rate
  limits, manual fallback, and calibration checks.
- Evidence uploads require bounded reads, allowed types, safe filenames,
  persistent storage, and ownership checks.

## Verification

Run the checks that match the change:

```bash
cd backend
./.venv/bin/python -m compileall -q app tests
./.venv/bin/python -m pytest -q
./.venv/bin/python -m alembic current

cd ../frontend
npm ci
npm run build
npm run cli:validate
npm run cli:sanity
npm audit --audit-level=high
```

The frontend currently has no lint or typecheck script. Install
`backend/requirements-dev.txt` before running Ruff in a fresh environment.

`.github/workflows/ci.yml` runs the same checks (plus a fresh-database
migration/seed proof and real-browser Playwright coverage) on every PR and
push to main. Reproduce any CI job locally with the commands and
`scripts/e2e/` fixture harness documented in `docs/DEPLOYMENT.md` under
"Continuous integration" — don't duplicate that section here.

## Continuing documentation

- `README.md`: local setup and entry points.
- `docs/DEPLOYMENT.md`: deploy, backup, restore, health checks, and CI.
- `docs/AUTHORING_CONFIG_SECURITY.md`: content authoring, environment variables,
  and current security controls.
- `docs/PROGRESSION_CONTRACT.md`: what current progression means — authoritative
  vs. non-authoritative systems, every seeded gate's semantics, and Gate 4's
  deferred Windows Server/AD coverage.
- `docs/MENTOR_GUIDE.md` and `docs/STUDENT_GUIDE.md`: operating guides.
- `TASKS.md`: current roadmap only.
