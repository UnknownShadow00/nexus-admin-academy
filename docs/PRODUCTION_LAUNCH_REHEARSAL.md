# Production Launch Rehearsal

Date: 2026-08-08
Release branch: `prelaunch/final-hardening`
Production origin: `https://nexus.builtfromzero.fyi`

## Verdict

**READY WITH MANUAL CONFIGURATION AND CREDENTIAL ROTATION.** Do not restart
the production backend until every failing item from `scripts/predeploy_check.sh`
has been resolved. No production deployment was performed during this rehearsal.

## Verified production architecture

- Cloudflare Tunnel (`cloudflared.service`) terminates public HTTPS and sends
  `nexus.builtfromzero.fyi` to host port 80.
- `nexus-frontend` is an `nginx:alpine` container on port 80. The Vite `dist/`
  and `frontend/nginx.host.conf` are copied into the container; neither is a
  bind mount.
- `nexus-admin-academy.service` runs one Uvicorn/FastAPI process as user
  `nexus`, from `backend/.venv`, on host port 8000.
- Production data is SQLite at `backend/nexus.db`. Production is not the
  running `nexus-staging` PostgreSQL Compose project.
- `nexus-service-desk` is a standalone Next.js container on the private
  `nexus-production` network and loopback port `127.0.0.1:13000`.
- Evidence/uploads are under `backend/uploads`; application logs currently
  fall back to `backend/nexus.log`. The desired explicit log path is
  `/var/log/nexus/app.log`.

## Required manual configuration before restart

Edit the gitignored `backend/.env` without copying values into tickets or logs.
The following non-secret declarations are required:

```dotenv
APP_ENV=production
DATABASE_URL=sqlite:///./nexus.db
FRONTEND_URL=https://nexus.builtfromzero.fyi
CORS_ORIGINS=https://nexus.builtfromzero.fyi
UPLOAD_DIR=/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/uploads
APP_LOG_PATH=/var/log/nexus/app.log
COOKIE_SECURE=true
```

`JWT_SECRET_KEY` and `JWT_ALGORITHM` are present, valid in format, and match
the running Service Desk container. Keep those values synchronized whenever
the simulator container is replaced.

Before launch, rotate `ADMIN_PASSWORD` and all seven `SEED_PASSWORD_*` values
to unique secrets of at least 14 characters. The current fixed cohort accounts
still authenticate with the configured short seed passwords. Changing the env
file alone does not change existing student hashes: use Admin > Students to
set each account's new password, then verify the old credentials fail. Rotate
`ADMIN_API_KEY` in the approved secret store as part of the same maintenance
window. Do not run `seed_users.py` after the rotation; it intentionally skips
existing accounts.

Prepare the log directory and restrict the environment file:

```bash
sudo install -d -o nexus -g nexus -m 0750 /var/log/nexus
chmod 0600 backend/.env
```

The tracked standalone nginx template now sets `X-Forwarded-Proto: https` for
FastAPI and Service Desk proxy requests. This is required for the hardened
CSRF origin calculation behind the Cloudflare HTTPS boundary.

## Rehearsal evidence

- Runtime versions: backend Python 3.11.15 (pip 24.0), Node 22.23.1,
  npm 10.9.8, pnpm 10.15.1 as selected by the workspace, Docker 29.6.1,
  and Docker Compose 5.3.0.
- A SQLite online copy of production started and ended at
  `0041_verified_question_keys`; `alembic upgrade head` was a clean no-op.
  Integrity remained `ok`, foreign-key violations remained zero, and every
  checked row count was unchanged: students 8, quizzes 104, questions 966,
  quiz attempts 2, scenarios 13, versions 15, assignments 56, Service Desk
  attempts 140, events 1,364, grades 140, evidence 1, lab runs 2, and lesson
  notes 3. Questions 647 and 651 retained the verified D keys; question 970
  remained flagged and hidden. No checked seed duplicates were introduced.
- The revised backup script created a compressed database and matching uploads
  archive from an isolated copy. Restoring both into a second location passed
  integrity and foreign-key checks and restored students, quizzes, progress,
  Service Desk attempts, and scenario versions.
- Backend: Ruff and compilation passed; 340 tests passed; Alembic has one head.
  Service Desk: lint, typecheck, 251 tests, production build, and high-severity
  audit passed. Frontend: clean install, zero-vulnerability audit, production
  build, CLI validation, and CLI sanity passed.
