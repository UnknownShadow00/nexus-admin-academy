#!/usr/bin/env bash
# The ONLY supported way to change what nexus-admin-academy.service serves.
#
# This directory is a deploy-only checkout. It must never carry a dev/review
# branch, uncommitted edits, or automated commits (the nightly snapshot skips
# it). All feature work happens in a git worktree elsewhere. See
# docs/DEPLOYMENT.md -> "Deploying a change".
#
# What it does, in order (every step after the checkout is covered by an
# automatic rollback if a later step fails -- see "Rollback" below):
#   1. Refuses to run anywhere except the live serving checkout.
#   2. Refuses to run with a dirty working tree.
#   3. git fetch, then checkout --detach the pinned target commit.
#   4. Snapshots the virtualenv, then installs target backend deps (unless
#      --skip-deps) -- BEFORE predeploy_check and any target-tree Alembic call,
#      which import the target's models/services.
#   5. With --frontend: `npm ci` + build NOW, before anything touches the
#      backend/DB, so a build failure never causes a database rollback.
#   6. Runs scripts/predeploy_check.sh (read-only gate; full output tee'd to
#      the deploy log). A failing gate aborts unless --force-predeploy.
#   7. FAILS CLOSED if it cannot confirm the live schema is compatible with the
#      target (DB revision ahead of / absent from the target tree), unless
#      --allow-db-ahead. Runs even with --skip-migrations.
#   8. If a migration will actually run: stops the service, takes a fresh
#      SQLite + uploads backup (scripts/backup_sqlite.sh), then
#      `alembic upgrade head` -- all with the service down so no write is lost.
#   9. (Re)starts the backend and verifies /health. Once healthy, the code +
#      schema are COMMITTED (see Rollback).
#  10. With --frontend: snapshots the live container assets/config, swaps in the
#      build from step 5, `nginx -t`, reload, re-checks frontend /health.
#  11. Appends timestamped lines to ~/deploy-logs/nexus-deploy.log for every run.
#
# Rollback (automatic, on ANY failure after step 3):
#   - BEFORE the step-9 health check passes -- full unwind: check the old SHA
#     back out; restore the pre-deploy virtualenv snapshot (if deps installed);
#     restore the pre-migration database backup (if a migration was attempted --
#     SQLite DDL here is non-transactional, so a half-applied migration is
#     possible and the backup is the only safe restore, with the live DB's
#     owner/mode reapplied); (re)start the service on the old SHA and
#     re-health-check.
#   - AFTER step 9 (only the frontend swap can fail now) -- the NEW backend has
#     begun accepting writes, so the database is NOT rolled back. Only the
#     frontend snapshot is restored; the backend stays on NEW and the frontend
#     is fixed forward.
#   Rolling back a PAST deploy that changed the schema is NOT just
#   `deploy.sh <old-sha>`: you must first restore a database backup taken at or
#   before that commit's migration head, then re-run with --allow-db-ahead.
#   deploy.sh detects and refuses the unsafe case (step 7).
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
#                      diff contains no migration).
#   --allow-db-ahead   Proceed even though the live DB schema is ahead of the
#                      target commit. Only after restoring a matching DB backup.
#   --force-predeploy  Continue even if scripts/predeploy_check.sh fails. Its
#                      full output (every FAIL line) is written to the deploy
#                      log. Use only after reviewing each failure.
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

SERVICE="$NEXUS_SERVICE"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

cd "$REPO_ROOT"
mkdir -p "$LOG_DIR"

