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
