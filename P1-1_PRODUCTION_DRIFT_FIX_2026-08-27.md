# P1-1 — Fix Production Working-Directory Drift

**Date:** 2026-08-27 · **Source:** `NEXUS_FULL_PROJECT_REVIEW_2026-08-27.md`, Priority 1 item P1-1
**Serving checkout:** `/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy`
(`WorkingDirectory=<that>/backend` in `nexus-admin-academy.service`, running
`uvicorn app.main:app` from `backend/.venv` on `:8000`)

---

## 1. What was causing the drift

The directory `nexus-admin-academy.service` serves from is a normal developer
checkout. Its `backend/nexus.db`, `backend/.env`, `backend/uploads/`, and
`backend/.venv/` are live production state. Two independent things were writing
to it:

### 1a. The nightly workspace snapshot — `/opt/apps/nightly-snapshot.sh`

Installed in the `nexus` user crontab:

```
59 23 * * * /opt/apps/nightly-snapshot.sh
```

It loops over every directory in `…/projects/` and, for each, runs:

```sh
git add -A
git commit -m "Nightly snapshot <date>" --quiet || true
git push origin HEAD:snapshot --force --quiet
```

Run inside the live serving checkout, this **commits whatever is checked out
there** onto whatever ref is current. Evidence in history:

| Commit | Date | What it actually captured |
|---|---|---|
| `862b9eb` | 2026-08-26 | one `tasks/loop-log.md` change, committed on top of the `feature/sentry-student-bug-reporting` branch that was checked out in the serving dir that evening |
| `6aa2ae1` | 2026-08-03 | the **entire 223-file / ~40k-line service-desk-app consolidation**, absorbed into a single anonymous "Nightly snapshot" commit |
| 16 total | 2026-07-09 → 2026-08-26 | `git log --all --grep="Nightly snapshot"` |

The `backup_sqlite.sh` cron job (`30 23 * * *`) is unrelated and clean — it is a
Python online SQLite backup to `~/backups/nexus/`, never touches git.

### 1b. In-place branch checkouts and deploys

`git reflog` in the serving checkout shows real feature work and deploy hops
happening *in the serving directory* instead of a worktree:

```
2026-08-26 19:51  checkout main -> feature/sentry-student-bug-reporting
2026-08-26 20:24  commit  bb1a2a0  feat: add privacy-safe student issue reporting
2026-08-26 20:52  commit  f40a591  fix: stabilize Sentry feedback context
2026-08-26 23:59  commit  862b9eb  Nightly snapshot 2026-08-26   (cron, on that branch)
2026-08-27 08:00  checkout feature/sentry-student-bug-reporting -> 8ea625a
2026-08-27 13:33  checkout 8ea625a -> 6227745
2026-08-27 13:34  checkout 6227745 -> 8ea625a
2026-08-27 18:28  checkout 8ea625a -> 44b7723      <- the "advanced mid-review" hop the review saw
```