log()  { printf '%s  %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
abort() { echo "ABORT: $*" >&2; exit 1; }

alembic_backend() { ( cd "$REPO_ROOT/backend" && ./.venv/bin/python -m alembic "$@" ); }

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

# --- 1. Must be THE serving checkout -----------------------------------------
SERVING_DIR="$($NEXUS_SYSTEMCTL show -p WorkingDirectory --value "$SERVICE" 2>/dev/null || true)"
if [ -z "$SERVING_DIR" ]; then
  abort "cannot read WorkingDirectory of $SERVICE (is it installed on this host?)"
fi
if [ "$SERVING_DIR" != "$REPO_ROOT/backend" ]; then
  abort "$REPO_ROOT is not the serving checkout. $SERVICE serves: $SERVING_DIR
Deploy only from the production checkout; use a git worktree for everything else."
fi

# --- 2. Clean tree ----------------------------------------------------------
if [ -n "$(git status --porcelain)" ]; then
  git status --short >&2
  abort "serving checkout has uncommitted changes. This directory is deploy-only."
fi

OLD_SHA="$(git rev-parse HEAD)"
DB_PATH="$(resolve_db_path)"

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
  rm -rf "$staged"
  if { cp -al "$VENV_SNAPSHOT" "$staged" 2>/dev/null || cp -a "$VENV_SNAPSHOT" "$staged"; } \
       && rm -rf "$VENV" && mv "$staged" "$VENV"; then
    log "ROLLBACK: virtualenv restored"
  else
    rm -rf "$staged"
    log "ROLLBACK WARNING: virtualenv restore failed — MANUAL INTERVENTION NEEDED"
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
  if gunzip -c "$DB_BACKUP_BEFORE" > "$tmp"; then
    chmod "$ref_mode" "$tmp" 2>/dev/null || log "ROLLBACK WARNING: could not set mode $ref_mode on restored DB"
    chown "$ref_owner" "$tmp" 2>/dev/null || log "ROLLBACK WARNING: could not set owner $ref_owner on restored DB (run rollback as the service user)"
    mv -f "$tmp" "$DB_PATH"
    rm -f "$DB_PATH-wal" "$DB_PATH-shm"
    log "ROLLBACK: database file restored (mode $ref_mode, owner $ref_owner)"
  else
    rm -f "$tmp"
    log "ROLLBACK WARNING: could not decompress $DB_BACKUP_BEFORE — MANUAL INTERVENTION NEEDED"
    return 1
  fi
}

restore_frontend() {
  [ -n "$FRONTEND_SNAPSHOT" ] && [ -d "$FRONTEND_SNAPSHOT" ] || return 0
  log "ROLLBACK: restoring previous frontend assets/config"
  docker cp "$FRONTEND_SNAPSHOT/html/." "$NEXUS_FRONTEND_CONTAINER:/usr/share/nginx/html/" || \
    log "ROLLBACK WARNING: frontend asset restore failed"
  docker cp "$FRONTEND_SNAPSHOT/default.conf" "$NEXUS_FRONTEND_CONTAINER:/etc/nginx/conf.d/default.conf" || \
    log "ROLLBACK WARNING: frontend config restore failed"
  docker exec "$NEXUS_FRONTEND_CONTAINER" nginx -s reload || \
    log "ROLLBACK WARNING: nginx reload after frontend restore failed"
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
    [ "$FRONTEND_APPLIED" = "1" ] && restore_frontend
    log "ROLLBACK: frontend restored — backend stays on ${NEW_SHA:0:12}; redeploy the frontend once fixed"
    return
  fi

  log "ROLLBACK: starting (target ${OLD_SHA:0:12})"

  # Cycle the service if anything it reads at runtime (code, venv, schema) was
  # touched, so it comes back up consistent with the restored old release.
  local cycle_service=0
  { [ "$MIGRATION_ATTEMPTED" = "1" ] || [ "$SERVICE_RESTARTED" = "1" ] \
    || [ "$SERVICE_STOPPED" = "1" ] || [ "$DEPS_INSTALLED" = "1" ]; } && cycle_service=1

  [ "$cycle_service" = "1" ] && { log "ROLLBACK: stopping $SERVICE"; $NEXUS_SYSTEMCTL stop "$SERVICE"; }

  [ "$FRONTEND_APPLIED" = "1" ] && restore_frontend

  if [ "$CHECKOUT_MOVED" = "1" ]; then
    log "ROLLBACK: checkout -> ${OLD_SHA:0:12}"
    git checkout --detach "$OLD_SHA" --quiet || log "ROLLBACK WARNING: git checkout of old SHA failed"
  fi

  [ "$DEPS_INSTALLED" = "1" ] && restore_venv
  [ "$MIGRATION_ATTEMPTED" = "1" ] && restore_database

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
  if [ "$CHECKOUT_MOVED" = "1" ]; then
    do_rollback
  else
    log "nothing to roll back (no checkout move happened)"
  fi
  exit "$ec"
}
trap on_exit EXIT

fail() { log "ERROR: $*"; exit 1; }

# --- 4. Move the checkout -------------------------------------------------------
if [ "$OLD_SHA" = "$NEW_SHA" ]; then
  log "already at ${NEW_SHA:0:12} — no checkout needed"
  CHECKOUT_MOVED=1
