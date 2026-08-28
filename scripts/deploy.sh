#!/usr/bin/env bash
# The ONLY supported way to change what nexus-admin-academy.service serves.
#
# This directory is a deploy-only checkout. It must never carry a dev/review
# branch, uncommitted edits, or automated commits (the nightly snapshot skips
# it). All feature work happens in a git worktree elsewhere. See
# docs/DEPLOYMENT.md -> "Deploying a change".
#
# It takes a host-wide flock first (a shared /run/lock path, not a per-account
# one), so concurrent deploys -- even from different Unix accounts -- cannot race.
#
# What it does, in order (every step after "stop" is covered by an automatic
# rollback if a later step fails -- see "Rollback" below):
#   1. Resolves the serving checkout from the systemd unit's WorkingDirectory
#      (so the ~/bin/nexus-deploy copy works from anywhere); an in-repo copy
#      must additionally be running from that same checkout.
#   2. Refuses to run with a dirty working tree.
#   3. git fetch, then resolve the pinned target commit to a SHA.
#   4. Runs scripts/predeploy_check.sh while the OLD backend is still up (its
#      live-health / container / env checks need it running). Full output tee'd
#      to the deploy log; a failing gate aborts unless --force-predeploy.
#   5. STOPS the backend. It runs from this checkout and its handlers do lazy
#      imports, so files must not change under a live process. It stays down
#      until step 11.
#   6. checkout --detach the target SHA.
#   7. Snapshots the virtualenv, then installs target backend deps (unless
#      --skip-deps) -- before any target-tree Alembic call.
#   8. With --frontend: `npm ci` + Vite build (backend already down).
#   9. FAILS CLOSED if it cannot confirm the live schema is compatible with the
#      target (DB revision ahead of / absent from the target tree), unless
#      --allow-db-ahead. Runs even with --skip-migrations.
#  10. If a migration will actually run: fresh SQLite + uploads backup
#      (scripts/backup_sqlite.sh), then `alembic upgrade head`.
#  11. Starts the backend on the new release and verifies /health. Once
#      healthy, the code + schema are COMMITTED (see Rollback).
#  12. With --frontend: snapshots the live container assets/config, swaps in the
#      build from step 8, `nginx -t`, reload, re-checks frontend /health.
#  13. Appends timestamped lines to ~/deploy-logs/nexus-deploy.log for every run.
#
# The backend is DOWN from step 5 until step 11 -- every deploy is a short
# maintenance window (seconds for code-only, longer with deps/migration/build).
# Zero-downtime would need a separate release directory with an atomic switch,
# or blue/green; that is out of scope for this single-process, shared-checkout
# deployment.
#
# Rollback (automatic, on ANY failure once the backend has been stopped):
#   - BEFORE the step-11 health check passes -- full unwind: check the old SHA
#     back out; restore the pre-deploy virtualenv snapshot (if deps installed);
#     restore the pre-migration database backup (if a migration was attempted --
#     SQLite DDL here is non-transactional, so a half-applied migration is
#     possible and the backup is the only safe restore, with the live DB's
#     owner/mode reapplied); start the service on the old SHA and re-health-check.
#   - AFTER step 11 (only the frontend swap can fail now) -- the NEW backend has
#     begun accepting writes, so the database is NOT rolled back. Only the
#     frontend snapshot is restored; the backend stays on NEW and the frontend
#     is fixed forward.
#   Rolling back a PAST deploy that changed the schema is NOT just
#   `deploy.sh <old-sha>`: you must first restore a database backup taken at or
#   before that commit's migration head, then re-run with --allow-db-ahead.
#   deploy.sh detects and refuses the unsafe case (step 9).
#
# Usage:
#   scripts/deploy.sh [options] [<ref>]
#
#   <ref>              Commit/branch/tag to deploy. Default: origin/main.
#                      Always resolved to a concrete SHA before checkout.
#
# Options:
#   --frontend         Also rebuild the Vite app and reload the nginx container.
#   --skip-deps        Skip `pip install -r backend/requirements.txt`.
#   --skip-migrations  Skip `alembic upgrade head` (use only when the reviewed
#                      diff contains no migration). REFUSED if the live DB is
#                      not already at the target's Alembic head.
#   --allow-db-ahead   Proceed even though the live DB schema is ahead of the
#                      target commit. Only after restoring a matching DB backup.
#   --force-predeploy  Continue even if scripts/predeploy_check.sh fails. Its
#                      full output (every FAIL line) is written to the deploy
#                      log. Use only after reviewing each failure. Also the
#                      expected mode for a manual schema rollback where you have
#                      already stopped the backend (its live checks then fail).
#   --dry-run          Print the plan and resolved SHAs, change nothing.
#   -h, --help         Show this header.
#
# Examples:
#   scripts/deploy.sh                               # deploy origin/main
#   scripts/deploy.sh origin/main --frontend        # backend + frontend
#   scripts/deploy.sh --skip-deps --skip-migrations abc1234   # code-only hotfix

set -euo pipefail

