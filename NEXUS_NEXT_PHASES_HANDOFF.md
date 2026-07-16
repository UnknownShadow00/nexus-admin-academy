# Nexus Admin Academy — Handoff: Phase 1b through Phase 5

**Context for the AI agent (Claude Code / Codex):** You are running directly on the Linux server `nexus-services` (`192.168.0.101`), in the repo at `/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy`. This is the same machine the app actually runs on — edit files and run tests/migrations directly here, no SSH hop needed. (This same repo also syncs back to the developer's Windows PC via Syncthing for their own editing/review — that's a one-way convenience mirror for them, not something you need to account for.)

A separate GPU VM (`ai-server`, `192.168.0.104`) runs Ollama with the `deepseek-r1:32b` model, reachable at `http://192.168.0.104:11434/v1` (OpenAI-compatible endpoint). This is already wired into `ai_service.py` via `AI_BASE_URL` / `AI_MODEL` env vars — do not reintroduce a hosted or paid AI API.

**Status so far:** Phase 0 (server setup), Phase 0.5 (GPU VM + Ollama), and Phase 1 (AI Task 1 — ai_service.py rewrite, usage-log removal, phantom seed removal, password env vars, .env.example) are complete and tested.

Work through the phases below **in order**. Each phase ends with a check — do not proceed to the next phase until the current one's check passes. Show diffs for every change. Run tests after each fix, not just at the end of a batch. Never claim a step succeeded without having actually run and observed its result.

---

## Phase 1b — Guacamole + async VM provisioning fixes

Fix these VM-lab P0 issues, one at a time, with diffs and tests (extend `backend/tests/test_labs.py` as needed):

1. `guacamole_service.py` builds the client URL as `base64("c/{conn_id}")`, but Guacamole actually requires base64 of `"{identifier}\0c\0{datasource}"` (NUL-separated, datasource typically `"postgresql"`). Fix `get_token_url` accordingly, with the datasource configurable via `GUACAMOLE_DATASOURCE` (default `"postgresql"`).
2. The same function currently authenticates as the Guacamole ADMIN and hands that admin token to students — a privilege escalation risk. Implement the smallest safe alternative: create a per-lab-run Guacamole user via the REST API, grant it READ on only its own connection, return THAT user's token, and delete the user during lab teardown alongside the existing connection cleanup.
3. `routers/labs.py` provisions VMs synchronously — Proxmox clone + IP polling can exceed the frontend's 30s axios timeout. Convert to: POST returns 202 with status `"provisioning"` immediately; the clone/start/IP-wait/Guacamole steps run in a FastAPI `BackgroundTask`; add a status field on the lab run (`provisioning`/`ready`/`failed` + `guac_url`) and `GET /api/labs/{id}/vm-status`; persist `guac_url` so a page refresh recovers it.
4. Update `LabPage.jsx` to poll `vm-status` every 3s and render the iframe when ready, with a friendly failed state.

No Redis/Celery — this is a 6-user cohort, background tasks are sufficient.

**Check:** `python -m pytest -q backend/tests/test_labs.py` passes on the server.

---

## Phase 2 — First local run (mostly manual — flag anything code-related that blocks it)

This phase is primarily the human's job (filling `.env`, running migrations/seeds, starting servers), but if you hit a code bug while helping verify it, fix it here rather than deferring.

Verify on the server:
```bash
cd "/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend"
source .venv/bin/activate
alembic upgrade head
python scripts/seed_users.py && python seed_curriculum.py
```

