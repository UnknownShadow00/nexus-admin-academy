#!/usr/bin/env bash
# Failure-simulation harness for scripts/deploy.sh.
#
# Runs the REAL scripts/deploy.sh against a throwaway git "serving checkout"
# with fake systemctl / curl / npm / docker on PATH and stub
# predeploy_check.sh / backup_sqlite.sh / venv python+pip, then asserts that
# every post-checkout failure path rolls the checkout (and, for migrations,
# the database) back to the previous state.
#
# No root, no network, no real services. Safe in CI. Usage: scripts/tests/deploy_failure_sim.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_SRC="$REPO_ROOT/scripts/deploy.sh"
[ -f "$DEPLOY_SRC" ] || { echo "cannot find $DEPLOY_SRC" >&2; exit 1; }

PASS=0 FAIL=0
ok()  { PASS=$((PASS + 1)); printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  \033[31mFAIL\033[0m %s\n' "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/       | /'; }

SIM_VARS="SIM_PREDEPLOY_FAIL SIM_BACKUP_FAIL SIM_ALEMBIC_FAIL SIM_PIP_FAIL
SIM_SYSTEMCTL_RESTART_FAIL SIM_SYSTEMCTL_START_FAIL SIM_HEALTH_FAIL
SIM_NEW_UNHEALTHY SIM_NPM_FAIL SIM_DOCKER_FAIL SIM_HISTORY_RC"
reset_sims() { for v in $SIM_VARS; do unset "$v"; done; }

# ---------------------------------------------------------------------------
setup_env() {
  WORK="$(cd "$(mktemp -d)" && pwd -P)"
  SERVING="$WORK/serving"
  FAKEBIN="$WORK/bin"
  export WORK SERVING
  export SERVING_BACKEND="$SERVING/backend"
  mkdir -p "$FAKEBIN" "$WORK/deploy-logs" "$WORK/backups" \
           "$SERVING/scripts" "$SERVING/backend/.venv/bin" "$SERVING/frontend"

  # --- fake PATH binaries -------------------------------------------------
  cat > "$FAKEBIN/systemctl" <<'EOF'
#!/usr/bin/env bash
cmd="${1:-}"; shift || true
case "$cmd" in
  show)
    if printf '%s\n' "$@" | grep -q WorkingDirectory; then echo "$SERVING_BACKEND"
    else echo "ActiveState=active"; echo "SubState=running"; fi ;;
  restart)
    echo "restart $*" >> "$WORK/systemctl.log"
    [ -n "${SIM_SYSTEMCTL_RESTART_FAIL:-}" ] && exit 1
    : > "$WORK/new_active"; exit 0 ;;
  stop)
    echo "stop $*" >> "$WORK/systemctl.log"; rm -f "$WORK/new_active"; exit 0 ;;
  start)
    echo "start $*" >> "$WORK/systemctl.log"
    [ -n "${SIM_SYSTEMCTL_START_FAIL:-}" ] && exit 1
    exit 0 ;;
  *) exit 0 ;;
esac
EOF

  cat > "$FAKEBIN/curl" <<'EOF'
#!/usr/bin/env bash
[ -n "${SIM_HEALTH_FAIL:-}" ] && exit 22
if [ -n "${SIM_NEW_UNHEALTHY:-}" ] && [ -f "$WORK/new_active" ]; then exit 22; fi
exit 0
EOF

  cat > "$FAKEBIN/npm" <<'EOF'
#!/usr/bin/env bash
[ -n "${SIM_NPM_FAIL:-}" ] && exit 1
if [ "${1:-}" = "run" ]; then mkdir -p dist && echo built > dist/index.html; fi
exit 0
EOF

  cat > "$FAKEBIN/docker" <<'EOF'
#!/usr/bin/env bash
[ -n "${SIM_DOCKER_FAIL:-}" ] && exit 1
if [ "${1:-}" = "cp" ]; then
  src="${2:-}"; dst="${3:-}"
  case "$src" in
    *:*) mkdir -p "$(dirname "$dst")" 2>/dev/null || true
         if [ "${src: -2}" = "/." ]; then mkdir -p "$dst"; echo old > "$dst/old-asset";
         else echo old-conf > "$dst"; fi ;;
  esac