# Load guard: the brace group forces bash to parse the ENTIRE script before it
# runs a single command, so a mid-run `git checkout` that swaps in a different
# version of this file cannot make bash resume from a half-read buffer.
{

# --- Overridable knobs (defaults are production; tests override these) -------
: "${NEXUS_SERVICE:=nexus-admin-academy.service}"
: "${NEXUS_HEALTH_URL:=http://127.0.0.1:8000/health}"
: "${NEXUS_FRONTEND_HEALTH_URL:=http://127.0.0.1/health}"
: "${NEXUS_DEPLOY_LOG_DIR:=$HOME/deploy-logs}"
: "${NEXUS_BACKUP_SCRIPT:=}"          # resolved to $REPO_ROOT/scripts/backup_sqlite.sh below
: "${NEXUS_BACKUP_DIR:=$HOME/backups/nexus}"
: "${NEXUS_SQLITE_DB:=}"              # resolved from backend/.env / default below
: "${NEXUS_FRONTEND_CONTAINER:=nexus-frontend}"
: "${NEXUS_HEALTH_RETRIES:=15}"
: "${NEXUS_HEALTH_DELAY:=2}"
: "${NEXUS_SYSTEMCTL:=sudo systemctl}"  # tests set NEXUS_SYSTEMCTL=systemctl with a fake on PATH
: "${NEXUS_DEPLOY_LOCK:=}"              # resolved to $LOG_DIR/nexus-deploy.lock below
: "${NEXUS_DEPLOY_LAUNCHER:=$HOME/bin/nexus-deploy}"  # stable copy, survives rollback to a pre-deploy.sh commit

SERVICE="$NEXUS_SERVICE"

# Resolve the serving checkout from the systemd unit itself -- NOT from this
# script's own path. The standalone launcher copy ($NEXUS_DEPLOY_LAUNCHER) lives
# OUTSIDE any checkout so it survives a rollback to a commit that predates this
# script; deriving REPO_ROOT from its location would point at $HOME and abort the
# WorkingDirectory check below, leaving the promised recovery entry point
# unusable. The unit's WorkingDirectory is the single source of truth. Fall back
# to the script-relative path only when the unit cannot be queried at all (the
# failure-sim harness on a host without this service).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVING_WORKDIR="$($NEXUS_SYSTEMCTL show -p WorkingDirectory --value "$SERVICE" 2>/dev/null || true)"
case "$SERVING_WORKDIR" in
  */backend) REPO_ROOT="${SERVING_WORKDIR%/backend}" ;;
  "")        REPO_ROOT="$SCRIPT_REPO_ROOT" ;;   # unit not queryable; step 1 aborts
  *)         echo "ABORT: $SERVICE WorkingDirectory ('$SERVING_WORKDIR') is not a .../backend path" >&2; exit 1 ;;
esac
LOG_DIR="$NEXUS_DEPLOY_LOG_DIR"
LOG="$LOG_DIR/nexus-deploy.log"
[ -n "$NEXUS_BACKUP_SCRIPT" ] || NEXUS_BACKUP_SCRIPT="$REPO_ROOT/scripts/backup_sqlite.sh"

REF="origin/main"
DO_FRONTEND=0
SKIP_DEPS=0
SKIP_MIGRATIONS=0
ALLOW_DB_AHEAD=0
FORCE_PREDEPLOY=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --frontend)        DO_FRONTEND=1 ;;
    --skip-deps)       SKIP_DEPS=1 ;;
    --skip-migrations) SKIP_MIGRATIONS=1 ;;
    --allow-db-ahead)  ALLOW_DB_AHEAD=1 ;;
    --force-predeploy) FORCE_PREDEPLOY=1 ;;
    --dry-run)         DRY_RUN=1 ;;
    -h|--help)         awk 'NR>1 && /^#/{sub(/^# ?/,"");print;next} NR>1{exit}' "$0"; exit 0 ;;
    -*)                echo "Unknown option: $arg" >&2; exit 2 ;;
    *)                 REF="$arg" ;;
  esac
done

mkdir -p "$LOG_DIR"

log()  { printf '%s  %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
abort() { echo "ABORT: $*" >&2; exit 1; }

# --- 0. Host-wide deploy lock (held for the whole run, released on any exit) --
# Serializes concurrent deploys before any state is read, so two operators
# cannot race on the checkout / venv / service / database. The default path is
# ACCOUNT-INDEPENDENT (/run/lock, not $HOME) so two operators on different Unix
# accounts still contend on the same file; it is pre-created world-writable
# (sticky dir) so either account can open it for flock.
[ -n "$NEXUS_DEPLOY_LOCK" ] || NEXUS_DEPLOY_LOCK="/run/lock/nexus-admin-academy-deploy.lock"
if [ ! -e "$NEXUS_DEPLOY_LOCK" ]; then
  ( umask 000; : > "$NEXUS_DEPLOY_LOCK" ) 2>/dev/null || true
fi
exec 9>"$NEXUS_DEPLOY_LOCK" || abort "cannot open deploy lock $NEXUS_DEPLOY_LOCK (create it world-writable, or set NEXUS_DEPLOY_LOCK to a path you can write)"
if ! flock -n 9; then
  abort "another deploy is in progress (lock: $NEXUS_DEPLOY_LOCK). Wait for it to finish, or clear a stale lock only if no deploy.sh is running."
fi

# Always pin Alembic to the SAME database file that DB_PATH / the rollback
# backup use. app/config.py loads .env with override=False, so a DATABASE_URL
# already exported in the operator's shell would otherwise make Alembic inspect
# and migrate a DIFFERENT database than the one we back up and restart against.
alembic_backend() {
  ( cd "$REPO_ROOT/backend" && DATABASE_URL="sqlite:///$DB_PATH" ./.venv/bin/python -m alembic "$@" )
}

resolve_db_path() {
  [ -n "$NEXUS_SQLITE_DB" ] && { printf '%s\n' "$NEXUS_SQLITE_DB"; return; }
  local url=""
  if [ -f "$REPO_ROOT/backend/.env" ]; then
    url="$(sed -n 's/^[[:space:]]*DATABASE_URL[[:space:]]*=[[:space:]]*//p' "$REPO_ROOT/backend/.env" \
           | head -n1 | tr -d '"'"'"'\r')"
  fi
  case "$url" in
    sqlite:////*) printf '%s\n' "/${url#sqlite:////}" ;;
    sqlite:///*)  printf '%s\n' "$REPO_ROOT/backend/${url#sqlite:///}" ;;
    *)            printf '%s\n' "$REPO_ROOT/backend/nexus.db" ;;
  esac
}

