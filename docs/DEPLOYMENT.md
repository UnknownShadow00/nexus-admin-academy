# Nexus Deployment, Backup, and Recovery

Nexus supports two deployment shapes. The active production deployment is the
self-hosted systemd + SQLite arrangement. `docker-compose.yml` is the supported
PostgreSQL alternative. Do not mix their backup procedures.

## Required configuration

Copy values from `backend/.env.example` into a gitignored `backend/.env` and
set production secrets outside Git. The complete variable reference is in
`AUTHORING_CONFIG_SECURITY.md`.

At minimum, production needs a database URL, JWT signing key, admin
credentials, allowed frontend origin, persistent upload directory, and cookie
settings appropriate to HTTPS. AI and automated-VM integrations may remain
disabled until configured and tested.

## Active self-hosted deployment

### Hard invariant: never checkout a dev/review branch in the production WorkingDirectory

The production checkout's working directory (see `WorkingDirectory=` in
`systemctl cat nexus-admin-academy.service`) is not a sandbox — its
`backend/nexus.db`, `.env`, and any file the systemd unit reads directly are
live production state. Development, review, and testing branches must never
be checked out there. Use an isolated `git worktree` (or an equivalent
disposable clone) for any feature work, independent review, or exploratory
testing, and confirm production remains on its intended commit/branch
afterward. This applies to every agent and contributor, not just this phase.

### Deploying a change (the only supported procedure)

The serving checkout is **deploy-only**. It carries no branch work, no
uncommitted edits, and no automated commits:

- The nightly workspace snapshot (`/opt/apps/nightly-snapshot.sh`) treats this
  checkout as *protected* — it never runs `git add`/`commit`/`push` here. It
  only records `HEAD`, and if it ever finds the tree dirty it archives the
  drift to `~/backups/nexus/drift/` and logs a warning. Investigate any such
  warning: something wrote to the serving checkout outside this procedure.
- All feature, review, and hotfix work happens in a `git worktree`
  (`git worktree add ~/worktrees/<name> -b <branch> origin/main`), never here.

A deploy is a single command:

```bash
# from the serving checkout only (it refuses to run anywhere else)
scripts/deploy.sh [options] [<ref>]      # <ref> default: origin/main
```

`scripts/deploy.sh`, in order:

1. refuses to run unless it is the checkout `nexus-admin-academy.service`
   actually serves, and refuses a dirty working tree;
2. `git fetch`, then `git checkout --detach` the pinned target commit
   (a branch/tag ref is resolved to a concrete SHA first);
3. **snapshots `backend/.venv`** (hardlink copy), then
   `pip install -r backend/requirements.txt` — *before* anything that imports
   the target's code, since `backend/alembic/env.py` and several migrations
   import application modules (skip with `--skip-deps`);
4. runs `scripts/predeploy_check.sh` (read-only gate — env, migrations
   ancestry, disk, container/nginx/JWT, health). Its **full output is tee'd to
   the deploy log**. A failing gate aborts unless you pass `--force-predeploy`
   after reviewing every `FAIL` line (which are now in the log);
5. **refuses if the live database schema is ahead of the target commit**
   (would run older code against a newer schema) unless `--allow-db-ahead` is
   given. This check runs **even with `--skip-migrations`**;
6. if a migration will actually run: **stops the service**, takes a fresh
   SQLite + uploads backup (`scripts/backup_sqlite.sh`, stamp
   `predeploy-<sha>-<ts>`), then `alembic upgrade head` — all with the service
   down, so no write lands after the backup and no old code sees a
   half-applied schema. `--skip-migrations` skips this step for a reviewed
   code-only change;
7. `sudo systemctl restart` (or `start`, if step 6 stopped it), then polls
   `http://127.0.0.1:8000/health`;
8. with `--frontend`, snapshots the current container assets/config, rebuilds
   the Vite bundle, swaps it in, `nginx -t`, reloads, re-checks
   `http://127.0.0.1/health`;
9. appends timestamped lines to `~/deploy-logs/nexus-deploy.log` for every run
   (plan, each stage, and any rollback).

