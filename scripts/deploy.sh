#!/usr/bin/env bash
# The ONLY supported way to change what nexus-admin-academy.service serves.
#
# This directory is a deploy-only checkout. It must never carry a dev/review
# branch, uncommitted edits, or automated commits (the nightly snapshot skips
# it). All feature work happens in a git worktree elsewhere. See
# docs/DEPLOYMENT.md -> "Deploying a change".
#
# What it does:
#   1. Refuses to run anywhere except the live serving checkout.
#   2. Refuses to run with a dirty working tree.
#   3. git fetch, then checkout --detach the pinned target commit.
#   4. Runs scripts/predeploy_check.sh (read-only gate).
#   5. Installs backend deps + runs alembic upgrade head (both skippable).
#   6. Restarts the backend and verifies /health; rolls back on failure.
#   7. Optionally rebuilds + reloads the nginx frontend (--frontend).
#   8. Appends a line to ~/deploy-logs/nexus-deploy.log for every run.
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
#   --force-predeploy  Continue even if scripts/predeploy_check.sh fails. Every
#                      FAIL line is logged. Use only after reviewing each one
#                      (e.g. a known-stale host artifact unrelated to the change).
#   --dry-run          Print the plan and resolved SHAs, change nothing.
#   -h, --help         Show this header.
#
# Examples:
#   scripts/deploy.sh                               # deploy origin/main
#   scripts/deploy.sh origin/main --frontend        # backend + frontend
#   scripts/deploy.sh --skip-deps --skip-migrations abc1234   # code-only hotfix

set -euo pipefail

SERVICE="nexus-admin-academy.service"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$HOME/deploy-logs"
LOG="$LOG_DIR/nexus-deploy.log"

REF="origin/main"
DO_FRONTEND=0
SKIP_DEPS=0
SKIP_MIGRATIONS=0
FORCE_PREDEPLOY=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --frontend)        DO_FRONTEND=1 ;;
    --skip-deps)       SKIP_DEPS=1 ;;
    --skip-migrations) SKIP_MIGRATIONS=1 ;;
    --force-predeploy) FORCE_PREDEPLOY=1 ;;
    --dry-run)         DRY_RUN=1 ;;
    -h|--help)         awk 'NR>1 && /^#/{sub(/^# ?/,"");print;next} NR>1{exit}' "$0"; exit 0 ;;
    -*)                echo "Unknown option: $arg" >&2; exit 2 ;;
    *)                 REF="$arg" ;;
  esac
done

cd "$REPO_ROOT"
mkdir -p "$LOG_DIR"

log() { printf '%s  %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
abort() { echo "ABORT: $*" >&2; exit 1; }

# --- 1. Must be THE serving checkout -----------------------------------------
SERVING_DIR="$(systemctl show -p WorkingDirectory --value "$SERVICE" 2>/dev/null || true)"
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

# --- 3. Resolve target ----------------------------------------------------------
git fetch --prune origin
NEW_SHA="$(git rev-parse --verify "${REF}^{commit}")"

PLAN="operator=$(whoami) service=$SERVICE ref=$REF old=${OLD_SHA:0:12} new=${NEW_SHA:0:12} frontend=$DO_FRONTEND skip_deps=$SKIP_DEPS skip_migrations=$SKIP_MIGRATIONS force_predeploy=$FORCE_PREDEPLOY"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY RUN — $PLAN"
  if [ "$OLD_SHA" = "$NEW_SHA" ]; then echo "would stay on ${NEW_SHA:0:12}"; else echo "would checkout ${NEW_SHA:0:12}"; fi
  exit 0
fi

log "deploy start: $PLAN"

rollback() {
  log "ROLLBACK -> ${OLD_SHA:0:12}"
  git checkout --detach "$OLD_SHA" --quiet || true
}

# --- 4. Move the checkout -------------------------------------------------------
if [ "$OLD_SHA" = "$NEW_SHA" ]; then
  log "already at ${NEW_SHA:0:12} — no checkout needed"
else
  git checkout --detach "$NEW_SHA" --quiet
  log "checked out ${NEW_SHA:0:12}"
fi

# --- 5. Read-only pre-deploy gate --------------------------------------------
if ./scripts/predeploy_check.sh; then
  :
elif [ "$FORCE_PREDEPLOY" = "1" ]; then
  log "predeploy_check FAILED — continuing on operator override (--force-predeploy)"
else
  log "predeploy_check FAILED"
  rollback
  abort "predeploy check failed; checkout restored to ${OLD_SHA:0:12} (service not restarted).
Re-run with --force-predeploy only after reviewing every FAIL line above."
fi

# --- 6. Backend deps + migrations --------------------------------------------
if [ "$SKIP_DEPS" = "1" ]; then
  log "skipping backend dependency install (--skip-deps)"
else
  ./backend/.venv/bin/pip install -q -r backend/requirements.txt
  log "backend dependencies installed"
fi

if [ "$SKIP_MIGRATIONS" = "1" ]; then
  log "skipping alembic upgrade (--skip-migrations)"
else
  ( cd backend && ./.venv/bin/python -m alembic upgrade head )
  log "alembic upgrade head complete"
fi

# --- 7. Restart + health ------------------------------------------------------
sudo systemctl restart "$SERVICE"
sleep 2
if ! curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/health >/dev/null; then
  log "HEALTH CHECK FAILED after restart"
  sudo journalctl -u "$SERVICE" -n 50 --no-pager | tee -a "$LOG" || true
  rollback
  sudo systemctl restart "$SERVICE" || true
  abort "health check failed; rolled back to ${OLD_SHA:0:12} and restarted. Check the log above."
fi
log "backend healthy on ${NEW_SHA:0:12}"

# --- 8. Optional frontend ----------------------------------------------------
if [ "$DO_FRONTEND" = "1" ]; then
  (
    cd frontend
    npm ci
    VITE_API_URL= npm run build
    docker cp dist/. nexus-frontend:/usr/share/nginx/html/
    docker cp nginx.host.conf nexus-frontend:/etc/nginx/conf.d/default.conf
    docker exec nexus-frontend nginx -t
    docker exec nexus-frontend nginx -s reload
  )
  curl --fail --silent --show-error --max-time 10 http://127.0.0.1/health >/dev/null
  log "frontend rebuilt and nginx reloaded"
fi

log "deploy OK: now serving ${NEW_SHA:0:12} (was ${OLD_SHA:0:12})"
