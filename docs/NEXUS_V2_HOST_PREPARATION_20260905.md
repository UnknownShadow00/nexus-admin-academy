# Nexus V2 host preparation operations log

Operational window opened: **2026-09-05 22:41:51 UTC**

Scope: authorized host preparation only. Production migration, V2 content load,
V2 enablement, pilot enrollment, candidate deployment, and merge are excluded.

## Before state

### Disk

```text
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv   57G   53G  1.9G  97% /
Bytes available: 1,947,156,480
/tmp: 2.3G used, 1.5G available (tmpfs)
Docker build cache: 6.69GB
```

### Production database

```text
path=/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/nexus.db
inode=1846526 size=3022848 mode=0644 owner=nexus:nexus
mtime=2026-09-01 12:56:25.985088728 +0000
sha256=d2ac53c3beee0b474d7216d49c0fc4d7f6f854e3d79040296f829e55b2e5e881
revision=0064_v2_ai_grading_infrastructure
integrity=ok foreign_key_violations=0 students=7
quiz_attempts=2 student_lesson_progress=3 xp_ledger=2
training_weeks=35 promotion_gates=30 service_desk_attempts=0
certifications=0 certification_versions=0
V2 pilot schema/columns are not present at revision 0064.
```

### Backend systemd service

```text
unit=/etc/systemd/system/nexus-admin-academy.service
drop-ins=99-service-desk-admin.conf, override.conf, zz-service-desk-admin.conf
state=active/running
PID=3034210
started=Wed 2026-09-02 06:32:04 UTC
Environment=PATH=/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/.venv/bin
ExecStart=.../uvicorn app.main:app --host 0.0.0.0 --port 8000
V2 environment variables in live process: none
```

The PATH assignment is incorrectly unquoted. The Service Desk drop-ins are
unrelated and must be preserved.

### Network and containers

```text
0.0.0.0:80     nexus-frontend (production nginx)
0.0.0.0:8000   nexus-admin-academy systemd backend
127.0.0.1:13000 nexus-service-desk
127.0.0.1:18000 nexus-staging-backend-1
0.0.0.0:18081  nexus-staging-frontend-1
```

Active production images are `nginx:alpine` (`7068961d45b0`) and
`nexus-service-desk:331efc899e72` (`3a86b9cbc5ef`). The production nginx
container reaches the host backend through `backend-host:8000`, mapped to the
Docker host gateway `172.17.0.1`; direct loopback binding would break this
route. The staging stack owns port 18081 and has retained volumes
`nexus-staging_pgdata` (71.05MB) and `nexus-staging_uploads` (0B). Its only
requests during the inspected seven-day window were operator health probes.

### Health and backup

```text
backend /health: HTTP 200
frontend /: HTTP 200
Service Desk /service-desk/api/health: HTTP 200
staging /: HTTP 200
latest normal DB backup: nexus-20260904-233001.db.gz (475899 bytes)
latest uploads backup: nexus-uploads-20260904-233001.tar.gz (140 bytes)
nightly cron: 30 23 * * * scripts/backup_sqlite.sh
grading service/timer: not installed
candidate source contract: 2.0 compatible
current-live Backend contract endpoint: HTTP 404 (stale deployment)
```

### Privilege preflight

The operator account `nexus` has Docker access, but non-interactive sudo is not
available (`sudo: interactive authentication is required`). Root-owned
systemd/firewall changes therefore require an authorized privileged operator
or an existing non-sudo management path.

## Safety backup

Created with `scripts/backup_sqlite.sh` at 2026-09-05 22:44:07 UTC in a new,
dedicated directory so the helper's retention pass could not delete any
existing backup:

```text
/home/nexus/backups/nexus/host-prep-20260905-224500/nexus-20260905-224500.db.gz
size=475899 mode=0644 owner=nexus:nexus
/home/nexus/backups/nexus/host-prep-20260905-224500/nexus-uploads-20260905-224500.tar.gz
size=140 mode=0664 owner=nexus:nexus
```

`gzip -t` and `tar -tzf` passed. A disposable restored database at
`/tmp/nexus-host-prep-restore-pgVMuo/restored.db` reports integrity `ok`, zero
foreign-key violations, revision `0064_v2_ai_grading_infrastructure`, and seven
students. Production SHA-256 was identical before and after the backup.

## Disk cleanup

