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

`scripts/deploy.sh` takes a **host-wide `flock`** first
(`/run/lock/nexus-admin-academy-deploy.lock` — a shared path, not per-account,
pre-created world-writable) so two operators can't race even from different Unix
accounts, then — **after** confirming it is the serving checkout (steps 1–2) and
unless `--dry-run` — refreshes **standalone copies of itself at
`~/bin/nexus-deploy` and of the SQLite backup helper at
`~/bin/nexus-backup-sqlite`** (both used when a rollback target predates or
changes the in-repo versions). In order:

1. **resolves the serving checkout from `nexus-admin-academy.service`'s
   `WorkingDirectory`, not from its own path** — so `~/bin/nexus-deploy` works
   when run from anywhere. Run from an in-repo copy, it additionally refuses
   unless that copy's tree *is* the serving checkout (so you can't "deploy" a
   worktree by mistake). Refuses a dirty working tree;
2. `git fetch`, then resolves the pinned target ref to a concrete SHA;
3. runs `scripts/predeploy_check.sh` **while the old backend is still up** (its
   live-health / container / env checks need it running). **Full output tee'd
   to the deploy log**; a failing gate aborts unless `--force-predeploy` (after
   you review every `FAIL` line in the log). The *target*-schema check is
   step 6, not this;
4. **stops the backend.** It runs from this checkout and its handlers do lazy
   imports, so files must not change under a live process. It stays down until
   step 8;
5. `git checkout --detach` the target SHA; then **snapshot `backend/.venv`**
   (same-filesystem hardlink copy) and `pip install -r backend/requirements.txt`
   — before any target-tree Alembic call (`env.py` / migrations import app
   modules a new release may add a dependency for). Skip with `--skip-deps`.
   With `--frontend`, `npm ci` + Vite build here too;
6. **schema compatibility guard — fails closed.** Requires exactly one target
   Alembic head and one live DB revision (rejects a divergent migration tree or
   a branched DB); refuses unless it can positively confirm the live revision is
   contained in the target tree; an Alembic introspection error (its behaviour
   when the DB is stamped with a revision the tree lacks) is treated as
   *incompatible*, not "unknown". Runs **even with `--skip-migrations`**, and
   **`--skip-migrations` is itself refused unless the live DB is already at the
   target head** (you can't skip a migration that's actually due).
   Override with `--allow-db-ahead` only after restoring a matching DB backup.
   Alembic is **pinned to the `.env` database** for this and the migration step
   (an ambient `DATABASE_URL` in your shell is ignored, so the guard, the
   backup, the migration and the restart all act on the same file);
7. **always** takes a fresh SQLite + uploads snapshot (stamp
   `predeploy-<sha>-<ts>`) while the service is still down (step 4), using the
   stable backup helper copied to `~/bin/nexus-backup-sqlite` (not the in-tree
   `scripts/backup_sqlite.sh`, which a historical rollback may have already
   checked out to an older/missing version) — one snapshot that covers both the
   Alembic upgrade
   **and** the target's own lifespan startup writes (`seed_cli_labs` /
   `recompute_weekly_domain_leads` / `db.commit` in `backend/app/main.py`, which
   run even on a `--skip-migrations` or already-at-head deploy) — then, if a
   migration is due, `alembic upgrade head`. `--skip-migrations` skips only the
   upgrade, not the snapshot;
8. `sudo systemctl start`, then polls `http://127.0.0.1:8000/health`.
   **Once healthy, the code + schema are committed** (see Rollback);
9. with `--frontend`, snapshots the live container assets/config, swaps in the
   build from step 5, `nginx -t`, reloads, then verifies the **deployed SPA
   itself** at `http://127.0.0.1/` — the response must be an HTTP success *and*
   the Nexus `index.html` (app root div + app `<title>`), not the backend
   `/health` proxy — so an nginx that is up but serving stale/broken/missing
   static files is caught and the previous frontend is restored;
10. appends timestamped lines to `~/deploy-logs/nexus-deploy.log` for every run
    (plan, each stage, and any rollback).

Use `--dry-run` to preview the resolved SHAs without touching anything.
**Every deploy is a short maintenance window** — the backend is down from
step 4 to step 8 (seconds for a code-only deploy, longer with
deps/migration/build). Zero-downtime would need a separate release directory
with an atomic switch, or blue/green — out of scope for this single-process,
shared-checkout deployment.

One consequence of that same limitation: at step 8 the new process binds
`:8000` and nginx keeps proxying `/api/` + `/auth/` to it, so it is publicly
reachable for the brief interval between "started" and "first `/health`
response". The first health probe is issued with no delay, so for a healthy
process this is sub-second; but a write accepted in that window on a deploy
whose health check then fails is discarded by the automatic
restore-pre-start-DB rollback. Eliminating that window (not just shrinking
it) is the same blue/green work noted above.

