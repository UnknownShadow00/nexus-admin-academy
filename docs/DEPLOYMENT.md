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
./.venv/bin/alembic upgrade head
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
database, synchronizes uploads, rejects suspiciously small backups, and keeps
14 days. The script documents the production cron entry.

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
dump format, restore the uploads archive, run `alembic current`, and complete
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

`.github/workflows/ci.yml` runs on every pull request targeting `main` and on
every push to `main`. It never touches production — every job uses a
throwaway SQLite database and generated-per-run credentials, never the real
`backend/nexus.db` or `backend/.env`. An older run for the same branch is
cancelled automatically when a newer commit arrives.

Four independent jobs, so a failure is easy to attribute:

- **Backend quality and tests** — `pip check`, Ruff, `python -m compileall`,
  the full `pytest` suite, and a manifest-based `pip-audit` against
  `backend/requirements.txt`.
- **Database, migrations, and seeds** — migrates an empty database to head,
  confirms the head revision, seeds it, and confirms 25 weeks / 296
  activities / 137 mapped videos / one required Week 0 orientation activity /
  no duplicate seed records / clean SQLite integrity and foreign-key checks.
  `backend/tests/test_orientation_seed.py` (also run here) is the source of
  truth for the seed-idempotency proof.
- **Frontend validation** — `npm audit --audit-level=high`, `npm run build`,
  `npm run cli:validate`, `npm run cli:sanity`. There is no frontend unit
  test script; real-browser coverage runs in the Playwright job instead.
- **Playwright browser tests** — real Chromium against an isolated local
  stack (see below), covering My Training, lesson objectives, quiz pass/fail
  messaging, Progress labels, and
  authentication/navigation regressions, at both the 1440x1000 desktop and
  375x812 mobile viewports. Both specs currently run in under 20 seconds
  combined, so the full pair runs on every PR rather than splitting a
  "critical" subset out to a nightly job — revisit that split only if the
  suite grows slow enough to justify it.

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

# Playwright browser tests — see "Browser test fixture harness" below
```

### Browser test fixture harness

`scripts/e2e/` holds the reusable local-stack harness both CI and developers
use for real-browser testing:

- `seed_fresh_db.sh` — migrates and seeds a throwaway SQLite database. Refuses
  to run against anything other than a `sqlite:///` URL, and refuses the
  production `backend/nexus.db` path specifically.
- `start_local_stack.sh` — generates fresh random credentials (never
  hard-coded, never logged), seeds a scratch database, starts an isolated
  backend (default port 8011) and frontend (default port 5173), creates the
  `browser-training-student` and `browser-qualified-student` fixture
  accounts, and writes the resulting `NEXUS_E2E_*` variables to
  `<scratch dir>/stack.env` (and to `$GITHUB_ENV` under GitHub Actions).
- `stop_local_stack.sh` — kills both processes and deletes the scratch
  directory (database, uploads, logs, generated credentials). Always run
  this from an `if: always()` step (or after a local run, success or not) so
  cleanup happens even when a test fails.

Local usage:

```bash
bash scripts/e2e/start_local_stack.sh
set -a && source /tmp/nexus-e2e-XXXXXX/stack.env && set +a   # path printed by start_local_stack.sh
cd frontend && npx playwright test tests/e2e/my-training.spec.js tests/e2e/service-desk-disabled.spec.js --reporter=list
cd .. && bash scripts/e2e/stop_local_stack.sh
```

Expected runtime: each of the four CI jobs finishes in well under two
minutes; the Playwright job's browser-test step itself takes under 20
seconds once the stack is up.

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

The simulator is a separate Next.js application reverse-proxied at
`/service-desk`. The root compose file expects its repository at
`../Nexus dupe/service-desk-app`, alongside this repository, and proxies it
through the frontend nginx container. For standalone-host deployments, update
the `service-desk-host:3000` placeholder in `frontend/nginx.host.conf` to the
simulator's deployed host and port.

Automated Proxmox/Guacamole delivery remains opt-in until a staging test proves
start, scoped student access, isolation, refresh recovery, expiry, and cleanup.
Manual VM delivery remains the safe fallback.
