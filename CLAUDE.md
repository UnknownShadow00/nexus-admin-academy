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

Student primary navigation is intentionally limited to Home, Learn, Practice,
and Progress. Quizzes live under Learn; tickets, labs, networking labs,
capstones, commands, and terminal practice live under Practice.

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
./.venv/bin/alembic current

cd ../frontend
npm ci
npm run build
npm run cli:validate
npm run cli:sanity
npm audit --audit-level=high
```

The frontend currently has no lint or typecheck script. Install
`backend/requirements-dev.txt` before running Ruff in a fresh environment.

## Continuing documentation

- `README.md`: local setup and entry points.
- `docs/DEPLOYMENT.md`: deploy, backup, restore, and health checks.
- `docs/AUTHORING_CONFIG_SECURITY.md`: content authoring, environment variables,
  and current security controls.
- `docs/MENTOR_GUIDE.md` and `docs/STUDENT_GUIDE.md`: operating guides.
- `TASKS.md`: current roadmap only.
