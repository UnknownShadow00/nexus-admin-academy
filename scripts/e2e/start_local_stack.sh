#!/bin/bash
# Stand up an isolated backend + frontend pair for Playwright browser tests:
# a throwaway SQLite database (fresh migrate + seed), non-production ports,
# and disposable fixture accounts with passwords generated for this run only.
# Never reads or writes the real backend/nexus.db or backend/.env.
#
# Usage: scripts/e2e/start_local_stack.sh [scratch_dir]
#   scratch_dir defaults to a fresh mktemp -d.
#
# On success, prints `export` lines for the NEXUS_E2E_* variables the
# Playwright specs read, and writes the same to <scratch_dir>/stack.env.
# When running under GitHub Actions ($GITHUB_ENV set), also appends them
# there so later steps in the same job pick them up automatically.
#
# Pair with scripts/e2e/stop_local_stack.sh <scratch_dir> to tear down —
# call it even if this script or the tests fail.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"

SCRATCH_DIR="${1:-$(mktemp -d -t nexus-e2e-XXXXXX)}"
mkdir -p "$SCRATCH_DIR/uploads"

BACKEND_PORT="${E2E_BACKEND_PORT:-8011}"
FRONTEND_PORT="${E2E_FRONTEND_PORT:-5173}"
SERVICE_DESK_PORT="${E2E_SERVICE_DESK_PORT:-3001}"
BACKEND_HOST="127.0.0.1"
FRONTEND_HOST="127.0.0.1"
SERVICE_DESK_DIR="$REPO_ROOT/service-desk-app"
API_BASE="http://$BACKEND_HOST:$BACKEND_PORT"

rand() { openssl rand -hex 16; }

# Fixture credentials generated fresh for this run — never hard-coded, never logged.
ADMIN_USERNAME_GEN="browser-admin"
ADMIN_PASSWORD_GEN="$(rand)"
STUDENT_USERNAME_GEN="browser-training-student"
STUDENT_PASSWORD_GEN="$(rand)"
QUALIFIED_USERNAME_GEN="browser-qualified-student"
QUALIFIED_PASSWORD_GEN="$(rand)"
STUDENT_C_USERNAME_GEN="browser-training-student-c"
STUDENT_C_PASSWORD_GEN="$(rand)"
STUDENT_D_USERNAME_GEN="browser-training-student-d"
STUDENT_D_PASSWORD_GEN="$(rand)"
FRESH_A_USERNAME_GEN="browser-fresh-student-a"
FRESH_A_PASSWORD_GEN="$(rand)"
FRESH_B_USERNAME_GEN="browser-fresh-student-b"
FRESH_B_PASSWORD_GEN="$(rand)"

export DATABASE_URL="sqlite:///$SCRATCH_DIR/e2e.db"
export JWT_SECRET_KEY="$(rand)$(rand)"
export JWT_ALGORITHM=HS256
export JWT_EXPIRE_MINUTES=1440
export ADMIN_USERNAME="$ADMIN_USERNAME_GEN"
export ADMIN_PASSWORD="$ADMIN_PASSWORD_GEN"
export ADMIN_API_KEY="$(rand)"
export ADMIN_SECRET_KEY="$(rand)"
export CORS_ORIGINS="http://$FRONTEND_HOST:$FRONTEND_PORT"
export UPLOAD_DIR="$SCRATCH_DIR/uploads"
export APP_LOG_PATH="$SCRATCH_DIR/app.log"
export COOKIE_SECURE=false
export AI_ENABLED=false
export SEED_PASSWORD_MENTOR="$(rand)"
export SEED_PASSWORD_SHAK="$(rand)"
export SEED_PASSWORD_RAKIB="$(rand)"
export SEED_PASSWORD_AHMED="$(rand)"
export SEED_PASSWORD_EMRAN="$(rand)"
export SEED_PASSWORD_WALO="$(rand)"
export SEED_PASSWORD_HUDAYFA="$(rand)"

echo "== Seeding throwaway database at $DATABASE_URL =="
bash "$REPO_ROOT/scripts/e2e/seed_fresh_db.sh"