health_ok() {
  local url="$1" i
  for ((i = 1; i <= NEXUS_HEALTH_RETRIES; i++)); do
    if curl --fail --silent --show-error --max-time 10 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$NEXUS_HEALTH_DELAY"
  done
  return 1
}

# Point-in-time copy of a directory tree: same-filesystem hardlink copy when
# possible, otherwise a deep copy. Always starts from a clean destination --
# `cp -al` can create the target dir and some subdirs before failing EXDEV on a
# cross-filesystem $NEXUS_BACKUP_DIR, and a leftover dir would make the `cp -a`
# fallback nest the source INSIDE it ($dest/$(basename src)/...) instead of
# replacing it, which later breaks the rollback that moves $dest into place.
snapshot_tree() {
  local src="$1" dest="$2"
  rm -rf "$dest"
  cp -al "$src" "$dest" 2>/dev/null && return 0
  rm -rf "$dest"
  cp -a "$src" "$dest"
}

# --- 1. Must be THE serving checkout -----------------------------------------
# REPO_ROOT was derived from the unit's WorkingDirectory above. Re-assert the
# unit was actually queryable, and -- when we were launched from a checkout tree
# rather than the out-of-tree launcher -- that that tree IS the serving checkout
# (stops an operator "deploying" a worktree by mistake).
if [ -z "$SERVING_WORKDIR" ]; then
  abort "cannot read WorkingDirectory of $SERVICE (is it installed on this host?)"
fi
if [ "${BASH_SOURCE[0]}" -ef "$NEXUS_DEPLOY_LAUNCHER" ]; then
  echo "info: invoked via the standalone launcher; serving checkout = $REPO_ROOT (from $SERVICE)" >&2
elif [ "$SCRIPT_REPO_ROOT" != "$REPO_ROOT" ]; then
  abort "refusing to deploy: launched from $SCRIPT_REPO_ROOT, but $SERVICE serves $REPO_ROOT/backend.
Run scripts/deploy.sh from the serving checkout (or the $NEXUS_DEPLOY_LAUNCHER copy); use a git worktree for everything else."
fi

# Only now is REPO_ROOT confirmed to be the live serving checkout -- safe to
# enter it and touch git / the venv / the database.
cd "$REPO_ROOT" || abort "serving checkout $REPO_ROOT is not accessible"

# --- 2. Clean tree ----------------------------------------------------------
if [ -n "$(git status --porcelain)" ]; then
  git status --short >&2
  abort "serving checkout has uncommitted changes. This directory is deploy-only."
fi

# Keep a standalone copy of this script OUTSIDE the checkout so a rollback to a
# commit that predates scripts/deploy.sh still leaves a working entry point.
# Only AFTER steps 1-2 have confirmed this is the serving checkout AND its tree
# is clean -- an accidental run from a worktree, or with an uncommitted edit to
# deploy.sh itself, must not overwrite ~/bin/nexus-deploy with unreviewed code.
# Skipped on --dry-run. Still well before the checkout can move (step 6).
if [ "$DRY_RUN" != "1" ] && ! [ "${BASH_SOURCE[0]}" -ef "$NEXUS_DEPLOY_LAUNCHER" ]; then
  mkdir -p "$(dirname "$NEXUS_DEPLOY_LAUNCHER")" 2>/dev/null \
    && install -m 0755 "${BASH_SOURCE[0]}" "$NEXUS_DEPLOY_LAUNCHER" 2>/dev/null \
    || echo "warning: could not refresh standalone launcher at $NEXUS_DEPLOY_LAUNCHER" >&2
fi

OLD_SHA="$(git rev-parse HEAD)"
DB_PATH="$(resolve_db_path)"
# Canonicalise so the backup, stat/chmod, rollback and the Alembic URL all name
# the exact same file (the .env value can be relative, e.g. sqlite:///./nexus.db).
if [ -d "$(dirname "$DB_PATH")" ]; then
  DB_PATH="$(cd "$(dirname "$DB_PATH")" && pwd)/$(basename "$DB_PATH")"
fi

# --- 3. Resolve target ----------------------------------------------------------
git fetch --prune origin
NEW_SHA="$(git rev-parse --verify "${REF}^{commit}")"

