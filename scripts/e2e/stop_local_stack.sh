#!/bin/bash
# Tear down a stack started by start_local_stack.sh: kill the backend and
# frontend processes and delete the scratch directory (throwaway database,
# uploads, logs, and generated fixture credentials). Safe to call more than
# once and safe to call even if the stack never fully came up — always call
# this from an `if: always()` (or `finally`) step so cleanup happens on
# failure too.
#
# Usage: scripts/e2e/stop_local_stack.sh [scratch_dir]
#   scratch_dir defaults to the value start_local_stack.sh recorded in
#   <repo_root>/.e2e-stack-dir.

set +e  # best-effort cleanup — one failure must not skip the rest

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATE_FILE="$REPO_ROOT/.e2e-stack-dir"

SCRATCH_DIR="${1:-}"
if [[ -z "$SCRATCH_DIR" && -f "$STATE_FILE" ]]; then
    SCRATCH_DIR="$(cat "$STATE_FILE")"
fi

if [[ -z "$SCRATCH_DIR" ]]; then
    echo "No scratch dir given and none recorded in $STATE_FILE — nothing to stop."
    exit 0
fi

for pid_file in "$SCRATCH_DIR/backend.pid" "$SCRATCH_DIR/frontend.pid" "$SCRATCH_DIR/service-desk.pid"; do
    if [[ -f "$pid_file" ]]; then
        pid="$(cat "$pid_file")"
        if kill -0 "$pid" 2>/dev/null; then
            # setsid gave each process its own group; kill the group so
            # `npm run dev`'s child vite process goes down too.
            kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
            sleep 1
            kill -KILL "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
        fi
    fi
done

# Extra safety net in case a pid file was missing or stale.
pkill -f "uvicorn app.main:app --host 127.0.0.1 --port ${E2E_BACKEND_PORT:-8011}" 2>/dev/null
pkill -f "vite --port ${E2E_FRONTEND_PORT:-5173}" 2>/dev/null
pkill -f "next dev.*--port ${E2E_SERVICE_DESK_PORT:-3001}" 2>/dev/null

rm -rf "$SCRATCH_DIR"
rm -f "$STATE_FILE"

echo "Stopped local e2e stack and removed $SCRATCH_DIR"