if [[ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
    UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
else
    UVICORN="uvicorn"
fi

echo "== Starting isolated backend on $BACKEND_HOST:$BACKEND_PORT =="
(
    cd "$BACKEND_DIR"
    setsid "$UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
        > "$SCRATCH_DIR/uvicorn.log" 2>&1 < /dev/null &
    echo $! > "$SCRATCH_DIR/backend.pid"
)

echo "== Waiting for backend health =="
for _ in $(seq 1 30); do
    if curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/health" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done
if ! curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo "Backend did not become healthy in time. Log:" >&2
    cat "$SCRATCH_DIR/uvicorn.log" >&2 || true
    exit 1
fi

echo "== Starting isolated frontend on $FRONTEND_HOST:$FRONTEND_PORT =="
echo "== Starting isolated Service Desk on $BACKEND_HOST:$SERVICE_DESK_PORT =="
(
    cd "$SERVICE_DESK_DIR"
    NEXUS_INTEGRATION=1 NEXT_PUBLIC_NEXUS_INTEGRATION=1 \
    SERVICE_DESK_BASE_PATH=/service-desk NEXT_PUBLIC_BASE_PATH=/service-desk \
    JWT_SECRET_KEY="$JWT_SECRET_KEY" JWT_ALGORITHM="$JWT_ALGORITHM" \
    NEXUS_ADMIN_CHECK_URL="$API_BASE" \
    setsid pnpm --filter @service-desk/web exec next dev --hostname "$BACKEND_HOST" --port "$SERVICE_DESK_PORT" \
        > "$SCRATCH_DIR/service-desk.log" 2>&1 < /dev/null &
    echo $! > "$SCRATCH_DIR/service-desk.pid"
)
for _ in $(seq 1 45); do
    if curl -sf "http://$BACKEND_HOST:$SERVICE_DESK_PORT/service-desk/api/health" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done
if ! curl -sf "http://$BACKEND_HOST:$SERVICE_DESK_PORT/service-desk/api/health" > /dev/null 2>&1; then
    echo "Service Desk did not become ready in time. Log:" >&2
    cat "$SCRATCH_DIR/service-desk.log" >&2 || true
    exit 1
fi

(
    cd "$FRONTEND_DIR"
    E2E_API_PROXY_URL="http://$BACKEND_HOST:$BACKEND_PORT" \
    E2E_SERVICE_DESK_URL="http://$BACKEND_HOST:$SERVICE_DESK_PORT" \
    VITE_API_URL="http://$BACKEND_HOST:$BACKEND_PORT" setsid npm run dev -- \
        --port "$FRONTEND_PORT" --host "$FRONTEND_HOST" \
        > "$SCRATCH_DIR/vite.log" 2>&1 < /dev/null &
    echo $! > "$SCRATCH_DIR/frontend.pid"
)

echo "== Waiting for frontend =="
for _ in $(seq 1 30); do
    if curl -sf "http://$FRONTEND_HOST:$FRONTEND_PORT/" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done
if ! curl -sf "http://$FRONTEND_HOST:$FRONTEND_PORT/" > /dev/null 2>&1; then
    echo "Frontend did not become ready in time. Log:" >&2
    cat "$SCRATCH_DIR/vite.log" >&2 || true
    exit 1
fi

echo "== Creating fixture student accounts =="
ADMIN_COOKIES="$SCRATCH_DIR/admin_cookies.txt"
curl -sf -c "$ADMIN_COOKIES" -X POST "$API_BASE/api/admin/session/login" \
    -H "Content-Type: application/json" -H "Origin: http://$FRONTEND_HOST:$FRONTEND_PORT" \
    -d "{\"username\":\"$ADMIN_USERNAME_GEN\",\"password\":\"$ADMIN_PASSWORD_GEN\"}" > /dev/null

create_student() {
    local username="$1" password="$2" label="$3"
    curl -sf -b "$ADMIN_COOKIES" -X POST "$API_BASE/api/admin/students" \
        -H "Content-Type: application/json" -H "Origin: http://$FRONTEND_HOST:$FRONTEND_PORT" \
        -H "Referer: http://$FRONTEND_HOST:$FRONTEND_PORT/admin/students" \
        -d "{\"name\":\"$label\",\"email\":\"$username@example.invalid\",\"username\":\"$username\",\"password\":\"$password\"}" \
        > /dev/null
}

create_student "$STUDENT_USERNAME_GEN" "$STUDENT_PASSWORD_GEN" "Browser Training Student"
create_student "$QUALIFIED_USERNAME_GEN" "$QUALIFIED_PASSWORD_GEN" "Qualified Browser Student"
create_student "$STUDENT_C_USERNAME_GEN" "$STUDENT_C_PASSWORD_GEN" "Browser Training Student C"
create_student "$STUDENT_D_USERNAME_GEN" "$STUDENT_D_PASSWORD_GEN" "Browser Training Student D"
create_student "$FRESH_A_USERNAME_GEN" "$FRESH_A_PASSWORD_GEN" "Fresh Progression Student A"
create_student "$FRESH_B_USERNAME_GEN" "$FRESH_B_PASSWORD_GEN" "Fresh Progression Student B"

# There is no admin API for directly granting a role — promotion is normally
# earned by completing gates. For the capstone-visibility fixture we grant a
# role directly in the throwaway database (role id 2 = Support Technician I,
# rank 2 — enough to see at least one published capstone). This only ever
# touches the scratch database created above, never production.
if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    PYTHON="$BACKEND_DIR/.venv/bin/python"
else
    PYTHON="python"
fi
"$PYTHON" - "$SCRATCH_DIR/e2e.db" "$QUALIFIED_USERNAME_GEN" <<'PY'
import sqlite3
import sys

db_path, username = sys.argv[1], sys.argv[2]
db = sqlite3.connect(db_path)
row = db.execute("SELECT id FROM students WHERE username = ?", (username,)).fetchone()
if row:
    db.execute("INSERT INTO student_roles (student_id, role_id) VALUES (?, 2)", (row[0],))
    db.commit()
PY

# Give each disposable browser account the published Service Desk fixtures.
# The four long-running simulator integration fixtures intentionally omit one
# Starter Support assignment. That is the documented instructor-assignment
# override path, preserving broad tool-workflow coverage without manufacturing
# course completions. The two fresh fixtures receive the complete catalog and
# therefore exercise the real server-authoritative pack progression.
"$PYTHON" - "$SCRATCH_DIR/e2e.db" "$STUDENT_USERNAME_GEN" "$QUALIFIED_USERNAME_GEN" "$STUDENT_C_USERNAME_GEN" "$STUDENT_D_USERNAME_GEN" <<'PY'
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
scenario_ids = [
    row[0]
    for row in db.execute(
        "SELECT id FROM service_desk_scenarios "
        "WHERE status = 'active' AND stable_key LIKE 'inc%' AND stable_key != 'inc2502'"
    )
]
for username in sys.argv[2:]:
    row = db.execute("SELECT id FROM students WHERE username = ?", (username,)).fetchone()
    if row:
        db.execute(
            "DELETE FROM service_desk_assignments WHERE student_id = ? AND scenario_id IN "
            "(SELECT id FROM service_desk_scenarios WHERE stable_key = 'inc2502')",
            (row[0],),
        )
        for scenario_id in scenario_ids:
            db.execute(
                "INSERT INTO service_desk_assignments (student_id, scenario_id, mode, is_required, assigned_by) "
                "SELECT ?, ?, 'simulation', 1, 'e2e' WHERE NOT EXISTS "
                "(SELECT 1 FROM service_desk_assignments WHERE student_id = ? AND scenario_id = ? AND mode = 'simulation')",
                (row[0], scenario_id, row[0], scenario_id),
            )
db.commit()
PY

"$PYTHON" - "$SCRATCH_DIR/e2e.db" "$FRESH_A_USERNAME_GEN" "$FRESH_B_USERNAME_GEN" <<'PY'
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
scenario_ids = [
    row[0]
    for row in db.execute(
        "SELECT id FROM service_desk_scenarios WHERE status = 'active' AND stable_key LIKE 'inc%'"
    )
]
for username in sys.argv[2:]:
    row = db.execute("SELECT id FROM students WHERE username = ?", (username,)).fetchone()
    if row:
        for scenario_id in scenario_ids:
            db.execute(
                "INSERT INTO service_desk_assignments (student_id, scenario_id, mode, is_required, assigned_by) "
                "SELECT ?, ?, 'simulation', 1, 'e2e-progression' WHERE NOT EXISTS "
                "(SELECT 1 FROM service_desk_assignments WHERE student_id = ? AND scenario_id = ? AND mode = 'simulation')",
                (row[0], scenario_id, row[0], scenario_id),
            )
db.commit()
PY

# The health endpoint is a separate Next.js route and does not compile the
# authenticated queue page. Warm the real route through the same Vite proxy
# the browser uses so "Local stack ready" means the cross-app page can render,
# not merely that the Service Desk process is listening.
echo "== Warming Service Desk application route =="
STUDENT_COOKIES="$SCRATCH_DIR/student_cookies.txt"
curl -sf --max-time 15 -c "$STUDENT_COOKIES" -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" -H "Origin: http://$FRONTEND_HOST:$FRONTEND_PORT" \
    -d "{\"username\":\"$STUDENT_USERNAME_GEN\",\"password\":\"$STUDENT_PASSWORD_GEN\"}" \
    > /dev/null
if ! SERVICE_DESK_STATUS="$(curl -sS --max-time 45 -b "$STUDENT_COOKIES" -o /dev/null -w '%{http_code}' \
    "http://$FRONTEND_HOST:$FRONTEND_PORT/service-desk")"; then
    echo "Service Desk application route did not respond in time. Logs:" >&2
    cat "$SCRATCH_DIR/service-desk.log" >&2 || true
    cat "$SCRATCH_DIR/vite.log" >&2 || true
    exit 1
fi
if [[ "$SERVICE_DESK_STATUS" != "200" ]]; then
    echo "Service Desk application route did not become ready (HTTP $SERVICE_DESK_STATUS). Logs:" >&2
    cat "$SCRATCH_DIR/service-desk.log" >&2 || true
    cat "$SCRATCH_DIR/vite.log" >&2 || true
    exit 1
fi

STACK_ENV="$SCRATCH_DIR/stack.env"
{
    echo "NEXUS_E2E_BASE_URL=http://$FRONTEND_HOST:$FRONTEND_PORT"
    echo "NEXUS_E2E_API_URL=$API_BASE"
    echo "NEXUS_E2E_ADMIN_USERNAME=$ADMIN_USERNAME_GEN"
    echo "NEXUS_E2E_ADMIN_PASSWORD=$ADMIN_PASSWORD_GEN"
    echo "NEXUS_E2E_STUDENT_USERNAME=$STUDENT_USERNAME_GEN"
    echo "NEXUS_E2E_STUDENT_PASSWORD=$STUDENT_PASSWORD_GEN"
    echo "NEXUS_E2E_STUDENT_A_USERNAME=$STUDENT_USERNAME_GEN"
    echo "NEXUS_E2E_STUDENT_A_PASSWORD=$STUDENT_PASSWORD_GEN"
    echo "NEXUS_E2E_STUDENT_B_USERNAME=$QUALIFIED_USERNAME_GEN"
    echo "NEXUS_E2E_STUDENT_B_PASSWORD=$QUALIFIED_PASSWORD_GEN"
    echo "NEXUS_E2E_STUDENT_C_USERNAME=$STUDENT_C_USERNAME_GEN"
    echo "NEXUS_E2E_STUDENT_C_PASSWORD=$STUDENT_C_PASSWORD_GEN"
    echo "NEXUS_E2E_STUDENT_D_USERNAME=$STUDENT_D_USERNAME_GEN"
    echo "NEXUS_E2E_STUDENT_D_PASSWORD=$STUDENT_D_PASSWORD_GEN"
    echo "NEXUS_E2E_FRESH_A_USERNAME=$FRESH_A_USERNAME_GEN"
    echo "NEXUS_E2E_FRESH_A_PASSWORD=$FRESH_A_PASSWORD_GEN"
    echo "NEXUS_E2E_FRESH_B_USERNAME=$FRESH_B_USERNAME_GEN"
    echo "NEXUS_E2E_FRESH_B_PASSWORD=$FRESH_B_PASSWORD_GEN"
    echo "NEXUS_E2E_QUALIFIED_USERNAME=$QUALIFIED_USERNAME_GEN"
    echo "NEXUS_E2E_QUALIFIED_PASSWORD=$QUALIFIED_PASSWORD_GEN"
} > "$STACK_ENV"
chmod 600 "$STACK_ENV"

echo "$SCRATCH_DIR" > "$REPO_ROOT/.e2e-stack-dir"

if [[ -n "${GITHUB_ENV:-}" ]]; then
    cat "$STACK_ENV" >> "$GITHUB_ENV"
fi

echo "== Local stack ready =="
echo "scratch dir: $SCRATCH_DIR"
echo "backend:     $API_BASE (pid $(cat "$SCRATCH_DIR/backend.pid"))"
echo "frontend:    http://$FRONTEND_HOST:$FRONTEND_PORT (pid $(cat "$SCRATCH_DIR/frontend.pid"))"
echo "env file:    $STACK_ENV (contains generated fixture passwords — not logged above)"
echo "Tear down with: scripts/e2e/stop_local_stack.sh $SCRATCH_DIR"
