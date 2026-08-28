#!/usr/bin/env bash
# Focused tests for predeploy_check.sh's Service Desk deployment check.
#
# Production runs the simulator from the `nexus-service-desk` Docker container,
# not a host `.next/` build, so the gate must validate the container -- present,
# running, and (if it declares a healthcheck) healthy -- and must NOT depend on
# `service-desk-app/apps/web/.next/BUILD_ID`.
#
# No root, no network, no services: a fake `docker` on PATH feeds the function.

set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREDEPLOY="$SCRIPTS_DIR/predeploy_check.sh"
[ -f "$PREDEPLOY" ] || { echo "cannot find $PREDEPLOY" >&2; exit 1; }

PASS=0 FAIL=0
ok()  { PASS=$((PASS + 1)); printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  \033[31mFAIL\033[0m %s\n' "$1"; }

# Load just the helpers (the gate is skipped by the sourced-mode guard).
PREDEPLOY_CHECK_SOURCED=1 source "$PREDEPLOY"
set +e   # the sourced script enabled `set -e`; tests check exit codes by hand

type service_desk_container_ok >/dev/null 2>&1 \
    && ok "service_desk_container_ok is defined after sourcing" \
    || { bad "service_desk_container_ok not defined"; printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"; exit 1; }

WORK="$(mktemp -d)"; BIN="$WORK/bin"; mkdir -p "$BIN"
trap 'rm -rf "$WORK"' EXIT
export PATH="$BIN:$PATH"

# Write a fake `docker` whose `inspect --format <fmt> <name>` answers from two
# env vars: FAKE_STATE (State.Status) and FAKE_HEALTH (the health branch).
# FAKE_STATE=absent makes `docker inspect` exit non-zero (container missing).
make_docker() {
  cat > "$BIN/docker" <<'EOF'
#!/usr/bin/env bash
[ "${1:-}" = "inspect" ] || exit 0
fmt=""; for a in "$@"; do case "$prev" in --format) fmt="$a";; esac; prev="$a"; done
[ "${FAKE_STATE:-running}" = "absent" ] && exit 1
case "$fmt" in
  *Health*) echo "${FAKE_HEALTH:-no-healthcheck}" ;;
  *)        echo "${FAKE_STATE:-running}" ;;
esac
EOF
  chmod +x "$BIN/docker"
}
make_docker

run() { FAKE_STATE="$1" FAKE_HEALTH="$2" service_desk_container_ok nexus-service-desk; }

out="$(run running healthy)";        rc=$?
[ $rc -eq 0 ] && [[ "$out" == *"running (healthy)"* ]] && ok "running + healthy -> pass ($out)" || bad "running+healthy: rc=$rc out='$out'"

out="$(run running no-healthcheck)"; rc=$?
[ $rc -eq 0 ] && [[ "$out" == *"no-healthcheck"* ]] && ok "running + no healthcheck -> pass ($out)" || bad "no-healthcheck: rc=$rc out='$out'"

out="$(run running unhealthy)";      rc=$?
[ $rc -ne 0 ] && [[ "$out" == *"health=unhealthy"* ]] && ok "running + unhealthy -> fail ($out)" || bad "unhealthy should fail: rc=$rc out='$out'"

out="$(run running starting)";       rc=$?
[ $rc -ne 0 ] && ok "running + still starting -> fail ($out)" || bad "starting should fail: rc=$rc out='$out'"

out="$(run exited none)";            rc=$?
[ $rc -ne 0 ] && [[ "$out" == *"not running (exited)"* ]] && ok "exited container -> fail ($out)" || bad "exited should fail: rc=$rc out='$out'"

out="$(run absent none)";            rc=$?
[ $rc -ne 0 ] && [[ "$out" == *absent* ]] && ok "missing container -> fail ($out)" || bad "absent should fail: rc=$rc out='$out'"

# The gate must no longer depend on a host Next.js build artifact.
grep -q 'BUILD_ID' "$PREDEPLOY" \
    && bad "predeploy_check.sh still references .next/BUILD_ID" \
    || ok "predeploy_check.sh has no .next/BUILD_ID dependency"
grep -q 'service_desk_container_ok nexus-service-desk' "$PREDEPLOY" \
    && ok "the gate calls service_desk_container_ok for the real container" \
    || bad "the gate does not call service_desk_container_ok"

printf '\n\033[1m%d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
