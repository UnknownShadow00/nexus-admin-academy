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

SIM_VARS="SIM_PREDEPLOY_FAIL SIM_BACKUP_FAIL SIM_ALEMBIC_FAIL SIM_ALEMBIC_CURRENT_FAIL
SIM_PIP_FAIL SIM_SYSTEMCTL_RESTART_FAIL SIM_SYSTEMCTL_START_FAIL SIM_HEALTH_FAIL
SIM_NEW_UNHEALTHY SIM_NPM_FAIL SIM_DOCKER_FAIL SIM_HISTORY_RC
SIM_FRONTEND_SWAP_FAIL SIM_FRONTEND_RELOAD_FAIL"
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
# "new_active" marker = the service is running the NEW release. Derived from
# whatever HEAD the serving checkout is on when start/restart is invoked, so a
# rollback that checks OLD out first correctly clears it.
mark_from_head() {
  if [ "$(git -C "$SERVING" rev-parse HEAD 2>/dev/null)" = "$NEW_SHA" ]; then
    : > "$WORK/new_active"
  else
    rm -f "$WORK/new_active"
  fi
}
case "$cmd" in
  show)
    if printf '%s\n' "$@" | grep -q WorkingDirectory; then echo "$SERVING_BACKEND"
    else echo "ActiveState=active"; echo "SubState=running"; fi ;;
  restart)
    echo "restart $*" >> "$WORK/systemctl.log"
    [ -n "${SIM_SYSTEMCTL_RESTART_FAIL:-}" ] && exit 1
    mark_from_head; exit 0 ;;
  stop)
    echo "stop $*" >> "$WORK/systemctl.log"; rm -f "$WORK/new_active"; exit 0 ;;
  start)
    echo "start $*" >> "$WORK/systemctl.log"
    # only the forward start (on NEW) fails; a rollback start (on OLD) succeeds
    if [ -n "${SIM_SYSTEMCTL_START_FAIL:-}" ] \
       && [ "$(git -C "$SERVING" rev-parse HEAD 2>/dev/null)" = "$NEW_SHA" ]; then exit 1; fi
    mark_from_head; exit 0 ;;
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
  case "$dst" in
    *:*) [ -n "${SIM_FRONTEND_SWAP_FAIL:-}" ] && exit 1 ;;   # copy INTO container
  esac
  case "$src" in
    *:*) mkdir -p "$(dirname "$dst")" 2>/dev/null || true    # copy OUT of container
         if [ "${src: -2}" = "/." ]; then mkdir -p "$dst"; echo old > "$dst/old-asset";
         else echo old-conf > "$dst"; fi ;;
  esac
fi
[ "${1:-}" = "exec" ] && [ -n "${SIM_FRONTEND_RELOAD_FAIL:-}" ] && exit 1
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
    current)
      # Real Alembic exits non-zero without a revision when the DB is stamped
      # with a revision the tree does not contain.
      [ -n "${SIM_ALEMBIC_CURRENT_FAIL:-}" ] && { echo "FAILED: Can't locate revision identified by '$rev'" >&2; exit 255; }
      echo "$rev (head)" ;;
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
# Simulate a dependency change so venv rollback is observable.
d="$(cd "$(dirname "$0")/.." && pwd)"
rm -f "$d/marker-OLD"; : > "$d/marker-NEW"
echo "sim pip ok"
EOF
  chmod +x "$SERVING/scripts/"*.sh "$SERVING/backend/.venv/bin/"*
  : > "$SERVING/backend/.venv/marker-OLD"

  cp "$DEPLOY_SRC" "$SERVING/scripts/deploy.sh"
  chmod +x "$SERVING/scripts/deploy.sh"

  printf 'DATABASE_URL=sqlite:///nexus.db\n' > "$SERVING/backend/.env"
  printf 'fastapi\n' > "$SERVING/backend/requirements.txt"
  printf '{"name":"sim"}\n' > "$SERVING/frontend/package.json"
  printf 'server { listen 80; }\n' > "$SERVING/frontend/nginx.host.conf"

  cat > "$SERVING/.gitignore" <<'EOF'
backend/.venv/
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
  export OLD_SHA="$(cat "$WORK/OLD_SHA")"
  export NEW_SHA="$(cat "$WORK/NEW_SHA")"
  printf 'OLD' > "$SERVING/backend/nexus.db"
}

teardown_env() { [ -n "${WORK:-}" ] && rm -rf "$WORK"; }