**Rollback — automatic on any failure once the backend has been stopped
(step 4).**

- **Before the step-8 health check passes** — full unwind: **confirm the unit
  is actually inactive** (if a rollback `stop` fails and the unit stays up, the
  rollback aborts here rather than rewrite files under a live process); check
  the previous SHA back out (and verify the worktree is clean afterwards); if
  deps were installed, **restore the `backend/.venv` snapshot** (a dependency
  up/downgrade otherwise outlives the failed release); if a migration ran **or
  the target was started at all** (its lifespan startup can write even on a
  code-only deploy), **restore the pre-start database snapshot** (SQLite DDL here
  is non-transactional, so a half-applied migration is possible — the snapshot is
  the only safe restore; the live DB's owner and mode are reapplied). **If that
  DB restore itself fails, the service is left stopped** — deploy.sh will not
  start any release against a half-restored database. Otherwise start the service on
  the old SHA and re-health-check (`MANUAL INTERVENTION NEEDED` in the log if it
  still can't come up).
- **After step 8** — only the `--frontend` swap can still fail, and the NEW
  backend has begun accepting writes, so the **database is not rolled back**.
  Only the frontend snapshot is restored; the backend stays on the new commit
  and the frontend is fixed forward. The deploy still exits non-zero.

The venv and frontend snapshots are deleted on a successful deploy.

**Rolling back a *past* deploy that changed the schema is not just
`deploy.sh <old-sha>`.** Checking out older code leaves the newer schema in
place. `deploy.sh` detects this (step 6) and refuses. To do it safely:

1. `scripts/backup_sqlite.sh` — snapshot the current (newer) DB first. **Keep
   this file.** If step 3 fails partway, `deploy.sh` cannot restore it for you
   (it never saw the pre-swap state): its automatic rollback will stop, log
   `MANUAL INTERVENTION NEEDED`, and leave the service down — you then restore
   *this* snapshot by hand before retrying or starting the service;
2. restore a database backup taken at or before the target commit's migration
   head (from `~/backups/nexus/`, e.g. the `predeploy-<sha>-*` backup that
   deploy.sh took just before that migration) — stop the service, replace
   `backend/nexus.db`, remove stale `-wal`/`-shm`;
3. `scripts/deploy.sh --allow-db-ahead --force-predeploy <old-sha>` — restart on
   the old code. **Both flags are required here:** `--allow-db-ahead` because
   you have deliberately put the DB behind the current tree, and
   `--force-predeploy` because you stopped the service in step 2, so
   `predeploy_check.sh`'s live-backend health/liveness checks *will* fail. Read
   every `FAIL` line it logs to `~/deploy-logs/nexus-deploy.log` and confirm the
   only failures are the expected "backend not responding" ones before letting
   the deploy continue.

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

### Alembic production safety guard

`backend/app/db_guard.py` (wired into `alembic/env.py`) refuses any
schema-mutating Alembic command (`upgrade` / `downgrade` / `stamp`) that
resolves to the live production SQLite file
(`backend/nexus.db`) unless the operator explicitly opts in with
`NEXUS_ALLOW_PROD_MIGRATION=1`. It exists because on 2026-08-29 a bare
`alembic upgrade head` with `DATABASE_URL` unset fell back to `alembic.ini`
(`sqlalchemy.url = sqlite:///./nexus.db`) and migrated production
(`tasks/lessons.md`).

- **Read-only inspection is never blocked** — `alembic current` / `heads` /
  `history` / `show` work against production with no opt-in, so
  `predeploy_check.sh` and rollback introspection are unaffected.
- **`scripts/deploy.sh` opts in for you** — its `alembic_backend()` wrapper
  sets both `DATABASE_URL` (pinned to the `.env` database) and
  `NEXUS_ALLOW_PROD_MIGRATION=1`. The sanctioned way to migrate production is
  a normal `deploy.sh` run; it still enforces `--allow-db-ahead` and every
  other predeploy guard — this check is additive to those, not a replacement.
- **The stable `~/bin/nexus-deploy` copy must be refreshed** from the updated
  `scripts/deploy.sh` (per the "stable copy" note above) so the opt-in is
  present there too.

Scratch / verification workflow (never touches production):

```bash
cd backend
DATABASE_URL="sqlite:////tmp/nexus-scratch.db" ./.venv/bin/python -m alembic upgrade head
DATABASE_URL="sqlite:////tmp/nexus-scratch.db" ./.venv/bin/python -m alembic downgrade -1
```

Deliberate manual production migration (only outside `deploy.sh`, e.g.
recovery):

```bash
cd backend
# take a fresh verified backup first (SQLite online-backup API; see below)
NEXUS_ALLOW_PROD_MIGRATION=1 DATABASE_URL="sqlite:///$(pwd)/nexus.db" \
  ./.venv/bin/python -m alembic upgrade head
```

Rules:

- **Never** run Alembic without first confirming the database it resolved to
  (the guard prints it on refusal; on success, check the `Running upgrade …`
  lines name the revisions you expect).
- **Never** suppress migration output with `>/dev/null 2>&1` — you cannot see
  which database was touched or whether it succeeded.
- CI is unaffected: the `db-migrations-seeds` job sets `DATABASE_URL` to a
  throwaway path under `$RUNNER_TEMP`, which never resolves to production.

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
# alembic is guarded — either run the migration through scripts/deploy.sh, or
# opt in explicitly (see "Alembic production safety guard" above):
NEXUS_ALLOW_PROD_MIGRATION=1 DATABASE_URL="sqlite:///$(pwd)/nexus.db" \
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

## V2 pilot operations

Everything in this section is read-only tooling and documentation for the V2
pilot cutover. None of it is wired into `scripts/deploy.sh`, and none of the
install commands below are executed by any script in the repository — an
operator runs them deliberately.

### Per-student pilot targeting

V2 access is the conjunction of two controls, both read from `backend/.env`:

```
V2_CURRICULUM_ENABLED=true      # master kill switch — off means nobody
V2_PILOT_STUDENT_IDS=3,7        # who is enrolled while the switch is on
```

It fails closed. Turning the master switch on without naming anyone enrols
nobody, so a mis-set flag cannot expose the whole cohort mid-pilot. The list
tolerates whitespace, duplicates, and junk entries — anything that is not a
positive integer is dropped rather than failing the list. Mentors
(`students.is_mentor`) reach V2 without being enrolled, so they can preview
the cohort's experience; admin surfaces authorize through `verify_admin` and
the master switch alone.

Both values are parsed in exactly one place, `app/services/v2_access.py`.
Do not read these variables anywhere else.

To change the roster, edit `backend/.env` and restart the backend service.
Confirm afterwards with `scripts/pilot_status.sh`, which reports the flag
state and how many students are enrolled — never which.

### Pilot preflight

`scripts/v2_pilot_preflight.py` answers one question: if the pilot were
switched on against this database now, would a student hit a wall? It opens
the database, runs SELECTs, and rolls back — it never writes.

```bash
cd backend
./.venv/bin/python ../scripts/v2_pilot_preflight.py
./.venv/bin/python ../scripts/v2_pilot_preflight.py --json
./.venv/bin/python ../scripts/v2_pilot_preflight.py --database-url sqlite:///./copy.db
./.venv/bin/python ../scripts/v2_pilot_preflight.py --check-links     # opt-in network
```

It checks the Alembic revision and head count; curriculum counts and
student-visible modules; that no assessment reports itself available while
being unopenable; which question banks are approved, published, blocked, or
missing approval; Service Desk stable keys, published versions, relationship
wiring, and all ten evidence-based INC2501–INC2510 fixtures; practical-to-lab
resolution, publication, `lab_type`, Proxmox independence, and explicit V2
launch relationships; required-resource URLs; duplicate stable keys; orphaned
rows; and V1 quiz visibility. It reports blocked banks — it never approves
them.

Exit status is 1 if any check FAILs. WARNs never fail the run.

For a cutover rehearsal on a disposable copy, capture V1 visibility first and
compare after loading content:

```bash
./.venv/bin/python ../scripts/v2_pilot_preflight.py --database-url sqlite:///./copy.db --baseline /tmp/before.json
# ... run migrations and seed_v2_foundation.py against the copy ...
./.venv/bin/python ../scripts/v2_pilot_preflight.py --database-url sqlite:///./copy.db --compare-baseline /tmp/before.json
```

The comparison FAILs if any quiz became newly visible — or lost visibility —
in the legacy student surfaces.

### Loading V2 foundation content

`backend/seed_v2_foundation.py` is one logical transaction: it loads, then
validates, then commits once, and rolls back to the pre-load state on any
failure. Rehearse it first:

```bash
cd backend
./.venv/bin/python seed_v2_foundation.py --dry-run   # loads, validates, rolls back
./.venv/bin/python seed_v2_foundation.py
```

Validation holds only student-reachable modules to the bar. A module still
being authored is reported as a note, not a failure.

### Pilot status

`scripts/pilot_status.sh` is the whole monitoring story for a cohort of five
to ten students — no Prometheus, no Grafana, no agent. It modifies nothing:
every database read opens SQLite read-only.

```bash
scripts/pilot_status.sh
scripts/pilot_status.sh --db /path/to/copy.db
scripts/pilot_status.sh --json
```

| Row | Meaning |
| --- | --- |
| backend / frontend / service desk | HTTP health probes |
| Docker / Service Desk container | container state where Docker is available; otherwise SKIP |
| backend service, grading timer | `systemctl is-active`; SKIP where systemd or the unit is absent |
| disk free | `OK` / `LOW` (under 4 GiB) / `CRITICAL` (under 2 GiB) |
| V2 master flag | `V2_CURRICULUM_ENABLED` as configured |
| pilot students enrolled | how many ids are in the allowlist, never which |
| alembic revision | read from `alembic_version`, not the alembic CLI |
| pending / stale grading jobs | queue depth, and jobs stuck over 30 minutes |
| stale processing leases | crashed workers holding a lease over 10 minutes |
| service desk attempts | in progress, and failures in the last 24 hours |
| V2 activity (24h) | whether pilot students are actually working |
| latest backup age | newest `*.db.gz`; `STALE` past 48 hours |

It degrades rather than failing: on a machine without systemd, Docker, a
database, or a running backend it prints SKIP with a reason and still exits 0.
A row reading `SKIP: no such column` means the target database predates that
migration — useful in itself.

### Grading worker installation

The unit files in `deploy/systemd/` are **not installed by this repository**.
Validate them first — the check is read-only, needs no root, and installs
nothing:

```bash
cd backend
./.venv/bin/python ../scripts/check_grading_worker_install.py
```

It confirms both units parse, runs `systemd-analyze verify` where available,
decodes the `\x20`-escaped paths and checks they exist, verifies the virtualenv
interpreter and worker script, imports the worker without running it, checks
the timer interval, and compares User/Group and WorkingDirectory against the
live `nexus-admin-academy.service`.

Once it passes, an operator installs the timer by hand:

```bash
sudo install -m 0644 deploy/systemd/nexus-grading-worker.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/nexus-grading-worker.timer  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nexus-grading-worker.timer

systemctl list-timers nexus-grading-worker.timer
systemctl status nexus-grading-worker.service
journalctl -u nexus-grading-worker.service --since '-15 min'
```

To roll back:

```bash
sudo systemctl disable --now nexus-grading-worker.timer
sudo rm /etc/systemd/system/nexus-grading-worker.{service,timer}
sudo systemctl daemon-reload
```

Until the timer is installed, no pending grade is ever processed: short-answer
and Explain submissions queue up and wait. Installing it is a prerequisite for
the pilot, not an optimisation.

### Cutover backup retention safety

The nightly job prunes with:

```bash
find "$DEST" -name 'nexus-*.db.gz' -mtime +14 -delete
```

A cutover snapshot named with the `nexus-` prefix is therefore deleted
fourteen days later — exactly when someone finally needs it. Use the helper,
which writes `v2-cutover-<revision>-<stamp>.db.gz`, a name that glob cannot
match:

```bash
scripts/make_cutover_snapshot.sh              # dry run — prints the plan only
scripts/make_cutover_snapshot.sh --confirm
```

It uses SQLite's online backup API (safe against a live writer), refuses a
label that would match the retention glob, applies the same 100 KiB sanity
floor as the nightly job, and never deletes anything. The nightly retention
policy itself is unchanged: a `v2-cutover-*` snapshot is kept until a human
removes it.

### Disk policy for the V2 rollout

`scripts/predeploy_check.sh` grades available space on the repository
filesystem:

| Free space | Result |
| --- | --- |
| under 2 GiB | FAIL — a deploy cannot complete |
| 2–4 GiB | PASS with a loud WARN — enough to deploy, not to rebuild images |
| 4–8 GiB | PASS |
| 8 GiB or more | PASS — recommended before a frontend or Service Desk rebuild |

Warnings never change the exit code, so ordinary development is not blocked.
Nothing is ever pruned automatically: review what would be removed before
reclaiming space by hand.

### Service Desk theme selection

The Service Desk resolves its first-paint theme in this order: an explicit
`light` or `dark` choice saved by the student, otherwise the operating-system
color-scheme preference, otherwise dark when browser preference detection is
unavailable. This remains browser-local; no account-level theme setting or
second Service Desk preference was added.
# Network exposure expectation

Production browser traffic should enter through nginx only. The backend on
port 8000, Service Desk application port, and any staging frontend ports must
remain loopback/container-network only unless an operator has explicitly
documented another requirement. `scripts/pilot_status.sh` reports externally
bound known ports as warnings; it never changes firewall or listener state.

For the final production-copy/cutover check, run V2 preflight with
`--production-candidate`. In that mode an uninstalled, disabled, inactive, or
otherwise unverifiable grading timer is a failure instead of a development-host
warning.