Use `--dry-run` to preview the resolved SHAs without touching anything.
**A migration deploy takes the backend down** from step 6 until it is healthy
again — treat schema releases as a maintenance window. Code-only deploys are
just the step-7 restart blip.

**Rollback — automatic on any failure after the checkout (step 2).**
`deploy.sh` installs an exit trap the moment the checkout moves. If **any**
later stage fails (`pip`, `predeploy`, `alembic`, `systemctl`, health, or the
frontend steps), it:

- checks the working tree back out to the previous SHA;
- if deps were installed, **restores the pre-deploy `backend/.venv` snapshot**
  (a dependency up/downgrade otherwise outlives the failed release);
- if a migration was attempted this run, **restores the pre-migration database
  backup** — SQLite DDL here is non-transactional, so a partially-applied
  migration is possible and the backup is the only safe restore;
- if the service had been stopped or restarted, (re)starts it on the old SHA
  and re-health-checks (logging `MANUAL INTERVENTION NEEDED` if it still can't
  come up);
- if frontend assets had been swapped, restores the snapshot and reloads nginx.

The venv snapshot is a same-filesystem hardlink copy, so it is near-instant and
cheap; both it and the frontend snapshot are deleted on a successful deploy.

**Rolling back a *past* deploy that changed the schema is not just
`deploy.sh <old-sha>`.** Checking out older code leaves the newer schema in
place. `deploy.sh` detects this (step 5) and refuses. To do it safely:

1. `scripts/backup_sqlite.sh` — snapshot the current (newer) DB first, in case;
2. restore a database backup taken at or before the target commit's migration
   head (from `~/backups/nexus/`, e.g. the `predeploy-<sha>-*` backup that
   deploy.sh took just before that migration) — stop the service, replace
   `backend/nexus.db`, remove stale `-wal`/`-shm`;
3. `scripts/deploy.sh --allow-db-ahead <old-sha>` — restart on the old code.

Prefer forward-fixing (a new migration + release) over a schema downgrade
whenever the newer migration is not cleanly reversible.

The failure/rollback paths are covered by `scripts/tests/deploy_failure_sim.sh`
(run in CI as the *Deploy script failure simulations* job).

The manual backend/frontend command sequences below are what `deploy.sh`
automates; run them by hand only if the script is unavailable.

The backend runs from `backend/.venv` under
`nexus-admin-academy.service` on port 8000. The `nexus-frontend` nginx
container serves the Vite build on port 80 and proxies `/api`, `/auth`,
`/uploads`, and `/health` to the host backend. Public traffic arrives through
Cloudflare HTTPS.

### Cloudflare browser analytics

Nexus does not embed Cloudflare Web Analytics and its production Content
Security Policy intentionally keeps `script-src 'self'`. If Cloudflare's edge
injects `static.cloudflareinsights.com/beacon.min.js`, do not add that host (or
a wildcard) to the application CSP merely to silence the warning. Unless RUM
has been explicitly approved, create a Cloudflare **Configuration Rule** for
`nexus.builtfromzero.fyi` and set **Disable Real User Monitoring (RUM)** to
enabled (`action_parameters.disable_rum = true`). A zone-scoped Cloudflare API
credential is required to automate that account setting; the tunnel
credential on the host is not sufficient.

Production browser validation may set
`NEXUS_E2E_ALLOW_CLOUDFLARE_BEACON_WARNING=true` while that operator action is
pending. The test exemption recognizes only the exact Cloudflare Insights
script plus the matching `csp` request failure; all other console and network
errors still fail the suite. Remove the flag after the configuration rule is
active and confirm the beacon no longer appears.

Before every deployment:

1. Confirm the intended commit and a clean worktree.
2. Run `scripts/backup_sqlite.sh` and verify both the compressed database and
   uploads copy exist.
3. Run the backend suite, frontend build, CLI checks, and dependency audit from
   `CLAUDE.md`.
4. Review new migrations and take a second timestamped database backup before
   any schema migration.

Backend update:

```bash
cd backend
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m alembic upgrade head
sudo systemctl restart nexus-admin-academy.service
curl --fail http://127.0.0.1:8000/health
sudo journalctl -u nexus-admin-academy.service -n 100 --no-pager
```

