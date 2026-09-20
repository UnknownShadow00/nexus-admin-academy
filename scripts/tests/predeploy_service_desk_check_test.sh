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
type service_desk_contract_ok >/dev/null 2>&1 \
    && ok "service_desk_contract_ok is defined after sourcing" \
    || { bad "service_desk_contract_ok not defined"; printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"; exit 1; }
type backend_health_ok >/dev/null 2>&1 \
    && ok "backend_health_ok is defined after sourcing" \
    || { bad "backend_health_ok not defined"; printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"; exit 1; }

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

cat > "$BIN/curl" <<'EOF'
#!/usr/bin/env bash
url="${!#}"
[ -n "${FAKE_CURL_LOG:-}" ] && printf '%s\n' "$url" >> "$FAKE_CURL_LOG"
case "$url" in
  */api/service-desk/contract)
    [ "${FAKE_BACKEND_HTTP:-200}" = 200 ] || exit 22
    printf '%s' "${FAKE_BACKEND_BODY:-}"
    ;;
  */service-desk/api/health)
    [ "${FAKE_SD_HTTP:-200}" = 200 ] || exit 22
    printf '%s' "${FAKE_SD_BODY:-}"
    ;;
  */health)
    [ "${FAKE_BACKEND_HTTP:-200}" = 200 ] || exit 22
    printf '%s' "${FAKE_BACKEND_HEALTH_BODY:-ok}"
    ;;
esac
EOF
chmod +x "$BIN/curl"

[[ "$BACKEND_BASE_URL" == "http://127.0.0.1:8000" ]] \
    && ok "default Backend URL remains the development loopback address" \
    || bad "unexpected default Backend URL: $BACKEND_BASE_URL"

configured="$(NEXUS_BACKEND_URL='http://172.17.0.1:8000/' PREDEPLOY_CHECK_SOURCED=1 \
    bash -c 'source "$1"; printf "%s" "$BACKEND_BASE_URL"' _ "$PREDEPLOY")"
[[ "$configured" == "http://172.17.0.1:8000" ]] \
    && ok "configured bridge Backend URL is selected and trailing slash normalized" \
    || bad "configured Backend URL was not normalized: '$configured'"

CURL_LOG="$WORK/curl.log"
: > "$CURL_LOG"
out="$(FAKE_CURL_LOG="$CURL_LOG" BACKEND_BASE_URL='http://172.17.0.1:8000' backend_health_ok)"; rc=$?
[ $rc -eq 0 ] && grep -qx 'http://172.17.0.1:8000/health' "$CURL_LOG" \
    && ok "health probe uses the configured bridge Backend URL" \
    || bad "configured health probe failed: rc=$rc out='$out' calls='$(tr '\n' ' ' < "$CURL_LOG")'"

: > "$CURL_LOG"
out="$(FAKE_CURL_LOG="$CURL_LOG" BACKEND_BASE_URL='http://172.17.0.1:8000/' \
    FAKE_BACKEND_BODY='{"contract_version":"2.0"}' \
    FAKE_SD_BODY='{"status":"ok","contract_version":"2.0"}' \
    service_desk_contract_ok '' 'http://candidate-service-desk')"; rc=$?
[ $rc -eq 0 ] \
    && grep -qx 'http://172.17.0.1:8000/api/service-desk/contract' "$CURL_LOG" \
    && ! grep -q '127.0.0.1:8000' "$CURL_LOG" \
    && ok "contract probe uses the same configured Backend URL without loopback fallback" \
    || bad "configured contract probe failed: rc=$rc out='$out' calls='$(tr '\n' ' ' < "$CURL_LOG")'"

: > "$CURL_LOG"
out="$(FAKE_CURL_LOG="$CURL_LOG" BACKEND_BASE_URL='http://wrong-backend:9999' \
    FAKE_BACKEND_HTTP=503 backend_health_ok)"; rc=$?
[ $rc -ne 0 ] \
    && grep -qx 'http://wrong-backend:9999/health' "$CURL_LOG" \
    && ! grep -q '127.0.0.1:8000' "$CURL_LOG" \
    && ok "wrong configured Backend URL fails without hidden loopback fallback" \
    || bad "wrong configured Backend URL did not fail closed: rc=$rc calls='$(tr '\n' ' ' < "$CURL_LOG")'"

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

contract_run() {
  FAKE_BACKEND_HTTP="${1:-200}" FAKE_BACKEND_BODY="${2:-}" \
  FAKE_SD_HTTP="${3:-200}" FAKE_SD_BODY="${4:-}" \
    service_desk_contract_ok http://candidate-backend http://candidate-service-desk
}

out="$(contract_run 200 '{"contract_version":"2.0"}' 200 '{"status":"ok","contract_version":"2.0"}')"; rc=$?
[ $rc -eq 0 ] && [[ "$out" == *2.0* ]] && ok "backend 2.0 + Service Desk 2.0 -> pass" || bad "compatible contract: rc=$rc out='$out'"
out="$(contract_run 404 '' 200 '{"status":"ok","contract_version":"2.0"}')"; rc=$?
[ $rc -ne 0 ] && ok "missing backend endpoint -> fail" || bad "missing backend endpoint passed"
out="$(contract_run 200 '{"contract_version":"2.0"}' 200 '{"status":"ok"}')"; rc=$?
[ $rc -ne 0 ] && ok "missing Service Desk contract -> fail" || bad "missing SD contract passed"
out="$(contract_run 200 '{"contract_version":"2.0"}' 200 '{"status":"ok","contract_version":"1.7"}')"; rc=$?
[ $rc -ne 0 ] && ok "backend 2.0 + Service Desk 1.x -> fail" || bad "contract mismatch passed"
out="$(contract_run 200 'not-json' 200 '{"status":"ok","contract_version":"2.0"}')"; rc=$?
[ $rc -ne 0 ] && ok "malformed JSON -> fail" || bad "malformed JSON passed"
out="$(contract_run 200 '{"contract_version":"2.0"}' 200 '{"status":"ok","contract_version":"1.0"}')"; rc=$?
[ $rc -ne 0 ] && ok "HTTP 200 but incompatible contract -> fail" || bad "incompatible HTTP 200 passed"

# The gate must no longer depend on a host Next.js build artifact.
grep -q 'BUILD_ID' "$PREDEPLOY" \
    && bad "predeploy_check.sh still references .next/BUILD_ID" \
    || ok "predeploy_check.sh has no .next/BUILD_ID dependency"
grep -q 'service_desk_container_ok nexus-service-desk' "$PREDEPLOY" \
    && ok "the gate calls service_desk_container_ok for the real container" \
    || bad "the gate does not call service_desk_container_ok"
backend_default_count="$(grep -o 'http://127\.0\.0\.1:8000' "$PREDEPLOY" | wc -l)"
[ "$backend_default_count" -eq 1 ] \
    && ok "the Backend loopback default is declared exactly once" \
    || bad "found $backend_default_count duplicated Backend loopback defaults"

printf '\n\033[1m%d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
