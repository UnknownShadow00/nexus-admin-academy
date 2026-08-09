#!/bin/bash
# Run the Service Desk launch browser suite against a new disposable local
# stack. This script never reads or writes production configuration or data.
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_ROOT="$REPO_ROOT/artifacts/e2e-launch-verification"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
SCRATCH_DIR="${E2E_LAUNCH_SCRATCH_DIR:-/tmp/nexus-launch-$RUN_ID}"
LOG_FILE="$ARTIFACT_ROOT/$RUN_ID.log"
STATUS_FILE="$ARTIFACT_ROOT/$RUN_ID.status"

mkdir -p "$ARTIFACT_ROOT"

cleanup() {
    local exit_code=$?
    "$REPO_ROOT/scripts/e2e/stop_local_stack.sh" "$SCRATCH_DIR" >>"$LOG_FILE" 2>&1 || true
    if [[ $exit_code -eq 0 ]]; then
        printf 'PASS\n' >"$STATUS_FILE"
    else
        printf 'FAIL (exit %s)\n' "$exit_code" >"$STATUS_FILE"
        # Playwright keeps traces, screenshots, and error context under
        # frontend/test-results. Do not delete or overwrite that directory.
        printf 'Playwright artifacts retained in %s/frontend/test-results\n' "$REPO_ROOT" >>"$LOG_FILE"
    fi
    exit "$exit_code"
}
trap cleanup EXIT

{
    echo "Launch verification run: $RUN_ID"
    echo "Scratch stack: $SCRATCH_DIR"
    "$REPO_ROOT/scripts/e2e/start_local_stack.sh" "$SCRATCH_DIR"
    set -a
    # Generated disposable credentials are intentionally not echoed.
    source "$SCRATCH_DIR/stack.env"
    set +a
    cd "$REPO_ROOT/frontend"
    npx playwright test tests/e2e/service-desk-integration.spec.js --reporter=line
} 2>&1 | tee "$LOG_FILE"