PLAN="operator=$(whoami) service=$SERVICE ref=$REF old=${OLD_SHA:0:12} new=${NEW_SHA:0:12} frontend=$DO_FRONTEND skip_deps=$SKIP_DEPS skip_migrations=$SKIP_MIGRATIONS allow_db_ahead=$ALLOW_DB_AHEAD force_predeploy=$FORCE_PREDEPLOY"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY RUN — $PLAN"
  if [ "$OLD_SHA" = "$NEW_SHA" ]; then echo "would stay on ${NEW_SHA:0:12}"; else echo "would checkout ${NEW_SHA:0:12}"; fi
  exit 0
fi

log "deploy start: $PLAN"
if [ -n "${DATABASE_URL:-}" ]; then
  log "note: DATABASE_URL is set in the environment; Alembic is pinned to the .env database ($DB_PATH) regardless"
fi

# --- Rollback machinery ------------------------------------------------------
VENV="$REPO_ROOT/backend/.venv"
CHECKOUT_MOVED=0        # tree may be on NEW_SHA
DEPS_INSTALLED=0        # pip install ran against the shared virtualenv
MIGRATION_ATTEMPTED=0   # alembic upgrade was started (DDL here is non-transactional)
SERVICE_STOPPED=0       # service was stopped for the migration window
SERVICE_RESTARTED=0     # service was (re)started on NEW_SHA
BACKEND_COMMITTED=0     # NEW backend passed health -> code+schema are the point of no return
FRONTEND_APPLIED=0      # new assets/config copied into the frontend container
DB_BACKUP_BEFORE=""     # pre-migration backup, set when MIGRATION_ATTEMPTED
VENV_SNAPSHOT=""        # hardlink copy of the pre-deploy virtualenv
FRONTEND_SNAPSHOT=""    # dir holding the previous container html + default.conf
IN_ROLLBACK=0
DEPLOY_OK=0

restore_venv() {
  [ -n "$VENV_SNAPSHOT" ] && [ -d "$VENV_SNAPSHOT" ] || {
    log "ROLLBACK WARNING: no virtualenv snapshot; dependencies NOT restored — MANUAL INTERVENTION NEEDED"
    return 1
  }
  log "ROLLBACK: restoring virtualenv from $VENV_SNAPSHOT"
  local staged="${VENV_SNAPSHOT}.staged.$$"
  if snapshot_tree "$VENV_SNAPSHOT" "$staged" && rm -rf "$VENV" && mv "$staged" "$VENV"; then
    log "ROLLBACK: virtualenv restored"
    # Restoration is verified good -> drop the snapshot so repeated transient
    # failures don't pile whole virtualenv trees up under $NEXUS_BACKUP_DIR.
    # (Kept on the failure path below for manual recovery.)
    rm -rf "$VENV_SNAPSHOT" 2>/dev/null || true
    VENV_SNAPSHOT=""
  else
    rm -rf "$staged"
    log "ROLLBACK WARNING: virtualenv restore failed — snapshot kept at $VENV_SNAPSHOT — MANUAL INTERVENTION NEEDED"
    return 1
  fi
}

restore_database() {
  # Assumes the service is already stopped.
  [ -n "$DB_BACKUP_BEFORE" ] && [ -f "$DB_BACKUP_BEFORE" ] || {
    log "ROLLBACK WARNING: no pre-migration backup available; database NOT restored — MANUAL INTERVENTION NEEDED"
    return 1
  }
  log "ROLLBACK: restoring database from $DB_BACKUP_BEFORE"
  # Preserve the live DB's ownership and mode (production is nexus:nexus 0640);
  # a fresh temp file would otherwise take the operator's uid and umask.
  local ref_mode ref_owner
  ref_mode="$(stat -c '%a' "$DB_PATH" 2>/dev/null || echo 640)"
  ref_owner="$(stat -c '%U:%G' "$DB_PATH" 2>/dev/null || echo nexus:nexus)"
  local tmp="$DB_PATH.rollback.$$"
  if ! gunzip -c "$DB_BACKUP_BEFORE" > "$tmp"; then
    rm -f "$tmp"
    log "ROLLBACK WARNING: could not decompress $DB_BACKUP_BEFORE — MANUAL INTERVENTION NEEDED"
    return 1
  fi
  # Wrong owner/mode here means the service account cannot open its own database.
  # /health does not touch the DB, so a mis-permissioned rollback would still
  # report "healthy" -- treat a perms failure as a failed restore.
  local perms_ok=1
  chmod "$ref_mode" "$tmp" 2>/dev/null || { log "ROLLBACK WARNING: could not set mode $ref_mode on restored DB"; perms_ok=0; }
  chown "$ref_owner" "$tmp" 2>/dev/null || { log "ROLLBACK WARNING: could not set owner $ref_owner on restored DB (run rollback as root or the service user)"; perms_ok=0; }
  if ! mv -f "$tmp" "$DB_PATH"; then
    rm -f "$tmp"
    log "ROLLBACK WARNING: could not move the restored database into place — MANUAL INTERVENTION NEEDED"
    return 1
  fi
  rm -f "$DB_PATH-wal" "$DB_PATH-shm"
  if [ "$perms_ok" != "1" ]; then
    log "ROLLBACK WARNING: restored database is in place but its owner/mode could not be set to $ref_owner/$ref_mode — the service may not be able to open it. MANUAL INTERVENTION NEEDED."
    return 1
  fi
  log "ROLLBACK: database file restored (mode $ref_mode, owner $ref_owner)"
}

