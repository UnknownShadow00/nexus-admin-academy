#!/usr/bin/env bash
# Read-only operator status for the Nexus V2 pilot.
#
# For a cohort of five to ten students, this is the whole monitoring story —
# no Prometheus, no Grafana, no agent. One command, one screen, nothing
# mutated: every database read opens SQLite read-only, and every probe is a
# GET or a `systemctl is-active`.
#
# It degrades instead of failing. Run it on a laptop with no systemd, no
# Docker, and no running backend and it prints SKIP rows with reasons and
# still exits 0. A non-zero exit means the script itself broke, never that a
# service is down — read the rows for that.
#
#   scripts/pilot_status.sh
#   scripts/pilot_status.sh --db /path/to/copy.db
#   scripts/pilot_status.sh --json
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
ENV_FILE="${NEXUS_ENV_FILE:-$BACKEND_DIR/.env}"
PYTHON="${NEXUS_PYTHON:-$BACKEND_DIR/.venv/bin/python}"
if [ -z "${NEXUS_PYTHON:-}" ] && [ ! -x "$PYTHON" ] && command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
fi
BACKUP_DIR="${NEXUS_BACKUP_DIR:-$HOME/backups/nexus}"
BACKEND_URL="${NEXUS_BACKEND_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${NEXUS_FRONTEND_URL:-http://127.0.0.1:80}"
SERVICE_DESK_URL="${NEXUS_SERVICE_DESK_URL:-http://127.0.0.1:13000}"
BACKEND_UNIT="${NEXUS_BACKEND_UNIT:-nexus-admin-academy.service}"
WORKER_TIMER="${NEXUS_WORKER_TIMER:-nexus-grading-worker.timer}"

DB_PATH=""
AS_JSON=0

usage() {
    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --db) DB_PATH="${2:-}"; shift 2 ;;
        --json) AS_JSON=1; shift ;;
        -h|--help) usage ;;
        *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
done

ROWS=()

row() { # name | status | detail
    ROWS+=("$1"$'\t'"$2"$'\t'"$3")
}

# Read one key from the env file without ever echoing the file itself.
# The env file may have CRLF line endings, so strip the carriage return —
# a trailing \r silently turns a valid path into a missing one.
env_value() {
    [ -r "$ENV_FILE" ] || return 1
    sed -n "s/^[[:space:]]*$1=//p" "$ENV_FILE" \
        | tail -n1 | tr -d '\r' \
        | sed 's/^"//; s/"$//; s/^'"'"'//; s/'"'"'$//'
}

# ---------------------------------------------------------------------------
# Resolve the database, read-only
# ---------------------------------------------------------------------------
if [ -z "$DB_PATH" ]; then
    DB_URL="$(env_value DATABASE_URL || true)"
    case "$DB_URL" in
        sqlite:////*) DB_PATH="/${DB_URL#sqlite:////}" ;;
        sqlite:///./*) DB_PATH="$BACKEND_DIR/${DB_URL#sqlite:///./}" ;;
        sqlite:///*) DB_PATH="${DB_URL#sqlite:///}" ;;
        *) DB_PATH="$BACKEND_DIR/nexus.db" ;;
    esac
fi

DB_READY=0
if [ ! -f "$DB_PATH" ]; then
    row "database" "SKIP" "not found: $DB_PATH"
elif [ ! -x "$PYTHON" ]; then
    row "database" "SKIP" "no interpreter at $PYTHON"
else
    DB_READY=1
    row "database" "OK" "$DB_PATH"
fi

# One SELECT, opened read-only. The sqlite3 CLI is not installed on the
# deployment host, so this uses Python's sqlite3 with a mode=ro URI: the file
# cannot be modified even by accident. A missing table yields SKIP, not an
# error, so this works against older copies too.
query() {
    [ "$DB_READY" -eq 1 ] || { printf 'SKIP\tdatabase unavailable'; return; }
    NEXUS_SQL="$1" NEXUS_DB="$DB_PATH" "$PYTHON" - <<'PY'
import os, sqlite3, sys
try:
    conn = sqlite3.connect(f"file:{os.environ['NEXUS_DB']}?mode=ro", uri=True, timeout=5)
    row = conn.execute(os.environ["NEXUS_SQL"]).fetchone()
    conn.close()
    sys.stdout.write("OK\t" + ("" if row is None or row[0] is None else str(row[0])))
except sqlite3.OperationalError as exc:
    sys.stdout.write("SKIP\t" + str(exc))
except Exception as exc:
    sys.stdout.write("SKIP\t" + str(exc))
PY
}