Run `python seed.py` or `python seed_curriculum.py` only when the reviewed
release intentionally changes seeded content. Both are idempotent, but a
deployment should not silently introduce content changes.

Frontend update:

```bash
cd frontend
npm ci
VITE_API_URL= npm run build
docker cp dist/. nexus-frontend:/usr/share/nginx/html/
docker cp nginx.host.conf nexus-frontend:/etc/nginx/conf.d/default.conf
docker exec nexus-frontend nginx -t
docker exec nexus-frontend nginx -s reload
curl --fail http://127.0.0.1/health
```

### Service Desk Simulator on the active host deployment

The active systemd/SQLite topology runs the separate Next.js simulator in its
own container on the private `nexus-production` Docker network, with host
loopback port `13000` retained for local diagnostics. `frontend/nginx.host.conf`
performs Nexus authentication before proxying `/service-desk` to the container
by its Docker DNS name. The existing `nexus-frontend` container must join the
same private network.
The container does not receive the full backend environment; pass only the
shared JWT settings it needs:

Run this from the repository root — `service-desk-app/` is a subdirectory of
this repository now, so the image tag is derived from this repo's own HEAD,
the same commit that produced the `service-desk-app/` sources being built:

```bash
SERVICE_DESK_IMAGE="nexus-service-desk:$(git rev-parse --short=12 HEAD)"
docker build \
  --build-arg NEXUS_INTEGRATION=1 \
  --build-arg NEXT_PUBLIC_NEXUS_INTEGRATION=1 \
  --build-arg SERVICE_DESK_BASE_PATH=/service-desk \
  -f 'service-desk-app/docker/web.Dockerfile' \
  -t "$SERVICE_DESK_IMAGE" 'service-desk-app'

read_nexus_env_value() {
  backend/.venv/bin/python - "$1" <<'PY'
import sys
from dotenv import dotenv_values
value = dotenv_values("backend/.env").get(sys.argv[1])
if not value:
    raise SystemExit(f"Missing {sys.argv[1]} in backend/.env")
print(value)
PY
}
export JWT_SECRET_KEY="$(read_nexus_env_value JWT_SECRET_KEY)"
export JWT_ALGORITHM="$(read_nexus_env_value JWT_ALGORITHM)"
docker network inspect nexus-production >/dev/null 2>&1 || docker network create nexus-production
docker network inspect nexus-production --format '{{json .Containers}}' | grep -q 'nexus-frontend' || \
  docker network connect nexus-production nexus-frontend
if docker inspect nexus-service-desk >/dev/null 2>&1; then
  if docker inspect nexus-service-desk-predeploy >/dev/null 2>&1; then
    echo 'ERROR: nexus-service-desk-predeploy already exists; resolve it before continuing.' >&2
    exit 1
  fi
  docker stop nexus-service-desk
  docker rename nexus-service-desk nexus-service-desk-predeploy
fi
docker run -d --name nexus-service-desk --restart unless-stopped \
  --network nexus-production \
  --add-host=backend-host:host-gateway \
  --publish 127.0.0.1:13000:3000 \
  --env JWT_SECRET_KEY --env JWT_ALGORITHM \
  --env NEXUS_ADMIN_CHECK_URL=http://backend-host:8000 \
  --env SERVICE_DESK_BASE_PATH=/service-desk \
  --env NEXUS_INTEGRATION=1 \
  --env NEXT_PUBLIC_BASE_PATH=/service-desk \
  --env NEXT_PUBLIC_NEXUS_INTEGRATION=1 \
  --health-cmd="node -e \"fetch('http://127.0.0.1:3000/service-desk/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))\"" \
  --health-interval=30s --health-timeout=10s --health-retries=3 \
  --health-start-period=15s \
  "$SERVICE_DESK_IMAGE"
unset JWT_SECRET_KEY JWT_ALGORITHM
unset -f read_nexus_env_value

curl --fail http://127.0.0.1:13000/service-desk/api/health
docker inspect nexus-service-desk --format '{{.State.Health.Status}}'
docker cp frontend/nginx.host.conf nexus-frontend:/etc/nginx/conf.d/default.conf
docker exec nexus-frontend nginx -t
docker exec nexus-frontend nginx -s reload
curl --fail http://127.0.0.1/service-desk/api/health
```