run_deploy() {
  OUT="$(
    cd "$SERVING" && PATH="$FAKEBIN:$PATH" HOME="$WORK" \
      NEXUS_SYSTEMCTL=systemctl \
      NEXUS_DEPLOY_LOG_DIR="$WORK/deploy-logs" \
      NEXUS_DEPLOY_LOCK="${NEXUS_DEPLOY_LOCK:-$WORK/deploy.lock}" \
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
a_venv()    { # 1 = expect marker-OLD present and marker-NEW gone (venv restored)
  if [ -f "$SERVING/backend/.venv/marker-OLD" ] && [ ! -f "$SERVING/backend/.venv/marker-NEW" ]
    then ok "virtualenv restored (marker-OLD back, marker-NEW gone)"
    else bad "virtualenv NOT restored (OLD=$( [ -f "$SERVING/backend/.venv/marker-OLD" ] && echo y || echo n ) NEW=$( [ -f "$SERVING/backend/.venv/marker-NEW" ] && echo y || echo n ))"; fi; }
a_order()   { # asserts "$1" appears before "$2" in the deploy log
  local a b; a="$(printf '%s\n' "$LOGTXT" | grep -n -- "$1" | head -1 | cut -d: -f1)"
  b="$(printf '%s\n' "$LOGTXT" | grep -n -- "$2" | head -1 | cut -d: -f1)"
  if [ -n "$a" ] && [ -n "$b" ] && [ "$a" -lt "$b" ]; then ok "'$1' logged before '$2'"
  else bad "order wrong: '$1'@${a:-?} vs '$2'@${b:-?}" "$LOGTXT"; fi; }
sctl_order() { # asserts systemctl verb "$1" recorded before verb "$2"
  local a b; a="$(grep -n "^$1" "$WORK/systemctl.log" 2>/dev/null | head -1 | cut -d: -f1)"
  b="$(grep -n "^$2" "$WORK/systemctl.log" 2>/dev/null | head -1 | cut -d: -f1)"
  if [ -n "$a" ] && [ -n "$b" ] && [ "$a" -lt "$b" ]; then ok "systemctl '$1' before '$2'"
  else bad "systemctl order: '$1'@${a:-?} vs '$2'@${b:-?}" "$(cat "$WORK/systemctl.log" 2>/dev/null)"; fi; }

case_start() { printf '\n\033[1m# %s\033[0m\n' "$1"; reset_sims; setup_env; }

# ===========================================================================
case_start "S0  happy path, code-only deploy"
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_0; a_head_new; a_log "deploy OK"; a_nolog "ROLLBACK"
teardown_env

case_start "S0b happy path: deps + migration + frontend all succeed"
  run_deploy --frontend origin/main
  a_rc_0; a_head_new
  a_log "frontend build complete"; a_log "alembic upgrade head complete"
  a_log "frontend swapped in and nginx reloaded"; a_log "deploy OK"
  a_nolog "ROLLBACK"
teardown_env

case_start "S1  dependency-install failure rolls back checkout and virtualenv"
  export SIM_PIP_FAIL=1
  run_deploy --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "backend dependency install failed"; a_log "ROLLBACK: complete"
  a_venv 1
teardown_env

case_start "S1b deps installed, later health failure -> virtualenv restored"
  export SIM_NEW_UNHEALTHY=1
  run_deploy --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "ROLLBACK: restoring virtualenv"
  a_venv 1
teardown_env

case_start "S2  migration failure restores the pre-migration database"
  export SIM_ALEMBIC_FAIL=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old
  a_log "stopping nexus-admin-academy.service for deployment"
  a_log "alembic upgrade head failed"; a_log "restoring database from"; a_db "OLD"
  sctl_order stop start
teardown_env

case_start "S2b pre-migration backup failure aborts before touching schema"
  export SIM_BACKUP_FAIL=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old
  a_log "pre-migration backup failed"; a_nolog "alembic upgrade head complete"
  a_db "OLD"
  grep -q '^start' "$WORK/systemctl.log" && ok "service restarted in rollback" || bad "service not restarted"
teardown_env

case_start "S2c migration quiesces the service BEFORE the backup (no lost writes)"
  run_deploy --skip-deps origin/main
  a_rc_0; a_head_new
  a_order "stopping nexus-admin-academy.service for deployment" "taking pre-migration backup"
  a_order "taking pre-migration backup" "alembic upgrade head complete"
teardown_env

case_start "S2d target deps are installed before any target-tree Alembic call"
  run_deploy origin/main
  a_rc_0; a_head_new
  a_order "backend dependencies installed" "alembic upgrade head complete"
teardown_env

case_start "S3  backend start failure on the new release rolls fully back"
  export SIM_SYSTEMCTL_START_FAIL=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "systemctl start"; a_log "ROLLBACK: backend healthy on"
  grep -q '^stop'  "$WORK/systemctl.log" && ok "rollback stopped service"  || bad "no stop in rollback"
  grep -q '^start' "$WORK/systemctl.log" && ok "rollback started service" || bad "no start in rollback"
teardown_env

case_start "S12 the backend is stopped BEFORE the checkout is touched (no mixed release)"
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_0; a_head_new
  a_order "stopping nexus-admin-academy.service for deployment" "checked out"
  a_order "predeploy_check passed" "stopping nexus-admin-academy.service for deployment"
teardown_env

case_start "S13 a second concurrent deploy is refused by the host lock"
  ( exec 9>"$WORK/deploy.lock"; flock -n 9 || exit 1; sleep 5 ) &
  holder=$!
  sleep 0.5
  NEXUS_DEPLOY_LOCK="$WORK/deploy.lock" run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0
  a_out "another deploy is in progress"
  a_head_old
  kill "$holder" 2>/dev/null; wait "$holder" 2>/dev/null
teardown_env

case_start "S4a backend health failure on new release, rollback recovers"
  export SIM_NEW_UNHEALTHY=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "health check failed after start"
  a_log "ROLLBACK: backend healthy on"; a_nolog "MANUAL INTERVENTION"
teardown_env

case_start "S4b backend health failure that rollback cannot fix is flagged"
  export SIM_HEALTH_FAIL=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "MANUAL INTERVENTION NEEDED"
teardown_env

case_start "S5  frontend build failure never advances the DB and fully rolls back"
  export SIM_NPM_FAIL=1
  run_deploy --frontend origin/main
  a_rc_ne0; a_head_old
  a_log "frontend: npm ci failed"
  a_nolog "code + schema committed"
  a_nolog "alembic upgrade head complete"
  a_db "OLD"
  a_venv 1
  a_log "ROLLBACK: backend healthy on"
teardown_env

case_start "S10a frontend swap fails AFTER a migration -> DB kept, only frontend rolled back"
  export SIM_FRONTEND_SWAP_FAIL=1
  run_deploy --skip-deps --frontend origin/main
  a_rc_ne0
  a_head_new
  a_db "MIGRATED"
  a_log "backend healthy on"
  a_log "rolling back the frontend only"
  a_log "backend stays on"
  a_nolog "restoring database from"
teardown_env

case_start "S10b frontend reload fails AFTER a code-only deploy -> backend kept"
  export SIM_FRONTEND_RELOAD_FAIL=1
  run_deploy --skip-deps --skip-migrations --frontend origin/main
  a_rc_ne0; a_head_new
  a_log "rolling back the frontend only"; a_nolog "checkout -> "
teardown_env

case_start "S11 migration rollback reapplies the live DB file mode (0640)"
  chmod 640 "$SERVING/backend/nexus.db"
  export SIM_ALEMBIC_FAIL=1
  run_deploy --skip-deps origin/main
  a_rc_ne0; a_head_old; a_db "OLD"
  m="$(stat -c '%a' "$SERVING/backend/nexus.db")"
  [ "$m" = "640" ] && ok "restored DB mode is 640" || bad "restored DB mode is $m, want 640"
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
  run_deploy --skip-deps --skip-migrations --allow-db-ahead origin/main
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

case_start "S7d schema-ahead is refused even with --skip-migrations (not just alembic)"
  printf 'FUTURE' > "$SERVING/backend/nexus.db"
  export SIM_HISTORY_RC=1
  run_deploy --skip-deps --skip-migrations origin/main
  a_rc_ne0; a_head_old
  a_log "live database is at revision 'rev_future'"
teardown_env

case_start "S7e schema-ahead + --skip-migrations + --force-predeploy is STILL refused"
  printf 'FUTURE' > "$SERVING/backend/nexus.db"
  export SIM_HISTORY_RC=1 SIM_PREDEPLOY_FAIL=1
  run_deploy --skip-deps --skip-migrations --force-predeploy origin/main
  a_rc_ne0; a_head_old
  a_log "live database is at revision 'rev_future'"
teardown_env

case_start "S9a alembic introspection failure fails CLOSED even with --skip-migrations --force-predeploy"
  export SIM_ALEMBIC_CURRENT_FAIL=1 SIM_PREDEPLOY_FAIL=1
  run_deploy --skip-deps --skip-migrations --force-predeploy origin/main
  a_rc_ne0; a_head_old
  a_log "could not confirm the live database is compatible"
teardown_env

case_start "S9b introspection failure + --allow-db-ahead proceeds with a warning"
  export SIM_ALEMBIC_CURRENT_FAIL=1
  run_deploy --skip-deps --skip-migrations --allow-db-ahead origin/main
  a_rc_0; a_head_new
  a_log "continuing on --allow-db-ahead"
teardown_env

# ===========================================================================
printf '\n\033[1m%d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