restore_frontend() {
  [ -n "$FRONTEND_SNAPSHOT" ] && [ -d "$FRONTEND_SNAPSHOT" ] || return 0
  log "ROLLBACK: restoring previous frontend assets/config"
  local fe_ok=1
  docker cp "$FRONTEND_SNAPSHOT/html/." "$NEXUS_FRONTEND_CONTAINER:/usr/share/nginx/html/" || {
    log "ROLLBACK WARNING: frontend asset restore failed"; fe_ok=0; }
  docker cp "$FRONTEND_SNAPSHOT/default.conf" "$NEXUS_FRONTEND_CONTAINER:/etc/nginx/conf.d/default.conf" || {
    log "ROLLBACK WARNING: frontend config restore failed"; fe_ok=0; }
  docker exec "$NEXUS_FRONTEND_CONTAINER" nginx -s reload || {
    log "ROLLBACK WARNING: nginx reload after frontend restore failed"; fe_ok=0; }
  if [ "$fe_ok" != "1" ]; then
    log "ROLLBACK WARNING: frontend restore FAILED — the nginx container may be serving mixed old/new assets or config. Snapshot kept at $FRONTEND_SNAPSHOT. MANUAL INTERVENTION NEEDED."
    return 1
  fi
  return 0
}

do_rollback() {
  [ "$IN_ROLLBACK" = "1" ] && return
  IN_ROLLBACK=1
  set +e

  # Point of no return: once the NEW backend passed its health check, the
  # code + schema are committed. A later failure (only the frontend can fail
  # after this) must NOT roll the database back over writes the NEW backend
  # has since accepted -- roll back just the frontend and stay on NEW.
  if [ "$BACKEND_COMMITTED" = "1" ]; then
    log "ROLLBACK: backend + database already committed and healthy on ${NEW_SHA:0:12}; rolling back the frontend only"
    local fe_restore_rc=0
    [ "$FRONTEND_APPLIED" = "1" ] && { restore_frontend || fe_restore_rc=1; }
    if [ "$fe_restore_rc" = "1" ]; then
      log "ROLLBACK: frontend restore FAILED — backend stays on ${NEW_SHA:0:12}, but the frontend is in an indeterminate state. Redeploy it by hand from $FRONTEND_SNAPSHOT. MANUAL INTERVENTION NEEDED."
      # keep FRONTEND_SNAPSHOT for that manual recovery
    else
      log "ROLLBACK: frontend restored — backend stays on ${NEW_SHA:0:12}; redeploy the frontend once fixed"
      [ -n "$FRONTEND_SNAPSHOT" ] && { rm -rf "$FRONTEND_SNAPSHOT" 2>/dev/null || true; FRONTEND_SNAPSHOT=""; }
    fi
    # The backend is committed on ${NEW_SHA:0:12}, so the pre-deploy virtualenv
    # snapshot is no longer a rollback target on this path -- drop it.
    [ -n "$VENV_SNAPSHOT" ] && { rm -rf "$VENV_SNAPSHOT" 2>/dev/null || true; VENV_SNAPSHOT=""; }
    log "ROLLBACK: complete (frontend-only)"
    return
  fi

  log "ROLLBACK: starting (target ${OLD_SHA:0:12})"

  # Cycle the service if anything it reads at runtime (code, venv, schema) was
  # touched, so it comes back up consistent with the restored old release.
  local cycle_service=0
  { [ "$MIGRATION_ATTEMPTED" = "1" ] || [ "$SERVICE_RESTARTED" = "1" ] \
    || [ "$SERVICE_STOPPED" = "1" ] || [ "$DEPS_INSTALLED" = "1" ]; } && cycle_service=1

  # Everything below replaces files the backend reads at runtime (code, venv,
  # the SQLite file). If we cannot confirm the unit is actually stopped, doing
  # that under a live process risks a mixed release or corrupt writes -- abort
  # and leave it for a human.
  if [ "$cycle_service" = "1" ]; then
    log "ROLLBACK: stopping $SERVICE"
    $NEXUS_SYSTEMCTL stop "$SERVICE"
    # Require a POSITIVE terminal-inactive state. A timed-out stop can leave the
    # unit "deactivating" (process still winding down) -- anything that is not
    # clearly inactive/failed means we must NOT rewrite files under it.
    local rb_state; rb_state="$($NEXUS_SYSTEMCTL is-active "$SERVICE" 2>/dev/null || true)"
    case "$rb_state" in
      inactive|failed) : ;;
      *)
        log "ROLLBACK ABORTED: $SERVICE is '$rb_state' after stop (not inactive/failed) — NOT restoring the checkout / venv / database under a live process. MANUAL INTERVENTION NEEDED."
        log "ROLLBACK: complete (aborted — service not confirmed stopped)"
        return ;;
    esac
  fi

  # Any restore step that cannot complete leaves runtime state (code / venv /
  # schema / frontend) in an indeterminate mix. Track that: if ANY of them
  # failed we do NOT restart -- a service brought up on half-restored state is
  # worse than one that is cleanly down with a MANUAL INTERVENTION line.
  local rollback_incomplete=0

  [ "$FRONTEND_APPLIED" = "1" ] && { restore_frontend || rollback_incomplete=1; }

  if [ "$CHECKOUT_MOVED" = "1" ]; then
    log "ROLLBACK: checkout -> ${OLD_SHA:0:12}"
    if ! git checkout --detach "$OLD_SHA" --quiet; then
      log "ROLLBACK WARNING: git checkout of ${OLD_SHA:0:12} failed — MANUAL INTERVENTION NEEDED"
      rollback_incomplete=1
    elif [ -n "$(git status --porcelain)" ]; then
      log "ROLLBACK WARNING: worktree still dirty after checking out ${OLD_SHA:0:12} — some files were not restored — MANUAL INTERVENTION NEEDED"
      rollback_incomplete=1
    fi
  fi

  [ "$DEPS_INSTALLED" = "1" ] && { restore_venv || rollback_incomplete=1; }

  if [ "$MIGRATION_ATTEMPTED" = "1" ]; then
    restore_database || rollback_incomplete=1
  fi

  # --allow-db-ahead means the operator took charge of the database out of band
  # (the documented historical-schema rollback). deploy.sh cannot know the
  # correct pre-recovery state -- and if it then ran a migration, restore_database
  # only puts back the operator's already-downgraded snapshot. Either way,
  # auto-starting OLD_SHA (which is the *newer* release) could run new code
  # against an old schema. Never auto-start under --allow-db-ahead.
  if [ "$ALLOW_DB_AHEAD" = "1" ]; then
    log "ROLLBACK: --allow-db-ahead was set — the database state is operator-managed and cannot be auto-verified."
    log "ROLLBACK: NOT auto-starting ${OLD_SHA:0:12}. Restore your own pre-recovery database backup, then start $SERVICE by hand. MANUAL INTERVENTION NEEDED."
    log "ROLLBACK: complete (service left stopped)"
    return
  fi

  # One or more restore steps failed -> the checkout / venv / database on disk
  # is not a coherent old release. Do not start anything against it.
  if [ "$rollback_incomplete" = "1" ]; then
    log "ROLLBACK: one or more restore steps FAILED — NOT starting $SERVICE against half-restored state. Fix the flagged item(s) by hand, then start $SERVICE. MANUAL INTERVENTION NEEDED."
    log "ROLLBACK: complete (service left stopped)"
    return
  fi

  if [ "$cycle_service" = "1" ]; then
    log "ROLLBACK: starting $SERVICE on ${OLD_SHA:0:12}"
    $NEXUS_SYSTEMCTL start "$SERVICE"
    if health_ok "$NEXUS_HEALTH_URL"; then
      log "ROLLBACK: backend healthy on ${OLD_SHA:0:12}"
    else
      log "ROLLBACK WARNING: backend NOT healthy after rollback — MANUAL INTERVENTION NEEDED"
    fi
  fi
  log "ROLLBACK: complete"
}