fi
exit 0
EOF
  chmod +x "$FAKEBIN"/*

  # --- stub scripts inside the serving checkout -------------------------
  cat > "$SERVING/scripts/predeploy_check.sh" <<'EOF'
#!/usr/bin/env bash
echo "INFO: sim predeploy gate"
if [ -n "${SIM_PREDEPLOY_FAIL:-}" ]; then
  echo "FAIL: sim-sentinel-DO-NOT-DEPLOY" >&2
  echo "PREDEPLOY CHECK FAILED" >&2
  exit 1
fi
echo "PREDEPLOY CHECK PASSED"
EOF

  cat > "$SERVING/scripts/backup_sqlite.sh" <<'EOF'
#!/usr/bin/env bash
set -eu
[ -n "${SIM_BACKUP_FAIL:-}" ] && { echo "sim backup failure" >&2; exit 1; }
db="${NEXUS_SQLITE_DB:?}"; dir="${NEXUS_BACKUP_DIR:?}"; stamp="${NEXUS_BACKUP_STAMP:?}"
mkdir -p "$dir"
gzip -c "$db" > "$dir/nexus-$stamp.db.gz"
echo "sim backup ok: $dir/nexus-$stamp.db.gz"
EOF

  cat > "$SERVING/backend/.venv/bin/python" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "-m" ] && [ "${2:-}" = "alembic" ]; then
  shift 2; sub="${1:-}"
  db="${NEXUS_SQLITE_DB:-$PWD/nexus.db}"
  content="$(cat "$db" 2>/dev/null || echo OLD)"
  case "$content" in
    OLD*)      rev=rev_old ;;
    MIGRATED*) rev=rev_head ;;
    PARTIAL*)  rev=rev_partial ;;
    FUTURE*)   rev=rev_future ;;
    *)         rev=rev_old ;;
  esac
  case "$sub" in
    current) echo "$rev (head)" ;;
    heads)   echo "rev_head (head)" ;;
    history) exit "${SIM_HISTORY_RC:-0}" ;;
    upgrade)
      if [ -n "${SIM_ALEMBIC_FAIL:-}" ]; then echo PARTIAL > "$db"; echo "sim alembic failure" >&2; exit 1; fi
      echo MIGRATED > "$db"; echo "sim upgraded to head" ;;
  esac
  exit 0
fi
echo "python stub: unsupported: $*" >&2; exit 2
EOF

  cat > "$SERVING/backend/.venv/bin/pip" <<'EOF'
#!/usr/bin/env bash
[ -n "${SIM_PIP_FAIL:-}" ] && { echo "sim pip failure" >&2; exit 1; }
echo "sim pip ok"
EOF
  chmod +x "$SERVING/scripts/"*.sh "$SERVING/backend/.venv/bin/"*

  cp "$DEPLOY_SRC" "$SERVING/scripts/deploy.sh"
  chmod +x "$SERVING/scripts/deploy.sh"

  printf 'DATABASE_URL=sqlite:///nexus.db\n' > "$SERVING/backend/.env"
  printf 'fastapi\n' > "$SERVING/backend/requirements.txt"
  printf '{"name":"sim"}\n' > "$SERVING/frontend/package.json"
  printf 'server { listen 80; }\n' > "$SERVING/frontend/nginx.host.conf"

  cat > "$SERVING/.gitignore" <<'EOF'
backend/nexus.db
backend/nexus.db-wal
backend/nexus.db-shm
*.db.gz
frontend/dist/
frontend/node_modules/
EOF

  ( cd "$SERVING"
    git init -q
    git config user.email sim@example.com
    git config user.name sim
    git config core.fileMode true
    git add -A
    git commit -qm base
    git rev-parse HEAD > "$WORK/OLD_SHA"
    echo NEW > deployed_marker
    git add -A
    git commit -qm new
    git rev-parse HEAD > "$WORK/NEW_SHA"
    git init --bare -q "$WORK/origin.git"
    git remote add origin "$WORK/origin.git"
    git push -q origin HEAD:main
    git checkout -q --detach "$(cat "$WORK/OLD_SHA")"
  )
  OLD_SHA="$(cat "$WORK/OLD_SHA")"
  NEW_SHA="$(cat "$WORK/NEW_SHA")"
  printf 'OLD' > "$SERVING/backend/nexus.db"
}

teardown_env() { [ -n "${WORK:-}" ] && rm -rf "$WORK"; }

run_deploy() {
  OUT="$(
    cd "$SERVING" && PATH="$FAKEBIN:$PATH" HOME="$WORK" \
      NEXUS_SYSTEMCTL=systemctl \
      NEXUS_DEPLOY_LOG_DIR="$WORK/deploy-logs" \
      NEXUS_BACKUP_DIR="$WORK/backups" \
      NEXUS_SQLITE_DB="$SERVING/backend/nexus.db" \
      NEXUS_BACKUP_SCRIPT="$SERVING/scripts/backup_sqlite.sh" \
      NEXUS_HEALTH_RETRIES=2 NEXUS_HEALTH_DELAY=0 \
      bash scripts/deploy.sh "$@" 2>&1
  )"
  RC=$?
  LOGTXT="$(cat "$WORK/deploy-logs/nexus-deploy.log" 2>/dev/null || true)"
}

head_sha() { git -C "$SERVING" rev-parse HEAD; }
a_rc_ne0()  { [ "$RC" -ne 0 ] && ok "exit non-zero ($RC)" || bad "expected non-zero exit" "$OUT"; }
a_rc_0()    { [ "$RC" -eq 0 ] && ok "exit zero" || bad "expected zero exit (got $RC)" "$OUT"; }
a_head_old(){ [ "$(head_sha)" = "$OLD_SHA" ] && ok "checkout rolled back to OLD" || bad "HEAD=$(head_sha) want OLD=$OLD_SHA"; }
a_head_new(){ [ "$(head_sha)" = "$NEW_SHA" ] && ok "checkout at NEW" || bad "HEAD=$(head_sha) want NEW=$NEW_SHA"; }
a_log()     { case "$LOGTXT" in *"$1"*) ok "log ~ '$1'";; *) bad "log missing '$1'" "$LOGTXT";; esac; }
a_nolog()   { case "$LOGTXT" in *"$1"*) bad "log unexpectedly has '$1'" "$LOGTXT";; *) ok "log lacks '$1'";; esac; }
a_db()      { local c; c="$(cat "$SERVING/backend/nexus.db")"; [ "$c" = "$1" ] && ok "db == '$1'" || bad "db == '$c' want '$1'"; }
a_out()     { case "$OUT" in *"$1"*) ok "output ~ '$1'";; *) bad "output missing '$1'" "$OUT";; esac; }

case_start() { printf '\n\033[1m# %s\033[0m\n' "$1"; reset_sims; setup_env; }

# ===========================================================================
case_start "S0  happy path, code-only deploy"
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_0; a_head_new; a_log "deploy OK"; a_nolog "ROLLBACK"
teardown_env

case_start "S1  dependency-install failure rolls back the checkout"
  export SIM_PIP_FAIL=1
  run_deploy --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "backend dependency install failed"; a_log "ROLLBACK: complete"
  [ -f "$WORK/systemctl.log" ] && grep -q '^restart' "$WORK/systemctl.log" \
    && bad "service was restarted despite earlier failure" || ok "service never restarted"
teardown_env

case_start "S2  migration failure restores the pre-migration database"
  export SIM_ALEMBIC_FAIL=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old
  a_log "taking pre-migration backup"; a_log "alembic upgrade head failed"
  a_log "restoring database from"; a_db "OLD"
teardown_env

case_start "S2b pre-migration backup failure aborts before touching schema"
  export SIM_BACKUP_FAIL=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old
  a_log "pre-migration backup failed"; a_nolog "alembic upgrade head complete"
  a_db "OLD"
teardown_env

case_start "S3  systemctl restart failure rolls back and cycles the service"
  export SIM_SYSTEMCTL_RESTART_FAIL=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "systemctl restart"; a_log "ROLLBACK: starting"
  grep -q '^stop'  "$WORK/systemctl.log" && ok "rollback stopped service"  || bad "no stop in rollback"
  grep -q '^start' "$WORK/systemctl.log" && ok "rollback started service" || bad "no start in rollback"
teardown_env

case_start "S4a backend health failure on new release, rollback recovers"
  export SIM_NEW_UNHEALTHY=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "health check failed after restart"
  a_log "ROLLBACK: backend healthy on"; a_nolog "MANUAL INTERVENTION"
teardown_env

case_start "S4b backend health failure that rollback cannot fix is flagged"
  export SIM_HEALTH_FAIL=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "MANUAL INTERVENTION NEEDED"
teardown_env

case_start "S5  frontend build failure rolls back backend too"
  export SIM_NPM_FAIL=1
  run_deploy --skip-deps --skip-migrations --frontend origin/main
  a_rc_ne0; a_head_old
  a_log "frontend: npm ci failed"; a_log "ROLLBACK: starting"
teardown_env

case_start "S5b frontend reload failure triggers frontend + backend rollback"
  export SIM_DOCKER_FAIL=1
  run_deploy --skip-deps --skip-migrations --frontend origin/main
  a_rc_ne0; a_head_old
  a_out "frontend:"; a_log "ROLLBACK"
teardown_env

case_start "S6  --force-predeploy records every FAIL line in the deploy log"
  export SIM_PREDEPLOY_FAIL=1
  run_deploy --skip-deps --skip-migrations --force-predeploy origin/main
  a_rc_0; a_head_new
  a_log "sim-sentinel-DO-NOT-DEPLOY"
  a_log "continuing on operator override"
teardown_env

case_start "S6b predeploy failure without override aborts, logs the FAIL line"
  export SIM_PREDEPLOY_FAIL=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "sim-sentinel-DO-NOT-DEPLOY"; a_log "predeploy check failed"
teardown_env

case_start "S7a schema-ahead database is refused with actionable guidance"
  printf 'FUTURE' > "$SERVING/backend/nexus.db"
  export SIM_HISTORY_RC=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old
  a_log "live database is at revision 'rev_future'"
  a_log "re-run with --allow-db-ahead"
  a_nolog "taking pre-migration backup"
teardown_env

case_start "S7b --allow-db-ahead proceeds past the schema-ahead guard"
  printf 'FUTURE' > "$SERVING/backend/nexus.db"
  export SIM_HISTORY_RC=1
  run_deploy --skip-deps --allow-db-ahead origin/main
  a_rc_0; a_head_new
  a_log "continuing on --allow-db-ahead"
teardown_env

case_start "S7c migration applied then health fails -> DB restored to pre-migration state"
  export SIM_NEW_UNHEALTHY=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old
  a_log "alembic upgrade head complete"
  a_log "restoring database from"
  a_db "OLD"
teardown_env

# ===========================================================================
printf '\n\033[1m%d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