`docs/DEPLOYMENT.md` already stated the invariant ("never checkout a dev/review
branch in the production WorkingDirectory") — but nothing enforced it and there
was **no sanctioned deploy path** to use instead, so deploys were done as bare
`git checkout` by hand/agent.

### 1c. Not the cause (checked and ruled out)

- **CI/CD:** `.github/workflows/ci.yml` has no ssh/rsync/scp/deploy step; it is
  push-scoped to `main` for CI only. No other workflow files.
- **systemd timers:** `systemctl list-timers` — only OS housekeeping
  (sysstat, fwupd, apt, logrotate, …). None touch the repo.
- **git hooks:** none active (`core.hooksPath` unset, `.git/hooks/` all samples).
- **root cron:** not readable without an interactive sudo prompt; the drift is
  fully explained by the `nexus`-user cron + manual checkouts above.

### 1d. Related, flagged, NOT changed here

- **`nexus-staging-*` compose stack** (backend `:18000`, frontend `:18081`,
  postgres, service-desk-web — all up 3–4 weeks): the staging backend runs
  `uvicorn app.main:app` **from a Docker image**, not a host bind-mount, so it
  has no git-drift problem. Disk cleanup of that stack + ~14 stale
  `nexus-service-desk:*` images (~18 GB) is **P2-1**, deliberately out of scope.
- **systemd unit bug:** the unit's
  `Environment=PATH=/opt/apps/IT TRAINING PROJECT CODE/…` line is unquoted;
  systemd rejects it (`Invalid environment assignment, ignoring: TRAINING /
  PROJECT / CODE/…` in the journal). The service works only because `ExecStart`
  uses an absolute `uvicorn` path. Should be quoted or moved to an
  `EnvironmentFile`. Not fixed here — it is a production env-var change and
  outside this task.

---

## 2. What was changed

Moving `WorkingDirectory` to a fresh path was rejected: it would mean relocating
the live `nexus.db` / `.env` / `uploads/` / `.venv/`, which this task forbids.
Instead the existing serving checkout is made to *behave* as a dedicated
deploy-only checkout.

### 2a. `/opt/apps/nightly-snapshot.sh` (host file, not in the repo)

Added a `PROTECTED_DIRS` list containing the serving checkout. For a protected
repo the snapshot now **never** runs `git add`/`commit`/`push`. It:

- logs `HEAD` ("recorded, no snapshot taken"), and
- if the working tree is unexpectedly dirty, archives the drift
  (`git ls-files -m -o --exclude-standard` → `tar`) to
  `~/backups/nexus/drift/drift-<repo>-<stamp>.tgz` and writes a `tree DIRTY …
  (NOT committed)` warning to `/opt/apps/nightly-snapshot.log`.

All other projects keep the exact previous behaviour. Original saved to
the session scratchpad before editing. `bash -n` clean; `is_protected`
match logic unit-tested (trailing-slash and sibling-dir cases).

### 2b. `scripts/deploy.sh` (new, in the repo)

The only supported way to change what the service serves. It:

1. refuses to run unless `$PWD` is the checkout the service actually serves
   (`systemctl show -p WorkingDirectory`), and refuses a dirty tree;
2. `git fetch --prune origin`, resolves `<ref>` (default `origin/main`) to a
   concrete SHA, `git checkout --detach` it;
3. runs `scripts/predeploy_check.sh` (existing read-only gate);
4. `pip install -r backend/requirements.txt` + `alembic upgrade head`
   (`--skip-deps` / `--skip-migrations` for a reviewed code-only change);
5. `sudo systemctl restart nexus-admin-academy.service`, verifies
   `:8000/health`; on any failure checks the previous SHA back out, restarts,
   exits non-zero;
6. `--frontend` also rebuilds the Vite bundle and reloads the `nexus-frontend`
   nginx container;
7. appends one line per run to `~/deploy-logs/nexus-deploy.log`.

`--dry-run` previews resolved SHAs and changes nothing.

### 2c. `docs/DEPLOYMENT.md`

New subsection **"Deploying a change (the only supported procedure)"** under
*Active self-hosted deployment*: documents `scripts/deploy.sh`, states that the
nightly snapshot no longer writes to this checkout, that all feature/hotfix
work happens in a worktree, and that rollback is just
`scripts/deploy.sh <previous-good-sha>`.

### 2d. Pre-existing drift cleared

The serving checkout was already dirty at task start:

- `tasks/loop-log.md` — 4 completion entries from the Aug-27 Sentry
  deploy/rollback/redeploy tasks, appended there and never committed;
- `NEXUS_FULL_PROJECT_REVIEW_2026-08-27.md` — the review doc, untracked.

Both were committed to `origin/main` (`7b3eed2`) so the serving checkout
returns to a clean, origin-matching tree.

---

## 3. New deploy procedure (also in `docs/DEPLOYMENT.md`)

```bash
# 1. Do the work in a worktree, never in the serving checkout
git -C "<serving-checkout>" worktree add ~/worktrees/my-fix -b my-fix origin/main
#    …edit, commit, push, review, merge to main…

# 2. Deploy from the serving checkout — one command
cd "<serving-checkout>"
scripts/deploy.sh                       # deploy origin/main (deps + migrations)
scripts/deploy.sh --skip-deps --skip-migrations <sha>   # reviewed code-only change
scripts/deploy.sh --frontend origin/main               # backend + frontend
scripts/deploy.sh --dry-run                            # preview only

# 3. Rollback is just another deploy
scripts/deploy.sh <previous-good-sha>
```

The serving checkout stays in **detached HEAD at the deployed commit**. It
should always be clean and always equal to a real commit on `origin/main`
(or an explicitly pinned rollback SHA). Anything else is drift — check
`~/backups/nexus/drift/` and `/opt/apps/nightly-snapshot.log`.

---

## 4. Verification

- `bash -n` clean on both scripts; `deploy.sh --help` / `--dry-run` work;
  `deploy.sh` correctly aborts from a non-serving dir and on a dirty tree.
- Pre-existing drift committed to `origin/main` (`7b3eed2`); serving checkout
  re-detached at `origin/main`, `git status` clean.
- **One full deploy cycle demonstrated** with `scripts/deploy.sh` — see
  §5 below and `~/deploy-logs/nexus-deploy.log`.
- Serving checkout observed to stay clean and on `origin/main` after the
  cycle.

---

## 5. Demonstrated deploy cycle

Run 2026-08-27 ~20:21–20:23 UTC from the serving checkout, code-only
(`--skip-deps --skip-migrations`, no `--frontend`). A fresh SQLite + uploads
backup was taken first: `~/backups/nexus/nexus-20260827-p1-1-demo.db.gz`.

Baseline: `MainPID 3007149`, up since 2026-08-26 18:59:26; `HEAD 7b3eed2`
(== `origin/main`); `alembic current 0061_integrated_support_prove (head)`;
`:8000/health` OK.

| Step | Command | Result |
|---|---|---|
| bootstrap | `git checkout --detach cbee2c5` (one-time — introduces `scripts/deploy.sh`; that commit differs from `origin/main` only in `scripts/deploy.sh`, `docs/DEPLOYMENT.md`, this report — **no runtime change**, no restart) | clean tree at `cbee2c5` |
| guard check | `scripts/deploy.sh` from a dirty tree / non-serving dir (earlier) | aborted with `This directory is deploy-only.` / `is not the serving checkout` |
| deploy | `scripts/deploy.sh --skip-deps --skip-migrations --force-predeploy origin/fix/p1-1-deploy-drift` | predeploy gate ran (1 pre-existing FAIL — see below — overridden and logged); `systemctl restart`; `MainPID 3557937`, start 20:22:58; `:8000/health` OK; deploy-log line written |
| roll back to `origin/main` | `scripts/deploy.sh --skip-deps --skip-migrations --force-predeploy 7b3eed2` | real `git checkout --detach cbee2c5 → 7b3eed2`; `systemctl restart`; `MainPID 3558276`, start 20:23:10; `:8000/health` **and** `https://nexus.builtfromzero.fyi/health` OK |

Final state (verified):

- serving checkout `HEAD` = `7b3eed2` = `origin/main`, `git status` clean;
- backend healthy, `alembic current` still `0061_integrated_support_prove`
  (never touched); Service Desk container healthy throughout;
- every run appended to `~/deploy-logs/nexus-deploy.log`;
- simulating tonight's nightly snapshot against the (now protected) serving
  checkout logs `PROTECTED, clean at 7b3eed2 — recorded, no snapshot taken`
  and leaves the tree untouched.

### Notes / follow-ups surfaced by the demo

- **`predeploy_check.sh` has one pre-existing FAIL in this environment:**
  `Service Desk production build is missing` — it looks for a host
  `service-desk-app/apps/web/.next/BUILD_ID`, but the live Service Desk runs
  from a Docker **image** (`nexus-service-desk:331efc899e72`), so that host
  artifact is stale/absent. Historically operators rebuilt `.next` on the host
  before each deploy to satisfy it (see `tasks/loop-log.md`). This is
  unrelated to the drift fix; `deploy.sh` exposes it via the hard gate and the
  `--force-predeploy` override (each FAIL logged). Worth deciding separately
  whether that check should instead validate the running container/image.
- **Bootstrap caveat:** `scripts/deploy.sh` only exists on this branch, so the
  very first move onto it needed one manual `git checkout --detach`. Once this
  PR merges to `main`, the script is permanently present and every subsequent
  deploy **and rollback** is `scripts/deploy.sh <ref>` with no manual checkout.
- The one-time bootstrap and the two demo restarts were the only production
  mutations; no database, migration, env, container, or frontend change was
  made.

---

## 6. Review round 2 — deploy.sh failure-handling hardening

A Codex review of PR #29 raised three issues in `scripts/deploy.sh`. All three
are now fixed properly (not suppressed).

### R1 (P1) — rollback only happened on a failed health check

**Was:** `set -e` made any failure after the checkout (`pip`, `alembic`,
`systemctl restart`, frontend steps) exit the script immediately, leaving the
serving checkout on the new SHA with the old process still running.

**Now:** an `EXIT` trap (`on_exit` -> `do_rollback`) is armed the moment the
checkout moves. Every stage runs as `cmd || fail "..."`; `fail` logs and exits,
and the trap restores state. `do_rollback` is *staged* from tracked flags:

| flag | set when | rollback action |
|---|---|---|
| `CHECKOUT_MOVED` | after `git checkout --detach NEW` | `git checkout --detach OLD` |
| `MIGRATION_ATTEMPTED` | immediately before `alembic upgrade` | stop service, restore pre-migration DB backup, remove stale `-wal`/`-shm` |
| `SERVICE_RESTARTED` | immediately before `systemctl restart` | restart on OLD, re-health-check, log `MANUAL INTERVENTION NEEDED` if still down |
| `FRONTEND_APPLIED` | before the first `docker cp` of new assets | restore the container html+`default.conf` snapshot, `nginx -s reload` |

The whole script is wrapped in a `{ … }` load guard so a mid-run `git checkout`
that swaps in a different `deploy.sh` version cannot corrupt the running shell.

### R2 (P1) — migration rollback was not actually safe

**Was:** the docs implied "redeploy any previous good SHA". If the failed
release had advanced Alembic, checking out older code leaves the newer schema
live, and `predeploy_check.sh` then rejects the DB as "not an ancestor of
head", so the documented rollback command aborts.

**Now, two mechanisms:**

1. **Same-run auto-rollback is DB-safe.** Before `alembic upgrade head`,
   `deploy.sh` calls `scripts/backup_sqlite.sh` (SQLite online-backup API, the
   mechanism the reviewer pointed at) with a `predeploy-<sha>-<ts>` stamp and
   records the path. If any later stage fails, `do_rollback` stops the service,
   restores that backup over `backend/nexus.db`, checks out the old code, and
   restarts. `alembic upgrade` is only started *after* the backup succeeds.
2. **Later manual rollback across a migration is detected and refused.** After
   checkout, `deploy.sh` compares the live DB revision to the target tree
   (`alembic history -r <db_rev>:<target_head>`). If the DB is ahead of / absent
   from the target, it aborts with an actionable message unless
   `--allow-db-ahead` is given — which the operator only passes after restoring
   a matching DB backup. `docs/DEPLOYMENT.md` now documents this instead of
   promising arbitrary old-SHA rollback, and recommends forward-fixing over a
   schema downgrade.

### R3 (P2) — `--force-predeploy` didn't log the FAIL lines

**Was:** `predeploy_check.sh` output went to the terminal; the deploy log only
got a generic `predeploy_check FAILED`.

**Now:** `./scripts/predeploy_check.sh 2>&1 | tee -a "$LOG"` with the real exit
code taken from `PIPESTATUS[0]`. Every `PASS:`/`FAIL:` line lands in
`~/deploy-logs/nexus-deploy.log`, followed by either
`predeploy_check passed` or `… FAILED (rc=N) — continuing on operator override`.

### Tests

`scripts/tests/deploy_failure_sim.sh` runs the **real** `deploy.sh` against a
throwaway git checkout with fake `systemctl`/`curl`/`npm`/`docker` on `PATH`
and stubbed `predeploy_check.sh` / `backup_sqlite.sh` / venv `python`+`pip`. No
root, no network, no services. 14 cases / 63 assertions:

| case | asserts |
|---|---|
| S0 happy path | code-only deploy reaches `deploy OK`, no rollback |
| S1 dependency-install failure | checkout rolled back, service never restarted |
| S2 migration failure | pre-migration backup taken, DB restored to pre-migration bytes |
| S2b backup failure | aborts before `alembic`, schema untouched |
| S3 systemctl restart failure | rollback stops + starts the service on OLD |
| S4a new release unhealthy | rollback restarts OLD and recovers |
| S4b health broken even after rollback | logs `MANUAL INTERVENTION NEEDED` |
| S5 frontend build failure | backend (already restarted) rolled back too |
| S5b frontend reload failure | frontend snapshot + backend rollback attempted |
| S6 `--force-predeploy` | deploy proceeds; every `FAIL:` line is in the deploy log |
| S6b predeploy fail, no override | aborts, FAIL line still logged |
| S7a schema-ahead DB | refused with `--allow-db-ahead` guidance, no backup/migration |
| S7b `--allow-db-ahead` | proceeds past the guard |
| S7c migration applied then health fails | DB restored from the pre-migration backup |

Wired into CI as the **Deploy script failure simulations** job
(`.github/workflows/ci.yml`): `bash -n` both scripts + run the harness.

### Drift protections preserved

No change to `PROTECTED_DIRS` in `/opt/apps/nightly-snapshot.sh`, the
serving-dir / clean-tree guards, the worktree-only workflow, or the deploy log.

---

## 7. Review round 3 — deeper deploy.sh correctness (Codex re-review of §6)

Codex re-reviewed the §6 hardening and raised four more. All fixed.

### R5 (P1) — pre-migration backup was taken while the service could still write

The snapshot was taken with the old service live; writes committed after it
(through migrate/deps/restart/frontend) would be silently discarded if
`restore_database` ran. **Fix:** a migration deploy now **stops the service
before the backup and keeps it down** through `alembic upgrade head`, then
`start`s it on the new code. No write can land after the snapshot. Documented
as a maintenance window for schema releases. Code-only deploys are unchanged
(just the restart blip).

### R6 (P1) — `pip install` mutated the shared virtualenv with no rollback

A dep up/downgrade for a release that later failed stayed applied, so the
restored old code could run against the wrong packages. **Fix:** before
`pip install`, `deploy.sh` takes a **hardlink snapshot of `backend/.venv`**
into `~/backups/nexus/venv-rollback-<sha>-<ts>`; `do_rollback` restores it
(staged copy + atomic rename). Near-instant and space-cheap (same-fs
hardlinks); deleted on success.

### R7 (P2) — schema guard was skipped under `--skip-migrations`

`deploy.sh --skip-migrations --force-predeploy <old-sha>` could put old code on
a newer schema (the predeploy ancestry failure was overridden along with the
standing Service Desk one). **Fix:** the schema-ahead guard now runs
**regardless of `--skip-migrations`**; only the actual `alembic upgrade` is
gated by that flag. `--allow-db-ahead` remains the separate, explicit override.

### R8 (P2) — target-tree Alembic ran before target deps were installed

`env.py` imports every model and migrations import services, so `alembic
current/heads/upgrade` (and `predeploy_check.sh`, which also calls Alembic)
could fail under the old venv for a release that adds a dependency. **Fix:**
dependency install is now **step 3** — before `predeploy_check.sh` and any
target-tree Alembic call.

### New deploy order

checkout → **venv snapshot + pip install** → predeploy (tee'd) → **schema-ahead
guard (always)** → *(migration: stop → backup → alembic upgrade)* → (re)start +
health → *(frontend: snapshot → build → swap → reload + health)* → done.
`do_rollback` unwinds, in order: stop service · restore frontend snapshot ·
checkout old SHA · restore venv snapshot · restore DB backup · start + health.

### Tests

`scripts/tests/deploy_failure_sim.sh` grew to **19 cases / 82 assertions**,
adding: venv restored after a post-install failure (S1, S1b); migration
quiesces the service *before* the backup, asserted by log/systemctl ordering
(S2, S2c); deps installed before any Alembic call (S2d); schema-ahead refused
under `--skip-migrations` and under `--skip-migrations --force-predeploy`
(S7d, S7e).

---

## 8. Review round 4 — fail-closed introspection, write-safety window, DB perms

Codex re-reviewed §7 and raised three more P1s. All fixed.

### R9 — schema guard must fail closed on an Alembic introspection error

Real Alembic exits non-zero **without** a revision precisely when the DB is
stamped with a revision the target tree lacks — the exact case the guard
exists for. The previous code turned that into an empty `DB_REV` and skipped
the guard, so `--skip-migrations --force-predeploy <old-sha>` could still land
old code on a newer schema. **Fix:** an introspection failure (or empty
`current`/`heads`) now **aborts** with the schema-ahead guidance unless
`--allow-db-ahead` is passed.

### R10 — keep the database un-rollback-able only until the new backend is proven, and build the frontend first

Two changes:

1. `--frontend` now runs `npm ci` + the Vite build **as step 4**, before
   anything touches the backend or DB. A build failure can no longer trigger a
   database rollback (nothing was changed yet).
2. Once the **new backend passes its health check (step 8), the code + schema
   are committed** (`BACKEND_COMMITTED`). The only thing that can fail after
   that is the frontend container swap, and by then the new backend has begun
   accepting writes — so `do_rollback` restores **only the frontend** and
   leaves the backend on the new commit (fix the frontend forward). It never
   restores a database backup over writes the new backend already took.

### R11 — preserve the live DB's ownership and mode on restore

`restore_database` wrote a fresh temp file (operator uid + umask) and moved it
over `backend/nexus.db`, dropping the production `nexus:nexus 0640`. **Fix:**
it now captures the live file's mode and owner with `stat` and reapplies them
to the restored file before the `mv`, logging a warning if it lacks the
privilege (i.e. run rollback as the service user).

### Deploy order (final)

checkout → **venv snapshot + pip** → **frontend build (if `--frontend`)** →
predeploy (tee'd) → **schema guard (fail-closed, always)** → *(migration: stop
→ backup → alembic upgrade)* → (re)start + health → **[commit point]** →
*(frontend: snapshot → swap → reload + health)* → done.

Rollback before the commit point = full unwind (frontend · checkout · venv ·
DB · service). After it = frontend only.

### Tests

`scripts/tests/deploy_failure_sim.sh` → **25 cases / 109 assertions**, adding:
happy `--frontend` deploy (S0b); build failure never touches backend/DB (S5);
frontend swap failure after a migration keeps code+DB and rolls back only the
frontend (S10a, S10b); DB file mode 0640 reapplied on restore (S11);
introspection failure fails closed / proceeds only with `--allow-db-ahead`
(S9a, S9b).

---

## 9. Review round 5 — no mixed-release window; deploy lock

Codex re-reviewed §8 and raised two more.

### R12 (P1) — isolate the running service from the checkout being replaced

Because the backend runs *from* the checkout and its handlers do lazy imports
(e.g. `routers/labs.py` importing `proxmox_service` on demand), a request
served in the window between `git checkout` and the restart could load
new-release code into the old process — a mixed release, even on the success
path. **Fix within the shared-checkout constraint:** the service is now
**stopped before the checkout for every deploy** and started only after the
new release passes health (step 4 → step 8). Predeploy runs first, while the
old backend is still up, so its live-health checks stay meaningful.

Every deploy is now a short maintenance window. True zero-downtime needs a
separate release directory with an atomic switch (or blue/green) and
relocating `nexus.db` / `.env` / `uploads` / `.venv` out of the checkout —
explicitly out of scope for P1-1 (see §2) and noted as the future path in
`docs/DEPLOYMENT.md`.

### R13 (P2) — serialize concurrent deploys

Two operators could both pass the clean-tree check and race on the checkout /
venv / service / DB. **Fix:** `deploy.sh` now takes a non-blocking host-wide
`flock` on `~/deploy-logs/nexus-deploy.lock` before it reads any state, held
(via an open fd) for the whole run and released on any exit. A second
concurrent invocation aborts with "another deploy is in progress".

### Final deploy order

`flock` → predeploy (old backend up) → **stop backend** → checkout →
venv snapshot + pip (+ `--frontend` build) → schema guard (fail-closed) →
*(migration: backup → alembic upgrade)* → **start backend + health → COMMIT** →
*(frontend swap + reload + health)* → done. Rollback before COMMIT = full
unwind; after = frontend only.

### Tests

`scripts/tests/deploy_failure_sim.sh` → **27 cases / 117 assertions**, adding:
backend stopped before the checkout is touched, and predeploy before the stop
(S12); a second concurrent run refused by the lock (S13); `SIM_SYSTEMCTL_START_FAIL`
rolls fully back and recovers on the old SHA (S3).

---

## 10. Review round 6 — launcher survives historical rollback; strict head count

### R14 (P1) — keep the deploy entry point after a rollback to a pre-`deploy.sh` commit

Rolling the checkout back to a commit older than this script removes
`scripts/deploy.sh`, leaving no supported way to run the next deploy. **Fix:**
every run refreshes a standalone copy at `~/bin/nexus-deploy`
(`NEXUS_DEPLOY_LAUNCHER`) *before* the checkout can move, so the newest working
version always exists outside the mutable tree. `docs/DEPLOYMENT.md` points
operators at it for that case.

### R15 (P2) — reject a divergent migration tree / branched DB instead of taking the first head

`alembic heads | awk '...exit'` kept only the first head; if the target had
divergent heads and the DB sat at that first one, the "already at head" check
skipped a migration that was actually needed (predeploy runs against the old
tree and can't catch it). **Fix:** the guard now counts heads and current
revisions and `fail`s unless there is exactly one of each.

### Tests

`scripts/tests/deploy_failure_sim.sh` → standalone launcher kept + matches
deploy.sh (S14); multiple target heads rejected (S15); branched live DB
rejected (S16).

---

## 11. Review round 7 — the standalone launcher must resolve the real repo

### R16 (P1) — `~/bin/nexus-deploy` derived `REPO_ROOT` from its own path

The R14 launcher copy computed `REPO_ROOT` from `${BASH_SOURCE[0]}/..`. Run as
`~/bin/nexus-deploy` (exactly the rollback-to-a-pre-`deploy.sh`-commit case it
exists for), that resolves to `$HOME`; the script then `cd`s to `$HOME` and the
serving-checkout check aborts — the recovery entry point was unusable. **Fix:**
`REPO_ROOT` is now taken from `nexus-admin-academy.service`'s `WorkingDirectory`
(`systemctl show -p WorkingDirectory`), stripped of the trailing `/backend`;
the script-path fallback is used only when the unit can't be queried at all. An
in-repo copy additionally still refuses unless the tree it was launched from
*is* that serving checkout (worktree-by-mistake protection preserved). The
identity check now runs **before** `cd "$REPO_ROOT"`, so a mismatch produces
the actionable message rather than a bare `cd` failure.

### Tests

`scripts/tests/deploy_failure_sim.sh` → the copied launcher, executed from
`$HOME` after a checkout rollback, resolves the serving checkout from the unit
and completes a deploy (S17); an in-repo `scripts/deploy.sh` whose tree is not
what the unit serves is refused with "refusing to deploy" (S18).

---

## 12. Review round 8 — snapshot atomicity; launcher-refresh ordering

### R17 (P1) — a cross-filesystem venv snapshot could nest itself

`cp -al "$VENV" "$VENV_SNAPSHOT" 2>/dev/null || cp -a "$VENV" "$VENV_SNAPSHOT"`:
when `$NEXUS_BACKUP_DIR` is on a different mount than the checkout (e.g. `/home`
vs `/opt`), `cp -al` creates the destination dir and part of the tree before
failing `EXDEV`. The `cp -a` fallback then copies `$VENV` *inside* that
leftover dir (`$VENV_SNAPSHOT/.venv/...`), and rollback later `mv`s that
wrapper onto `backend/.venv`, so `.venv/bin/python` is missing and the old
backend can't restart. **Fix:** a `snapshot_tree()` helper that `rm -rf`s the
destination before *each* attempt (`cp -al`, then `cp -a`), used for both the
step-7 venv snapshot and the `restore_venv` staging copy.

### R18 (P2) — the launcher was refreshed before the serving-checkout check

`install -m 0755 … "$NEXUS_DEPLOY_LAUNCHER"` ran in step 0, before step 1
rejected an accidental run from a dev worktree — so that aborted run still
overwrote `~/bin/nexus-deploy` with unreviewed worktree code, which a later
recovery deploy would then execute against production. **Fix:** the refresh
now runs only *after* the step-1 identity check passes, and is skipped entirely
on `--dry-run`.

### Tests

`scripts/tests/deploy_failure_sim.sh` → **35 cases / 145 assertions**. New:
S19 (fake `cp` that fails `cp -al` with a partial dir like a real `EXDEV`;
rollback still restores a flat, usable virtualenv — no nested wrapper);
S20 (`--dry-run` installs no launcher and changes nothing); S18 extended to
assert a wrong-tree run leaves `~/bin/nexus-deploy` untouched.

---

## 13. Review round 9 — skip-migrations behind head; shared lock; launcher vs. dirty tree

### R19 (P1) — `--skip-migrations` could start new code against a behind schema

Step 9 treated "live DB revision is an ancestor of the target head" as a
harmless forward upgrade. With `--skip-migrations` the upgrade is then skipped
and step 11 starts the new release against a schema that is missing its
migrations. **Fix:** after the compatibility block, if `--skip-migrations` is
set and `DB_REV != TARGET_HEAD` (and not `--allow-db-ahead`), `fail` — you may
only skip migrations when the DB is already exactly at the target head.

### R20 (P2) — the "host-wide" lock was actually per-account

`NEXUS_DEPLOY_LOCK` defaulted to `$LOG_DIR/nexus-deploy.lock` =
`$HOME/deploy-logs/...`, so two operators on different Unix accounts would take
different lock files and could deploy concurrently. **Fix:** default is now
`/run/lock/nexus-admin-academy-deploy.lock` (account-independent), pre-created
world-writable (`umask 000`) so either account can open it for `flock`.

### R21 (P2) — launcher refreshed before the clean-tree check

R18 moved the `~/bin/nexus-deploy` refresh after the step-1 identity check but
still before step 2 (clean tree). An uncommitted edit to `scripts/deploy.sh`
itself would be copied to the recovery launcher before the dirty-tree abort.
**Fix:** the refresh now runs after step 2 as well — serving checkout confirmed
*and* tree clean — still before the checkout can move.

### Tests

`scripts/tests/deploy_failure_sim.sh` → **39 cases / 151 assertions**. New:
S0c (`--skip-migrations` refused when the live DB is behind the target head);
S21 (default lock path is `/run/lock/...`, pre-created world-writable). Existing
`--skip-migrations` happy-path cases now put the sim DB at head first
(`db_head`), matching the new contract.

---

## 14. Review round 10 — stop-failure rollback; runnable documented rollback

### R22 (P1) — `fail` before `SERVICE_STOPPED=1` left the backend down with no recovery

`$NEXUS_SYSTEMCTL stop … || fail …` ran `fail` *before* `SERVICE_STOPPED=1`. A
stop that exits non-zero after already downing the unit (timed-out stop job, or
a kill) therefore hit `on_exit` with both `SERVICE_STOPPED` and `CHECKOUT_MOVED`
still `0` → "nothing to roll back" → production left down on the old release.
**Fix:** set `SERVICE_STOPPED=1` *before* issuing the stop, so a failed stop
still routes through `do_rollback` (which stops idempotently, then starts the
old SHA and health-checks it).

### R23 (P2) — the documented schema rollback wasn't runnable as written

`docs/DEPLOYMENT.md` said: stop the service, restore the DB backup, run
`deploy.sh --allow-db-ahead <old-sha>`. But step 4 runs `predeploy_check.sh`
expecting the backend live, so it aborts on the health check before the
checkout moves. **Fix:** the rollback recipe now specifies
`--allow-db-ahead --force-predeploy`, explains *why* both are needed, and tells
the operator to confirm in the log that the only predeploy `FAIL` lines are the
expected "backend not responding" ones. `deploy.sh`'s `--force-predeploy` help
text notes this stopped-service rollback as an expected use.

### Tests

`scripts/tests/deploy_failure_sim.sh` → **41 cases / 157 assertions**. New:
S22 (a `systemctl stop` that reports failure still arms rollback and the backend
is brought back up on the old SHA — log shows the rollback start + health, never
"nothing to roll back").

---

## 15. Review round 11 — DB binding, historical-rollback safety, checkout verification

### R24 (P1) — Alembic could act on a different database than the backup/restart

`app/config.py` loads `.env` with `override=False`, and `alembic/env.py` honours
`os.getenv("DATABASE_URL")`. An operator whose shell already exported
`DATABASE_URL` would make the schema guard and `alembic upgrade` inspect/migrate
*that* database, while `DB_PATH` (backup, `stat`/`chmod`, rollback) came from the
production `.env` — the guard could green-light a test DB, then the service would
start against an unmigrated production DB. **Fix:** `alembic_backend()` now
exports `DATABASE_URL="sqlite:///$DB_PATH"` for every Alembic call, and `DB_PATH`
is canonicalised once; a set ambient `DATABASE_URL` is logged as ignored.

### R25 (P1) — a failed historical schema rollback could auto-start new code on the downgraded DB

In the documented flow the operator swaps `backend/nexus.db` for an older
snapshot before running `deploy.sh --allow-db-ahead …`. If that run then failed,
automatic rollback checked out `OLD_SHA` (the *newer* release) and started it
against the hand-downgraded database. **Fix:** when `--allow-db-ahead` is set and
no pre-migration backup was taken, `do_rollback` now stops after restoring the
checkout/venv — it logs `MANUAL INTERVENTION NEEDED` and leaves the service down
so the operator restores their own pre-recovery DB backup. `docs/DEPLOYMENT.md`
step 1 now says to keep that backup for exactly this case.

### R26 (P1) — a checkout that half-applied could still be deployed

`git checkout` can advance `HEAD`, print `unable to unlink old '<path>'`, and
still exit 0 when it can't replace a file (parent-dir perms) — old contents then
linger in the "new" release. **Fix:** after the step-6 checkout, `deploy.sh`
re-checks `git status --porcelain` and `fail`s if the worktree is dirty; the
rollback checkout does the same check and warns on a dirty tree.

### Tests

`scripts/tests/deploy_failure_sim.sh` → **44 cases / 173 assertions**. New:
S23 (a bogus ambient `DATABASE_URL` doesn't divert Alembic — the real DB is
migrated, the ambient target is untouched); S24 (a failed `--allow-db-ahead`
recovery does *not* auto-start the old code, logs `MANUAL INTERVENTION`, leaves
the service stopped); S25 (a checkout that leaves the tree dirty is caught at
step 6 and never started). The Alembic stub now honours `DATABASE_URL`; a fake
`git` models the exit-0-but-dirty checkout.

---

## Final state of `scripts/deploy.sh`

26 review findings across 11 Codex rounds, all fixed with tests. The script now:
resolves the serving checkout from the systemd unit (launcher works from
anywhere) and refreshes the out-of-tree launcher only after the serving-checkout
*and* clean-tree checks pass; serializes on a shared `/run/lock` file (not a
per-account path); arms rollback before stopping the backend so even a failed
stop recovers; verifies the worktree actually matches the target after checkout;
pins Alembic to the `.env` database; refuses `--skip-migrations` when a migration
is actually due; will not auto-start old code over an operator-swapped database;
takes atomic (non-nesting) venv snapshots;
takes a host-wide lock; keeps an out-of-tree launcher copy; runs predeploy
while the old backend is up; **stops the backend before touching the checkout**
(no mixed-release window); snapshots + restores the venv; fail-closed schema
guard requiring exactly one head/revision, honoured even with
`--skip-migrations`; stops-quiesces for the migration + pre-migration backup;
starts + health-checks the new release as the commit point (later failures roll
back the frontend only, never the DB); preserves DB owner/mode on restore;
tee's predeploy output to the log; staged rollback covering every stage.

**Accepted limitation:** every deploy is a brief maintenance window (backend
down step 4→8). True zero-downtime needs a separate release directory with an
atomic switch (or blue/green) and moving `nexus.db` / `.env` / `uploads` /
`.venv` out of the checkout — explicitly out of scope for P1-1 (§2), noted in
`docs/DEPLOYMENT.md` as the future path.