on_exit() {
  local ec=$?
  trap - EXIT
  if [ "$DEPLOY_OK" = "1" ] || [ "$ec" -eq 0 ]; then
    exit "$ec"
  fi
  log "deploy FAILED (exit $ec)"
  if [ "$CHECKOUT_MOVED" = "1" ] || [ "$SERVICE_STOPPED" = "1" ]; then
    do_rollback
  else
    log "nothing to roll back (no state changed yet)"
  fi
  exit "$ec"
}
trap on_exit EXIT

fail() { log "ERROR: $*"; exit 1; }

# --- 4. Read-only pre-deploy gate (while the OLD service is still up) -------
# Run this BEFORE stopping the backend so its live-health / container / env
# checks are meaningful. The target-tree schema check is deploy.sh's own job
# (step 9). Full output is tee'd to the deploy log.
set +e
./scripts/predeploy_check.sh 2>&1 | tee -a "$LOG"
PREDEPLOY_RC=${PIPESTATUS[0]}
set -e
if [ "$PREDEPLOY_RC" -eq 0 ]; then
  log "predeploy_check passed"
elif [ "$FORCE_PREDEPLOY" = "1" ]; then
  log "predeploy_check FAILED (rc=$PREDEPLOY_RC) — continuing on operator override (--force-predeploy); full output recorded above in $LOG"
else
  fail "predeploy check failed (rc=$PREDEPLOY_RC); full output in $LOG.
Re-run with --force-predeploy only after reviewing every FAIL line."
fi

# --- 5. Quiesce the service for the whole deployment -----------------------
# The backend runs FROM this checkout and its request handlers do lazy imports,
# so replacing files under a live process yields a mixed release (new code /
# old schema). Stop it before the checkout and keep it down until the new
# release passes health. Zero-downtime would need a separate release directory
# with an atomic switch, or blue/green -- out of scope here (see DEPLOYMENT.md).
log "stopping $SERVICE for deployment"
# Arm rollback BEFORE issuing the stop: a stop that exits non-zero (timed-out
# job, or the unit was killed) may still have taken the backend down, and the
# EXIT handler must then run recovery instead of reporting "nothing changed".
SERVICE_STOPPED=1
$NEXUS_SYSTEMCTL stop "$SERVICE" || fail "could not stop $SERVICE cleanly"

# --- 6. Move the checkout ----------------------------------------------------
if [ "$OLD_SHA" = "$NEW_SHA" ]; then
  log "already at ${NEW_SHA:0:12} — no checkout needed"
else
  CHECKOUT_MOVED=1   # HEAD may move even on a partial/failed checkout
  git checkout --detach "$NEW_SHA" --quiet || fail "git checkout of $NEW_SHA failed"
  # git can advance HEAD, print "unable to unlink old '<path>'", and still exit
  # zero when it cannot replace a file (parent dir perms). The SHA then looks
  # right while old file contents linger in the new release -- verify the
  # worktree actually matches.
  if [ -n "$(git status --porcelain)" ]; then
    git status --short >&2
    fail "git checkout of $NEW_SHA left the worktree dirty — some files were not updated; not deploying a half-applied release"
  fi
  log "checked out ${NEW_SHA:0:12}"