- The launch suite passed 9/9 and the full browser suite passed 22/22. A
  separate isolated run created a Scenario Builder version and an
  authoritative Service Desk grade, replaced backend/frontend/Service Desk
  processes, then confirmed unchanged persistent row counts, healthy endpoints,
  and a successful post-restart admin login.
- The standalone nginx template passed `nginx -t` in an isolated container.
  Sensitive-looking paths returned 404, while live public SPA deep links for
  Today/training, Progress, lessons, quizzes, CLI labs, admin, Scenario Builder,
  Service Desk, and the application 404 route resolved without nginx 404s.
- Non-blocking warnings: nine dependency/test deprecation warnings, the Next.js
  ESLint-plugin detection warning (the explicit lint gate is clean), and host
  disk usage at 88% with about 6.6 GiB free. Monitor disk capacity.

## Exact pre-deployment sequence

Run from the repository root after the release has been merged locally:

```bash
git switch main
git pull --ff-only origin main
git status -sb
scripts/predeploy_check.sh
```

The check must end with `PREDEPLOY CHECK PASSED`. It prints presence/format
status only and never prints secret values.

Record the rollback SHA and deployed container identity:

```bash
git rev-parse HEAD
docker inspect nexus-service-desk --format '{{.Image}}'
docker exec nexus-frontend nginx -T > /tmp/nexus-nginx-predeploy.conf
```

Store those outputs in the restricted release record, not in the repository.

## Exact production backup and verification

The SQLite backup script uses the online backup API and now emits a matching,
timestamped uploads archive. Complete the builds and Service Desk image first,
then enter the maintenance window and stop every writer before taking the
paired backup:

```bash
docker stop nexus-frontend nexus-service-desk
sudo systemctl stop nexus-admin-academy.service
scripts/backup_sqlite.sh
ls -lh "$HOME/backups/nexus/"nexus-*.db.gz "$HOME/backups/nexus/"nexus-uploads-*.tar.gz
```

Select the just-created matching timestamp and verify it in isolation:

```bash
mkdir -p /tmp/nexus-predeploy-restore/uploads
gzip -cd "$HOME/backups/nexus/nexus-<TIMESTAMP>.db.gz" > /tmp/nexus-predeploy-restore/nexus.db
tar -xzf "$HOME/backups/nexus/nexus-uploads-<TIMESTAMP>.tar.gz" -C /tmp/nexus-predeploy-restore/uploads
python3 - /tmp/nexus-predeploy-restore/nexus.db <<'PY'
import sqlite3, sys
with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as db:
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    for table in ("students", "quizzes", "service_desk_attempts", "service_desk_scenario_versions"):
        assert db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] > 0
print("verified")
PY
```

Do not proceed unless this prints `verified` and both backup files have been
copied to storage outside the application host.

## Exact build and deployment commands

```bash
cd backend
.venv/bin/pip install -r requirements.txt
.venv/bin/pip check
.venv/bin/python -m compileall -q app tests seed.py seed_curriculum.py
.venv/bin/ruff check app tests seed.py seed_curriculum.py
.venv/bin/python -m pytest -q
.venv/bin/python -m alembic heads

cd ../frontend
npm ci
npm audit --audit-level=high
VITE_API_URL= npm run build
npm run cli:validate
npm run cli:sanity

cd ../service-desk-app
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm audit --audit-level=high
```

Build the immutable Service Desk image before stopping the existing container:

```bash
cd ..
SERVICE_DESK_IMAGE="nexus-service-desk:$(git rev-parse --short=12 HEAD)"
docker build --build-arg NEXUS_INTEGRATION=1 --build-arg NEXT_PUBLIC_NEXUS_INTEGRATION=1 --build-arg SERVICE_DESK_BASE_PATH=/service-desk -f service-desk-app/docker/web.Dockerfile -t "$SERVICE_DESK_IMAGE" service-desk-app
```

## Exact migration and restart commands

With writers still stopped from the paired backup, run:

```bash
cd backend
.venv/bin/python -m alembic current
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
DATABASE_URL=sqlite:///./nexus.db .venv/bin/python seed.py

sudo systemctl start nexus-admin-academy.service
curl --fail http://127.0.0.1:8000/health
sudo journalctl -u nexus-admin-academy.service -n 100 --no-pager
```