**Check:** All 6 seeded accounts log in with unique passwords (from `SEED_PASSWORD_*` env vars). No phantom students on the leaderboard. A quiz, a ticket (AI-graded via Ollama), and CLI labs all function. Submit a test ticket and confirm grading actually calls `192.168.0.104:11434` (check server logs / Ollama's own logs for the request) rather than failing silently.

---

## Phase 3 — Dockerize and deploy

Create production deployment files:

1. `backend/Dockerfile` — `python:3.12-slim`, install requirements, run uvicorn. Move `playwright` to a new `requirements-dev.txt` so it stays out of the production image.
2. `frontend/Dockerfile` — `node:22-alpine` build stage → `nginx:alpine` runtime with SPA `try_files` config, `VITE_API_URL` as a build ARG.
3. `docker-compose.yml` at repo root:
   - `backend` service: `env_file backend/.env`, healthcheck hitting the existing `/health` endpoint.
   - `frontend` service: expose on `8081:80`.
   - `postgres:16-alpine`: named volume, `pg_isready` healthcheck.
   - A named volume mounted at the uploads path so evidence/attachments survive container restarts.
4. `scripts/backup_db.sh`: nightly `pg_dump | gzip` to `/opt/backups` with 14-day retention. Include the crontab line as a comment in the script (actual cron install is a manual step).

Don't touch application code in this phase. Show all files, then a "first deploy" command list for the human to run (`docker compose build && docker compose up -d`, migrations/seeds via `docker compose exec`).

**Check (human-run):** Same functional checks as Phase 2, now via Docker Compose, reachable from a phone via Tailscale.

---

## Phase 4 — Real VM labs (manual, Proxmox/Guacamole — human does the infrastructure, you support the code side)

This phase is mostly manual infra work (scoped Proxmox token, lab template VM, Guacamole stack deployment) — not an AI task. If asked to help, focus on:
- Confirming `backend/.env` has the right `PROXMOX_*` and `GUACAMOLE_*` variable names (already verified in Phase 1's `.env.example`).
- Debugging any code-level errors that surface once real Proxmox/Guacamole calls are exercised (the Phase 1b fixes were built and tested against the API contract, but real hardware may surface edge cases — e.g. timing, auth token expiry, VMID pool exhaustion).

**Check (human-run):** Student starts a lab → status goes provisioning → ready → desktop appears in iframe → submit → VM destroyed and Guacamole user/connection removed.

---

## Phase 5 — Security hardening before full cohort invite

Apply this security batch, one item at a time with diffs and tests:

1. `admin_auth.py`: `allow_admin_or_student` currently accepts any `"Authorization: Bearer <anything>"` without decoding. Actually validate the JWT, or require `get_current_student`.
2. Replace the deterministic sha256 admin session token with a random server-side token (or signed token with expiry), constant-time comparison via `secrets.compare_digest`, and remove any secret-length logging.
3. `quizzes.py` `submit_quiz`: multi-select questions currently grade a single correct letter as full credit. Compare as exact sets when `is_multi_select`. *(Note: check if this was already fixed during Phase 1 — the project's known fixes list mentions multi-select grading as resolved. Verify before redoing it; if already fixed, skip and note that in your output.)*
4. Evidence uploads: add a size cap matching tickets' 5MB limit, and an ownership check so a student can only attach evidence to their own ticket/lab run.
5. Insert a new `QuizAttempt` row per attempt instead of overwriting (per-attempt history). *(Also check against known-fixes — may already be done via the per-attempt history migration mentioned in project notes.)*
6. Remove the localStorage-driven mentor admin shell in `AdminAccessGate.jsx` — the backend already blocks the APIs, so this is a defense-in-depth cleanup, not a functional fix.

**Check:** Full P1 security batch merged, tests passing, before inviting the remaining students beyond a 2-day beta tester.

---

## Reminders that apply to every phase

- Smallest diffs. Show each diff before moving on.
- Test after each individual fix, not in a batch at the end.
- Actually run tests after every edit and observe the real output — never assume a fix works just because the diff looks correct.
- Never invent env var names — grep the codebase to confirm.
- No paid APIs and no new external dependencies beyond what's already justified (Ollama, Postgres, Guacamole, Proxmox).
- Seeds must remain idempotent (existing project convention).
- Update `CLAUDE.md` / `TASKS.md` / `loop-log.md` with what changed at the end of each phase, and leave an exact continuation marker for the next session.