count_row() { # label | sql
    local out status detail
    out="$(query "$2")"
    status="${out%%$'\t'*}"
    detail="${out#*$'\t'}"
    if [ "$status" = "OK" ]; then
        row "$1" "OK" "$detail"
    else
        row "$1" "SKIP" "$detail"
    fi
}

# ---------------------------------------------------------------------------
# Health probes
# ---------------------------------------------------------------------------
probe() { # label | url
    if ! command -v curl >/dev/null 2>&1; then
        row "$1" "SKIP" "curl unavailable"
    elif curl --fail --silent --show-error --max-time 5 "$2" >/dev/null 2>&1; then
        row "$1" "UP" "$2"
    else
        row "$1" "DOWN" "$2"
    fi
}

probe "backend health" "$BACKEND_URL/health"
probe "frontend" "$FRONTEND_URL/"
probe "service desk health" "$SERVICE_DESK_URL/service-desk/api/health"

# Deployment expectation: only nginx is public. These are diagnostics only;
# the status command never changes a listener or firewall rule.
if command -v ss >/dev/null 2>&1; then
    LISTENERS="$(ss -ltnH 2>/dev/null || true)"
    if printf '%s\n' "$LISTENERS" | awk '$4 ~ /^(0\.0\.0\.0|\*|\[::\]|::):8000$/ {found=1} END {exit !found}'; then
        row "backend network exposure" "WARN" "port 8000 is wildcard-bound; production should use nginx only"
    else
        row "backend network exposure" "OK" "not listening on 0.0.0.0:8000"
    fi
    EXPOSED_STAGING="$(printf '%s\n' "$LISTENERS" | awk '$4 ~ /^(0\.0\.0\.0|\*|\[::\]|::):(3000|13000|18000|18080|18081)$/ {print $4}' | paste -sd, -)"
    if [ -n "$EXPOSED_STAGING" ]; then
        row "staging/bypass exposure" "WARN" "$EXPOSED_STAGING externally bound; production should expose nginx only"
    else
        row "staging/bypass exposure" "OK" "no known staging or Service Desk bypass port externally bound"
    fi
else
    row "backend network exposure" "SKIP" "ss unavailable"
    row "staging/bypass exposure" "SKIP" "ss unavailable"
fi

if ! command -v docker >/dev/null 2>&1; then
    row "Docker" "SKIP" "docker unavailable"
elif ! docker info >/dev/null 2>&1; then
    row "Docker" "SKIP" "daemon unavailable"
elif docker inspect nexus-service-desk >/dev/null 2>&1; then
    SD_STATE="$(docker inspect --format '{{.State.Status}}' nexus-service-desk 2>/dev/null || true)"
    row "Service Desk container" "${SD_STATE:-unknown}" "nexus-service-desk"
else
    row "Service Desk container" "SKIP" "nexus-service-desk is absent"
fi

unit_state() { # label | unit
    if ! command -v systemctl >/dev/null 2>&1; then
        row "$1" "SKIP" "systemd unavailable"
        return
    fi
    if ! systemctl cat "$2" >/dev/null 2>&1; then
        row "$1" "SKIP" "$2 is not installed"
        return
    fi
    row "$1" "$(systemctl is-active "$2" 2>/dev/null || echo unknown)" "$2"
}

unit_state "backend service" "$BACKEND_UNIT"
unit_state "grading timer" "$WORKER_TIMER"

if command -v systemctl >/dev/null 2>&1 && systemctl cat "$WORKER_TIMER" >/dev/null 2>&1; then
    NEXT="$(systemctl list-timers --all --no-pager "$WORKER_TIMER" 2>/dev/null | sed -n '2p' | tr -s ' ' | cut -d' ' -f1-3)"
    row "grading timer next run" "OK" "${NEXT:-unknown}"
fi

# ---------------------------------------------------------------------------
# Host
# ---------------------------------------------------------------------------
AVAIL_KB="$(df -Pk "$REPO_ROOT" 2>/dev/null | awk 'NR==2 {print $4}')"
if [ -n "${AVAIL_KB:-}" ]; then
    AVAIL_GIB="$(awk -v kb="$AVAIL_KB" 'BEGIN {printf "%.1f", kb/1048576}')"
    if [ "$AVAIL_KB" -lt 2097152 ]; then DISK_STATUS="CRITICAL"
    elif [ "$AVAIL_KB" -lt 4194304 ]; then DISK_STATUS="LOW"
    else DISK_STATUS="OK"; fi
    row "disk free" "$DISK_STATUS" "${AVAIL_GIB} GiB"