else
  git checkout --detach "$NEW_SHA" --quiet || fail "git checkout of $NEW_SHA failed"
  CHECKOUT_MOVED=1
  log "checked out ${NEW_SHA:0:12}"
fi

# --- 5. Target dependency environment ------------------------------------------
# Deps go in BEFORE predeploy_check and any target-tree Alembic call: env.py
# imports every model and several migrations import services, so a release that
# adds a dependency would make even `alembic current/heads` fail under the old
# virtualenv. Snapshot the venv first so rollback can undo it.
if [ "$SKIP_DEPS" = "1" ]; then
  log "skipping backend dependency install (--skip-deps)"
else
  VENV_SNAPSHOT="$NEXUS_BACKUP_DIR/venv-rollback-${NEW_SHA:0:12}-$(date +%s)"
  mkdir -p "$NEXUS_BACKUP_DIR"
  cp -al "$VENV" "$VENV_SNAPSHOT" 2>/dev/null \
    || cp -a "$VENV" "$VENV_SNAPSHOT" \
    || fail "could not snapshot $VENV for rollback"
  DEPS_INSTALLED=1
  ./backend/.venv/bin/pip install -q -r backend/requirements.txt || fail "backend dependency install failed"
  log "backend dependencies installed (rollback snapshot: $VENV_SNAPSHOT)"
fi

# --- 5b. Build the frontend NOW (if requested) -----------------------------
# Do the slow, failure-prone build before anything touches the backend/DB, so a
# build failure never triggers a database rollback. The container swap + reload
# happens later (step 10), after the backend is confirmed healthy.
if [ "$DO_FRONTEND" = "1" ]; then
  ( cd frontend && npm ci ) || fail "frontend: npm ci failed"
  ( cd frontend && VITE_API_URL= npm run build ) || fail "frontend: build failed"
  [ -f frontend/dist/index.html ] || fail "frontend: build produced no dist/index.html"
  log "frontend build complete"
fi

# --- 6. Read-only pre-deploy gate (full output to the deploy log) ----------
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

# --- 7. Schema compatibility guard (ALWAYS, even with --skip-migrations) ------
# --skip-migrations only means "don't run alembic upgrade"; it must not let old
# code deploy against a newer schema. This FAILS CLOSED: real Alembic exits
# non-zero without a revision precisely when the live DB is stamped with a
# revision the target tree does not contain -- the exact case this catches.
db_intro_rc=0
DB_REV="$(alembic_backend current 2>>"$LOG" | awk 'NF{print $1; exit}')" || db_intro_rc=1
TARGET_HEAD="$(alembic_backend heads 2>>"$LOG" | awk 'NF{print $1; exit}')" || db_intro_rc=1

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

# --- 8. Migration: quiesce the service, back up, then upgrade --------------
if [ "$SKIP_MIGRATIONS" = "1" ]; then
  log "skipping alembic upgrade (--skip-migrations)"
elif [ -n "$DB_REV" ] && [ "$DB_REV" = "$TARGET_HEAD" ]; then
  log "database already at target head $TARGET_HEAD — no migration to run"
else
  # Stop the service for the whole schema-change window so no writes land
  # after the backup is taken (they would be lost on rollback) and nothing
  # runs old code against a half-applied schema.
  log "stopping $SERVICE for the migration window"
  $NEXUS_SYSTEMCTL stop "$SERVICE" || fail "could not stop $SERVICE before migration"
  SERVICE_STOPPED=1

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

# --- 9. (Re)start + health --------------------------------------------------
SERVICE_RESTARTED=1
if [ "$SERVICE_STOPPED" = "1" ]; then
  $NEXUS_SYSTEMCTL start "$SERVICE" || fail "systemctl start $SERVICE failed"
else
  $NEXUS_SYSTEMCTL restart "$SERVICE" || fail "systemctl restart $SERVICE failed"
fi
if ! health_ok "$NEXUS_HEALTH_URL"; then
  $NEXUS_SYSTEMCTL show -p ActiveState -p SubState "$SERVICE" 2>/dev/null | tee -a "$LOG" || true
  fail "backend health check failed after restart ($NEXUS_HEALTH_URL)"
fi
# Point of no return for the database: from here a failure rolls back only the
# frontend, never the schema (the NEW backend has begun accepting writes).
BACKEND_COMMITTED=1
log "backend healthy on ${NEW_SHA:0:12} — code + schema committed"

# --- 10. Optional frontend swap (build already done in step 5b) -----------
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