Before replacing an existing simulator container, record its immutable image
ID and save the live nginx configuration in the release backup directory. A
rollback restores that nginx file, reloads nginx, and starts a container from
the recorded image ID on the same private Docker network and loopback port.
Never publish port `13000` on a LAN or public interface.

The frontend is a Vite SPA using React Router 7 declarative routing; it does
not use data routers, SSR, hydration serialization, actions, or RSC mode.
`safeNextPath()` rejects both protocol-relative and backslash-confused
redirects. `npm audit --audit-level=high` remains the release gate.

The project directory permissions protect `backend/.env`; do not replace the
copy-based frontend deployment with a bind mount that requires making the
repository world-traversable.

## Docker Compose deployment

Root `.env` supplies `POSTGRES_PASSWORD` and optional `VITE_API_URL` compose
variables. Application settings still come from `backend/.env`, **except**
`JWT_SECRET_KEY` and `JWT_ALGORITHM`, which the `service-desk-web` service
reads from root `.env` (see `docker-compose.yml`). These two values MUST be
identical to the `JWT_SECRET_KEY`/`JWT_ALGORITHM` set in `backend/.env` —
the backend signs the `student_session` cookie with its copy and
service-desk-app verifies it with its own, so a mismatch (or an unset root
`.env` value) silently breaks the Service Desk Simulator login bridge:
every request looks unauthenticated and users are bounced back to
`/login` in a loop, with no error logged on either side.

```bash
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
docker compose exec backend python seed_curriculum.py
docker compose ps
curl --fail http://127.0.0.1:8000/health
```

### Isolated staging deployment

Staging uses the same production Dockerfiles with separate Compose resources,
ports, and PostgreSQL volume. Create a gitignored `.env.staging` with
`POSTGRES_PASSWORD`, the exact `JWT_SECRET_KEY` and `JWT_ALGORITHM` values from
`backend/.env`, and these non-secret bindings:

```dotenv
NEXUS_BACKEND_BIND=127.0.0.1:18000
NEXUS_FRONTEND_BIND=18081
VITE_API_URL=
```

Then deploy with both Compose files. The staging override disables secure
cookies only because the LAN staging endpoint is HTTP and permits only the LAN
staging frontend as a CORS origin; production continues to use
`COOKIE_SECURE=true` and its own CORS configuration from `backend/.env`.

```bash
docker compose -p nexus-staging --env-file .env.staging \
  -f docker-compose.yml -f docker-compose.staging.yml build --pull
docker compose -p nexus-staging --env-file .env.staging \
  -f docker-compose.yml -f docker-compose.staging.yml up -d
```

The staging frontend is available at `http://192.168.0.101:18081`, and the
simulator is mounted at `/service-desk`. Never use the `nexus-staging` project
name or `.env.staging` file for production deployment commands.

The compose services use named `pgdata` and `uploads` volumes. Do not delete or
recreate those volumes during an ordinary deployment.

## SQLite backup and restore

`scripts/backup_sqlite.sh` uses SQLite's online backup API, compresses the
database, creates a timestamp-matched uploads archive, rejects suspiciously
small database backups, and keeps 14 days. The script documents the
production cron entry. `NEXUS_SQLITE_DB`, `NEXUS_UPLOADS_DIR`,
`NEXUS_BACKUP_DIR`, and `NEXUS_BACKUP_STAMP` may be set to rehearse safely
against an isolated copy; production defaults remain unchanged.

Test a backup without replacing production:

```bash
gzip -cd "$HOME/backups/nexus/nexus-YYYY-MM-DD.db.gz" > /tmp/nexus-restore-check.db
python3 - <<'PY'
import sqlite3
db = sqlite3.connect("/tmp/nexus-restore-check.db")
print(db.execute("PRAGMA integrity_check").fetchone()[0])
print(db.execute("PRAGMA foreign_key_check").fetchall())
PY
```