else
    row "disk free" "SKIP" "df unavailable"
fi

# ---------------------------------------------------------------------------
# Configuration (never print secrets or student ids)
# ---------------------------------------------------------------------------
if [ -r "$ENV_FILE" ]; then
    MASTER="$(env_value V2_CURRICULUM_ENABLED || true)"
    row "V2 master flag" "OK" "${MASTER:-unset (off)}"
    ALLOWLIST="$(env_value V2_PILOT_STUDENT_IDS || true)"
    # Count unique positive integer ids without importing the backend. This
    # keeps configuration status available in a clean checkout or during a
    # virtualenv repair, and never prints the ids themselves.
    PILOT_COUNT="$(
        printf '%s\n' "${ALLOWLIST:-}" | awk 'BEGIN { RS = "[,;[:space:]]+" }
            $0 ~ /^[0-9]+$/ && $0 + 0 > 0 { seen[$0 + 0] = 1 }
            END { print length(seen) }
        '
    )"
    row "pilot students enrolled" "OK" "${PILOT_COUNT:-0}"
else
    row "V2 master flag" "SKIP" "environment file unreadable"
    row "pilot students enrolled" "SKIP" "environment file unreadable"
fi

count_row "alembic revision" "SELECT version_num FROM alembic_version"

# ---------------------------------------------------------------------------
# Queues and activity
# ---------------------------------------------------------------------------
count_row "pending grading jobs" \
    "SELECT COUNT(*) FROM pending_grades WHERE status='pending'"
count_row "stale pending jobs (>30m)" \
    "SELECT COUNT(*) FROM pending_grades WHERE status='pending' AND created_at < datetime('now','-30 minutes')"
count_row "stale processing leases (>10m)" \
    "SELECT COUNT(*) FROM pending_grades WHERE status='processing' AND (claimed_at IS NULL OR claimed_at < datetime('now','-10 minutes'))"
count_row "service desk attempts in progress" \
    "SELECT COUNT(*) FROM service_desk_attempts WHERE status='in_progress'"
count_row "service desk attempts failed (24h)" \
    "SELECT COUNT(*) FROM service_desk_attempts WHERE status='failed' AND updated_at > datetime('now','-1 day')"
count_row "V2 activity (24h)" \
    "SELECT COUNT(*) FROM v2_module_activity WHERE updated_at > datetime('now','-1 day')"

# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
if [ -d "$BACKUP_DIR" ]; then
    NEWEST="$(find "$BACKUP_DIR" -maxdepth 1 -name '*.db.gz' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n1)"
    if [ -n "$NEWEST" ]; then
        AGE_H="$(awk -v t="${NEWEST%% *}" 'BEGIN {printf "%.1f", (systime()-t)/3600}')"
        BSTATUS="OK"
        awk -v a="$AGE_H" 'BEGIN {exit !(a > 48)}' && BSTATUS="STALE"
        row "latest backup age" "$BSTATUS" "${AGE_H}h — $(basename "${NEWEST#* }")"
    else
        row "latest backup age" "SKIP" "no *.db.gz in $BACKUP_DIR"
    fi
else
    row "latest backup age" "SKIP" "no backup directory at $BACKUP_DIR"
fi

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
if [ "$AS_JSON" -eq 1 ]; then
    json_escape() {
        local value="$1"
        value="${value//\\/\\\\}"
        value="${value//\"/\\\"}"
        value="${value//$'\n'/\\n}"
        value="${value//$'\r'/\\r}"
        value="${value//$'\t'/\\t}"
        printf '%s' "$value"
    }
    printf '{\n  "rows": [\n'
    for i in "${!ROWS[@]}"; do
        IFS=$'\t' read -r name status detail <<<"${ROWS[$i]}"
        printf '    {"name": "%s", "status": "%s", "detail": "%s"}' \
            "$(json_escape "$name")" "$(json_escape "$status")" "$(json_escape "$detail")"
        [ "$i" -lt $(( ${#ROWS[@]} - 1 )) ] && printf ','
        printf '\n'
    done
    printf '  ]\n}\n'
else
    printf 'Nexus V2 pilot status — %s\n\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
    for entry in "${ROWS[@]}"; do
        IFS=$'\t' read -r name status detail <<<"$entry"
        printf '  %-34s %-9s %s\n' "$name" "$status" "$detail"
    done
    printf '\nRead-only: nothing above was modified.\n'
fi