Replace the Service Desk container using the exact `docker run` command in
`docs/DEPLOYMENT.md`, passing the matching JWT variables from `backend/.env`,
then copy the frontend and nginx configuration while the frontend remains
stopped and start it only after the files are in place:

```bash
docker cp frontend/dist/. nexus-frontend:/usr/share/nginx/html/
docker cp frontend/nginx.host.conf nexus-frontend:/etc/nginx/conf.d/default.conf
docker start nexus-frontend
docker exec nexus-frontend nginx -t
docker exec nexus-frontend nginx -s reload
curl --fail http://127.0.0.1/health
curl --fail http://127.0.0.1:13000/service-desk/api/health
```

Keep the renamed `nexus-service-desk-predeploy` container stopped until the
production smoke test passes. Remove it only after the rollback window closes.

Do not expose Service Desk port 13000 beyond loopback. Confirm the replacement
container is on `nexus-production` with restart policy `unless-stopped`.

## 10–15 minute production smoke test

Use designated smoke-test accounts and remove any throwaway content afterward.

1. Confirm `/health` and `/service-desk/api/health` return 200 over public HTTPS.
2. Student: log in; open Today, one lesson, one quiz, and verify the explanation.
3. Confirm Progress records the quiz once and XP is not duplicated after refresh.
4. Open a CLI lab, enter a valid command, refresh, and confirm the lab still loads.
5. Start an assigned Service Desk ticket, perform one action, refresh/resume,
   complete it, and confirm its grade and evidence appear once.
6. Log out and confirm `/service-desk` redirects to `/login?next=/service-desk`.
7. Admin: log in; open Students, Learning Content, quiz editor/import, Service
   Desk review, and Scenario Builder.
8. Save a clearly labelled draft scenario, reload it, verify persistence, then
   delete the draft. Do **not** publish smoke-test content.
9. Confirm a student receives 403/redirect for admin and another student's
   protected data; confirm mentor write attempts remain rejected.
10. Directly refresh `/training`, `/progress`, a lesson, a quiz, `/admin`, and
    `/service-desk`; no route may become an nginx 404.
11. Review browser console/network errors and backend/Service Desk/nginx logs.

## Exact rollback plan

Prefer application rollback when the database is healthy and compatible. Use
the pre-deploy DB/uploads pair only when the migration or data write must be
reversed; do not use a destructive Alembic downgrade.

```bash
docker stop nexus-frontend nexus-service-desk
sudo systemctl stop nexus-admin-academy.service

git switch --detach <PREVIOUS_SHA>
cd backend
.venv/bin/pip install -r requirements.txt
cd ../frontend
npm ci && VITE_API_URL= npm run build
cd ..
```

If database restoration is required, first preserve the failed state, then
restore the matching pair while all writers are stopped:

```bash
cp backend/nexus.db "/tmp/nexus-failed-$(date +%Y%m%d-%H%M%S).db"
mv backend/uploads "/tmp/nexus-failed-uploads-$(date +%Y%m%d-%H%M%S)"
gzip -cd "$HOME/backups/nexus/nexus-<TIMESTAMP>.db.gz" > backend/nexus.db
mkdir -p backend/uploads
tar -xzf "$HOME/backups/nexus/nexus-uploads-<TIMESTAMP>.tar.gz" -C backend/uploads
chown -R nexus:nexus backend/nexus.db backend/uploads
chmod 0640 backend/nexus.db
chmod 0750 backend/uploads
```

Restore the recorded environment/nginx configuration and previous Service Desk
image. If the renamed pre-deploy container is still present, restore it exactly:

```bash
docker stop nexus-service-desk 2>/dev/null || true
docker rm nexus-service-desk 2>/dev/null || true
docker rename nexus-service-desk-predeploy nexus-service-desk
```

Then start the previous release:

```bash
sudo systemctl start nexus-admin-academy.service
docker start nexus-service-desk nexus-frontend
docker exec nexus-frontend nginx -t
docker exec nexus-frontend nginx -s reload
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:13000/service-desk/api/health
curl --fail https://nexus.builtfromzero.fyi/health
```

Run the smoke test before resuming normal access. Retain failed-state copies
and logs until the incident review is complete.
