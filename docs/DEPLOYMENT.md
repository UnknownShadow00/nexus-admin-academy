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

The Service Desk Scenario Foundation is also disabled by default. Keep
`SERVICE_DESK_LAB_ENABLED=false` in production until a separately approved
student rollout. `SERVICE_DESK_LAB_ADMIN_ENABLED=true` may be used only for a
controlled administrator validation session; it does not enable student APIs
or add navigation. The additive Scenario Foundation migration does not seed
scenarios automatically—do not run seed commands in production merely to
deploy it.

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
variables. Application settings still come from `backend/.env`.

```bash
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
docker compose exec backend python seed_curriculum.py
docker compose ps
curl --fail http://127.0.0.1:8000/health
```

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

## Service Desk Lab private beta

Run `alembic upgrade head` before restarting the backend. Keep `SERVICE_DESK_LAB_ENABLED=false` and `SERVICE_DESK_LAB_ADMIN_ENABLED=false` in `backend/.env` for the first deployment. After health/authentication validation, an operator may enable administrator review only; student access additionally requires an audited explicit beta enrollment through the supported administrator API. Do not enable the student flag globally or use unapproved browser credentials. Service Desk Lab is separate from legacy Support Tickets, which must be included in the normal smoke checklist unchanged.

For an administrator-only review, leave `SERVICE_DESK_LAB_ENABLED=false`, set only `SERVICE_DESK_LAB_ADMIN_ENABLED=true`, restart the backend, and use an approved administrator account to inspect the five published versions, health status, Knowledge Base, replay, assignments, and beta-enrollment controls. Confirm student `/service-desk` navigation and APIs remain unavailable. Return the administrator flag to `false` and restart after the approved review session unless continued review has been explicitly authorized. Do not enroll production students or set the student flag during this step.

Automated Proxmox/Guacamole delivery remains opt-in until a staging test proves
start, scoped student access, isolation, refresh recovery, expiry, and cleanup.
Manual VM delivery remains the safe fallback.