fi
CHECKOUT_MOVED=1

# --- 7. Target dependency environment ------------------------------------------
# Snapshot the venv (so rollback can undo it), then install target deps BEFORE
# any target-tree Alembic call: env.py imports every model and several
# migrations import services, so a release that adds a dependency would make
# even `alembic current/heads` fail under the old virtualenv.
if [ "$SKIP_DEPS" = "1" ]; then
  log "skipping backend dependency install (--skip-deps)"
else
  VENV_SNAPSHOT="$NEXUS_BACKUP_DIR/venv-rollback-${NEW_SHA:0:12}-$(date +%s)"
  mkdir -p "$NEXUS_BACKUP_DIR"
  snapshot_tree "$VENV" "$VENV_SNAPSHOT" || fail "could not snapshot $VENV for rollback"
  DEPS_INSTALLED=1
  ./backend/.venv/bin/pip install -q -r backend/requirements.txt || fail "backend dependency install failed"
  log "backend dependencies installed (rollback snapshot: $VENV_SNAPSHOT)"
fi

# --- 8. Build the frontend (if requested) --------------------------------
if [ "$DO_FRONTEND" = "1" ]; then
  ( cd frontend && npm ci ) || fail "frontend: npm ci failed"
  ( cd frontend && VITE_API_URL= npm run build ) || fail "frontend: build failed"
  [ -f frontend/dist/index.html ] || fail "frontend: build produced no dist/index.html"
  log "frontend build complete"
fi

# --- 9. Schema compatibility guard (ALWAYS, even with --skip-migrations) ------
# --skip-migrations only means "don't run alembic upgrade"; it must not let old
# code deploy against a newer schema. This FAILS CLOSED: real Alembic exits
# non-zero without a revision precisely when the live DB is stamped with a
# revision the target tree does not contain -- the exact case this catches.
db_intro_rc=0
DB_REVS="$(alembic_backend current 2>>"$LOG" | awk 'NF{print $1}')" || db_intro_rc=1
TARGET_HEADS="$(alembic_backend heads 2>>"$LOG" | awk 'NF{print $1}')" || db_intro_rc=1
db_rev_count="$(printf '%s\n' "$DB_REVS" | grep -c . || true)"
target_head_count="$(printf '%s\n' "$TARGET_HEADS" | grep -c . || true)"

# Divergent target heads or a branched DB would let the "already at head" check
# below skip a migration that is actually needed. Never guess -- require one.
if [ "$target_head_count" -gt 1 ]; then
  fail "target commit ${NEW_SHA:0:12} has $target_head_count Alembic heads:
$TARGET_HEADS
Merge them to a single head before deploying."
fi
if [ "$db_rev_count" -gt 1 ]; then
  fail "the live database reports $db_rev_count current Alembic revisions:
$DB_REVS
Resolve the branched revision before deploying."
fi
DB_REV="$(printf '%s\n' "$DB_REVS" | awk 'NF{print;exit}')"
TARGET_HEAD="$(printf '%s\n' "$TARGET_HEADS" | awk 'NF{print;exit}')"

if [ "$db_intro_rc" != "0" ] || [ -z "$DB_REV" ] || [ -z "$TARGET_HEAD" ]; then
  if [ "$ALLOW_DB_AHEAD" = "1" ]; then
    log "WARNING: could not confirm DB<->target schema compatibility (alembic introspection failed / empty); continuing on --allow-db-ahead"
  else
    fail "could not confirm the live database is compatible with target ${NEW_SHA:0:12}:
alembic could not read 'current'/'heads' (rc=$db_intro_rc, db_rev='${DB_REV:-}', target_head='${TARGET_HEAD:-}').
This usually means the DB is stamped with a revision the target tree does not contain.
Restore a database backup taken at/before the target's migration head, then re-run
with --allow-db-ahead; or choose a compatible target. Checkout restored to ${OLD_SHA:0:12}."
  fi
elif [ "$DB_REV" != "$TARGET_HEAD" ]; then
  if alembic_backend history -r "${DB_REV}:${TARGET_HEAD}" >/dev/null 2>>"$LOG"; then
    : # DB revision is an ancestor of the target head -> a forward upgrade, fine
  elif [ "$ALLOW_DB_AHEAD" = "1" ]; then
    log "WARNING: live DB revision $DB_REV is not in the target tree; continuing on --allow-db-ahead"
  else
    fail "live database is at revision '$DB_REV', which the target commit ${NEW_SHA:0:12} does not contain.
Deploying would run older code against a newer schema. Either:
  (a) restore a database backup taken at/before that commit's migration head
      ($TARGET_HEAD), then re-run with --allow-db-ahead; or
  (b) choose a target commit whose migrations include revision $DB_REV.
Checkout is being restored to ${OLD_SHA:0:12}."
  fi
fi