Protected production and staging container/image IDs were resolved before
cleanup. No volume, container, backup, or application data was deleted.

1. Dangling builder cache older than 24 hours: 45.06kB reported reclaimed.
2. All unused builder cache older than 24 hours: 4.173GB reported reclaimed.
3. Two unrelated, unused Jarvis validation images, each verified to have zero
   container references:
   - `c89cef2eb6fc` (`jarvis-ci-portaudio-validation:working`)
   - `787226de4e01` (`jarvis-validation-main:c9c8f29`)

Filesystem free space changed from 1,947,156,480 bytes (1.9G displayed) to
9,482,473,472 bytes (8.9G displayed, 8.83 GiB). Cleanup stopped immediately
after the 8 GiB target was reached. Backend, frontend, and Service Desk health
passed after every cleanup operation.

## Staging exposure

The `nexus-staging` Compose project owned wildcard port 18081. Inspection found
no non-operator request in the prior seven days. At 2026-09-05 22:45 UTC the
four services were stopped using Compose. All four stopped containers, both
named volumes, and all images remain preserved. Ports 18081 and 18000 no longer
listen. Production health remained green.

Restart, if later authorized and needed:

```bash
docker compose -p nexus-staging --env-file .env.staging \
  -f docker-compose.yml -f docker-compose.staging.yml start
```

## Backend PATH and exposure analysis

The active unit and `/etc/systemd/system` are not writable by `nexus`, and
`systemctl --no-ask-password daemon-reload` returns access denied. No unit,
drop-in, firewall rule, or production service was changed or restarted.

Binding the Backend to `127.0.0.1` is not safe in the current topology:
production nginx and Service Desk both resolve `backend-host` to the Docker
host gateway `172.17.0.1`. A disposable server bound only to `172.17.0.1:18082`
was reachable from both production containers and was not reachable through
the host LAN address. It was then stopped. The smallest verified architecture
is therefore a bridge-only Backend bind to `172.17.0.1`, not loopback and not
the LAN/wildcard address.

The privileged change should be an additive drop-in so the three existing
Service Desk drop-ins remain untouched:

```ini
# /etc/systemd/system/nexus-admin-academy.service.d/10-host-preparation.conf
[Service]
Environment="PATH=/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=
ExecStart="/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/.venv/bin/uvicorn" app.main:app --host 172.17.0.1 --port 8000
```

After a privileged operator creates that file: validate with
`systemd-analyze verify nexus-admin-academy.service`, reload, restart once,
confirm `ss` shows only `172.17.0.1:8000`, and test both containers against
`http://backend-host:8000/health`. Operator probes must use
`NEXUS_BACKEND_URL=http://172.17.0.1:8000` after the change.

## Grading worker

Pre-install validation produced 17 PASS, 5 WARN, 0 FAIL, 0 SKIP. Both shipped
units parse, `systemd-analyze verify` exits zero, paths/imports are valid, the
120-second timer interval is valid, and User/WorkingDirectory match the live
Backend. The warnings are the known invalid Backend PATH and the not-yet-
installed worker/timer state.

Installation could not proceed without interactive sudo. More importantly, an
explicit `AI_ENABLED=false` zero-job invocation against the verified production
database failed before processing because candidate code selects
`pending_grades.claimed_at`, which does not exist until the later 0068 schema.
The database remained byte-identical, with zero pending rows. Installing and
enabling this timer while production must remain at 0064 would create a failing
job every two minutes, so installation was deliberately stopped. Timer
activation must occur after the authorized 0064-to-0068 migration, or after a
separately reviewed backward-compatible no-op guard is developed.

## Functional checks

```text
login SPA: HTTP 200
normal SPA navigation: HTTP 200
student login (Ahmed): HTTP 200; /auth/me HTTP 200
admin login: HTTP 200
unauthenticated Service Desk: HTTP 307 to /login?next=/service-desk
backend, frontend, Service Desk health: HTTP 200
production DB hash before/after authentication checks: unchanged
candidate source contract: compatible semantic contract 2.0
current-live contract: backend endpoint HTTP 404 (expected stale deployment)
```

## Current host verdict

Disk, backup, staging exposure, candidate unit validation, and current V1
functional health are ready. Full host readiness is **not green** because the
privileged PATH/Backend-bind changes were not possible in this session and the
grading timer cannot safely run against schema 0064. Production remains
unchanged at schema 0064 with V2 off.