Expected results are `ok` and an empty foreign-key list. Remove the scratch
copy after verification. A real restore requires a maintenance window: stop
the backend, preserve the current database as a timestamped rollback copy,
restore the verified backup to the exact configured path, restore uploads,
start the backend, and run health/auth/ownership smoke tests. Never restore a
database while the application is writing to it.

## PostgreSQL backup and restore

`scripts/backup_db.sh` creates a compressed `pg_dump` and an uploads archive
for the compose deployment. Test a dump against a disposable PostgreSQL
database before relying on it. For a real restore, stop application writes,
preserve the current database, restore with the PostgreSQL tools matching the
dump format, restore the uploads archive, run `python -m alembic current`, and complete
the smoke checklist below.

## Post-deployment smoke checklist

- Health endpoint and backend startup logs are clean.
- Student login, Home, My Training, a week, All Course Content, Quiz Library,
  Practice Library, Progress, and logout work.
- A student cannot access another student's submissions or evidence.
- Admin login, Dashboard, Learning Content (including Weekly Training and its
  validator), Students, Ticket Review, labs, and logout work.
- Student credentials cannot open admin APIs or admin pages.
- New migrations are at head and database integrity checks pass.
- Browser console and network panels show no new errors.
- Cloudflare RUM is either intentionally approved by the operator or disabled
  at the edge; Nexus's strict CSP remains unchanged.
- Both desktop and mobile navigation expose the same grouped destinations.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request (any target branch —
this repo stages work through intermediate integration branches before
reaching `main`, so PRs are not restricted to a `main` base) and on every
push to `main`. It never touches production — every job uses a throwaway
SQLite database and generated-per-run credentials, never the real
`backend/nexus.db` or `backend/.env`. An older run for the same branch is
cancelled automatically when a newer commit arrives.

Five independent jobs, so a failure is easy to attribute:

- **Backend quality and tests** — `pip check`, Ruff, `python -m compileall`,
  the full `pytest` suite, and a manifest-based `pip-audit` against
  `backend/requirements.txt`.
- **Database, migrations, and seeds** — migrates an empty database to head,
  confirms the head revision, seeds it, and confirms 35 modules / 320
  activities / 137 mapped videos / one required Week 0 orientation activity /
  no duplicate seed records / clean SQLite integrity and foreign-key checks.
  `backend/tests/test_orientation_seed.py` (also run here) is the source of
  truth for the seed-idempotency proof.
- **Frontend validation** — `npm audit --audit-level=high`, `npm run build`,
  `npm run cli:validate`, `npm run cli:sanity`. There is no frontend unit
  test script; real-browser coverage runs in the Playwright job instead.
- **Service Desk quality and tests** — `pnpm lint`, `pnpm typecheck`,
  `pnpm test`, `pnpm build`, and `pnpm audit --audit-level=high` inside
  `service-desk-app/`. This is the in-repo replacement for the standalone
  app's old CI, which lived at `service-desk-app/.github/workflows/ci.yml`
  and stopped running the moment the app became a subdirectory of this repo
  — GitHub Actions only discovers workflow files under the repository's own
  root `.github/workflows/`, not in nested subdirectories.
  Note: `service-desk-app/tests/e2e/remote-desktop-workflows.spec.ts` and
  its `playwright.config.ts` exist but are currently dead — no package.json
  in the workspace declares `@playwright/test` as a dependency, so
  `pnpm exec playwright` cannot resolve it. Pre-existing breakage,
  independent of this merge; not wired into CI here. Add the dependency and
  confirm the suite actually passes before adding that job.