# --skip-migrations must not start the new code against a schema that is merely
# an ANCESTOR of the target head -- that release needs its migration. Only
# tolerable when the DB is already exactly at the target head, or the operator
# forces --allow-db-ahead (having migrated out of band).
if [ "$SKIP_MIGRATIONS" = "1" ] && [ "$ALLOW_DB_AHEAD" != "1" ] \
   && [ -n "$DB_REV" ] && [ -n "$TARGET_HEAD" ] && [ "$DB_REV" != "$TARGET_HEAD" ]; then
  fail "--skip-migrations, but the live database is at '$DB_REV' and the target head is '$TARGET_HEAD'.
The target release needs a migration; starting it now would run new code against a behind schema.
Re-run WITHOUT --skip-migrations, or (only if the DB was already migrated out of band) with --allow-db-ahead."
fi

# --- 10. Migration: back up, then upgrade (service already stopped, step 5) --
if [ "$SKIP_MIGRATIONS" = "1" ]; then
  log "skipping alembic upgrade (--skip-migrations)"
elif [ -n "$DB_REV" ] && [ "$DB_REV" = "$TARGET_HEAD" ]; then
  log "database already at target head $TARGET_HEAD — no migration to run"
else
  STAMP="predeploy-${NEW_SHA:0:12}-$(date +%Y%m%d-%H%M%S)"
  log "taking pre-migration backup (stamp $STAMP)"
  if NEXUS_SQLITE_DB="$DB_PATH" NEXUS_BACKUP_DIR="$NEXUS_BACKUP_DIR" NEXUS_BACKUP_STAMP="$STAMP" \
       "$NEXUS_BACKUP_SCRIPT" >>"$LOG" 2>&1; then
    DB_BACKUP_BEFORE="$NEXUS_BACKUP_DIR/nexus-$STAMP.db.gz"
    [ -f "$DB_BACKUP_BEFORE" ] || fail "backup script reported success but $DB_BACKUP_BEFORE is missing"
    log "pre-migration backup ok: $DB_BACKUP_BEFORE"
  else
    fail "pre-migration backup failed; not touching the schema"
  fi
  MIGRATION_ATTEMPTED=1
  alembic_backend upgrade head || fail "alembic upgrade head failed"
  log "alembic upgrade head complete (service stopped)"
fi

# --- 11. Start the backend on the new release + health --------------------
# The unit binds 0.0.0.0:8000 and nginx keeps proxying /api/ + /auth/ to it, so
# the new process is publicly reachable the moment it starts -- there is a brief
# window (until the first /health response below) where it could accept a write
# that an immediately-following rollback would discard. The first health probe
# fires with no delay, so in practice this is sub-second for a healthy process;
# a true zero-exposure deploy needs the out-of-scope blue/green setup noted in
# DEPLOYMENT.md.
SERVICE_RESTARTED=1
$NEXUS_SYSTEMCTL start "$SERVICE" || fail "systemctl start $SERVICE failed"
log "new backend started on ${NEW_SHA:0:12}; verifying /health before committing"
if ! health_ok "$NEXUS_HEALTH_URL"; then
  $NEXUS_SYSTEMCTL show -p ActiveState -p SubState "$SERVICE" 2>/dev/null | tee -a "$LOG" || true
  fail "backend health check failed after start ($NEXUS_HEALTH_URL)"
fi
# Point of no return for the database: from here a failure rolls back only the
# frontend, never the schema (the NEW backend has begun accepting writes).
BACKEND_COMMITTED=1
log "backend healthy on ${NEW_SHA:0:12} — code + schema committed"

# --- 12. Optional frontend swap (build already done in step 8) -----------
if [ "$DO_FRONTEND" = "1" ]; then
  FRONTEND_SNAPSHOT="$(mktemp -d "${TMPDIR:-/tmp}/nexus-fe-rollback.XXXXXX")"
  mkdir -p "$FRONTEND_SNAPSHOT/html"
  docker cp "$NEXUS_FRONTEND_CONTAINER:/usr/share/nginx/html/." "$FRONTEND_SNAPSHOT/html/" \
    || fail "frontend: could not snapshot current container assets"
  docker cp "$NEXUS_FRONTEND_CONTAINER:/etc/nginx/conf.d/default.conf" "$FRONTEND_SNAPSHOT/default.conf" \
    || fail "frontend: could not snapshot current nginx config"

  FRONTEND_APPLIED=1
  docker cp frontend/dist/. "$NEXUS_FRONTEND_CONTAINER:/usr/share/nginx/html/" || fail "frontend: asset copy failed"
  docker cp frontend/nginx.host.conf "$NEXUS_FRONTEND_CONTAINER:/etc/nginx/conf.d/default.conf" || fail "frontend: config copy failed"
  docker exec "$NEXUS_FRONTEND_CONTAINER" nginx -t || fail "frontend: nginx config test failed"
  docker exec "$NEXUS_FRONTEND_CONTAINER" nginx -s reload || fail "frontend: nginx reload failed"
  if ! health_ok "$NEXUS_FRONTEND_HEALTH_URL"; then
    fail "frontend health check failed after reload ($NEXUS_FRONTEND_HEALTH_URL)"
  fi
  log "frontend swapped in and nginx reloaded"
fi

DEPLOY_OK=1
[ -n "$FRONTEND_SNAPSHOT" ] && { rm -rf "$FRONTEND_SNAPSHOT" 2>/dev/null || true; }
[ -n "$VENV_SNAPSHOT" ] && { rm -rf "$VENV_SNAPSHOT" 2>/dev/null || true; }
log "deploy OK: now serving ${NEW_SHA:0:12} (was ${OLD_SHA:0:12})"

}
exit 0