- **Playwright browser tests** — real Chromium against an isolated local
  stack (see below), covering My Training, lesson objectives, quiz pass/fail
  messaging, Progress labels, and authentication/navigation regressions, at
  both the 1440x1000 desktop and 375x812 mobile viewports, plus the four
  Nexus <-> Service Desk integration scenarios in
  `service-desk-integration.spec.js` (offline outbox retry ordering, ticket
  completion gating on pending evidence, clean-browser snapshot restore, and
  real UI resolution with server-side grading/XP/evidence). The isolated
  stack now starts Service Desk in-process too (see "Browser test fixture
  harness" below), so this no longer needs a separate Compose stack.

### Reproducing each job locally

```bash
# Backend quality and tests
cd backend
pip check
ruff check app tests seed.py seed_curriculum.py
python -m compileall -q app tests seed.py seed_curriculum.py
python -m pytest -q
pip install pip-audit && pip-audit -r requirements.txt

# Database, migrations, and seeds (idempotency proof)
cd backend && python -m pytest -q tests/test_orientation_seed.py

# Frontend validation
cd frontend
npm audit --audit-level=high
npm run build
npm run cli:validate
npm run cli:sanity

# Service Desk quality and tests
cd service-desk-app
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm audit --audit-level=high

# Nexus <-> Service Desk Playwright integration — see "Browser test fixture harness" below
```

### Browser test fixture harness

`scripts/e2e/` holds the reusable local-stack harness both CI and developers
use for real-browser testing:

- `seed_fresh_db.sh` — migrates and seeds a throwaway SQLite database. Refuses
  to run against anything other than a `sqlite:///` URL, and refuses the
  production `backend/nexus.db` path specifically.
- `start_local_stack.sh` — generates fresh random credentials (never
  hard-coded, never logged), seeds a scratch database, starts an isolated
  backend (default port 8011), Service Desk (default port 3001, from the
  in-repo `service-desk-app/`), and frontend (default port 5173) — the Vite
  dev server proxies `/api` and `/service-desk` to the other two so all
  three share one browser origin (see `frontend/vite.config.js`) — creates
  the `browser-training-student`, `browser-qualified-student`, and two more
  fixture student accounts plus their Service Desk assignments, and writes
  the resulting `NEXUS_E2E_*` variables to `<scratch dir>/stack.env` (and to
  `$GITHUB_ENV` under GitHub Actions). Requires Service Desk's own
  dependencies already installed (`cd service-desk-app && pnpm install`).
- `stop_local_stack.sh` — kills both processes and deletes the scratch
  directory (database, uploads, logs, generated credentials). Always run
  this from an `if: always()` step (or after a local run, success or not) so
  cleanup happens even when a test fails.

Local usage:

```bash
cd service-desk-app && pnpm install --frozen-lockfile && cd ..
bash scripts/e2e/start_local_stack.sh
set -a && source /tmp/nexus-e2e-XXXXXX/stack.env && set +a   # path printed by start_local_stack.sh
cd frontend && npx playwright test tests/e2e/my-training.spec.js tests/e2e/service-desk-integration.spec.js --reporter=list
cd .. && bash scripts/e2e/stop_local_stack.sh
```

`scripts/e2e/run_launch_verification.sh` wraps the same start/test/stop
sequence for just the integration spec, with results logged under
`artifacts/e2e-launch-verification/`.

Expected runtime: each of the backend/database/frontend/service-desk CI jobs
finishes in well under two minutes; the Playwright job's two browser-test
steps themselves take under a minute combined once the stack is up.

### Inspecting a failed CI run

The Playwright job uploads its HTML report, traces, and screenshots as a
`playwright-report` artifact only when the job fails (5-day retention). It
never includes the scratch database, uploads directory, or generated
credentials — those live under the stack's scratch directory, which is
deleted by `stop_local_stack.sh` before the artifact step runs. Download the
artifact from the failed run's Summary page and open
`playwright-report/index.html`, or run `npx playwright show-trace
<trace.zip>` on a downloaded trace.

## Service Desk Simulator

The simulator is a Next.js application reverse-proxied at `/service-desk`.
It lives in this repository at `service-desk-app/`. The root
`docker-compose.yml` builds it from `./service-desk-app` directly. For the
active systemd/standalone-host deployment (built and run as its own Docker
container rather than through Compose — see "Service Desk Simulator on the
active host deployment" above), update the `service-desk-host:3000`
placeholder in `frontend/nginx.host.conf` to the simulator's deployed host
and port.

Automated Proxmox/Guacamole delivery remains opt-in until a staging test proves
start, scoped student access, isolation, refresh recovery, expiry, and cleanup.
Manual VM delivery remains the safe fallback.
