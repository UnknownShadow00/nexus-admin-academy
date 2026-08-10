#!/usr/bin/env bash
# Read-only pre-deployment gate for the active systemd + SQLite deployment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_ROOT="$REPO_ROOT/backend"
BACKEND_PYTHON="$BACKEND_ROOT/.venv/bin/python"
ENV_FILE="${NEXUS_ENV_FILE:-$BACKEND_ROOT/.env}"
FAILED=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; FAILED=1; }
info() { printf 'INFO: %s\n' "$1"; }
read_env_value() {
    python3 - "$ENV_FILE" "$1" <<'PY'
import sys
from pathlib import Path

key = sys.argv[2]
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if line and not line.startswith("#") and "=" in line:
        name, value = line.split("=", 1)
        if name.strip() == key:
            print(value.strip().strip('"').strip("'"))
            break
PY
}

cd "$REPO_ROOT"
info "branch $(git branch --show-current) at $(git rev-parse --short=12 HEAD)"
if [ -z "$(git status --porcelain)" ]; then pass "working tree is clean"; else fail "working tree is not clean"; fi

if [ -f "$ENV_FILE" ]; then
    pass "production environment file exists"
else
    fail "production environment file is missing"
fi

if [ -f "$ENV_FILE" ]; then
    if python3 - "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlsplit

values = {}
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip('"').strip("'")

errors = []
required = ("ADMIN_USERNAME", "ADMIN_PASSWORD", "ADMIN_API_KEY", "DATABASE_URL", "UPLOAD_DIR", "APP_LOG_PATH")
for key in required:
    if not values.get(key):
        errors.append(f"{key} is missing")

if values.get("APP_ENV", "").lower() not in {"production", "prod"}:
    errors.append("APP_ENV must be production")
secret = values.get("JWT_SECRET_KEY", "")
if len(secret) < 32 or secret.lower().startswith(("change_this", "replace-with", "changeme")):
    errors.append("JWT_SECRET_KEY is missing, too short, or a placeholder")
if values.get("JWT_ALGORITHM") not in {"HS256", "HS384", "HS512"}:
    errors.append("JWT_ALGORITHM is invalid")
if values.get("COOKIE_SECURE", "").lower() not in {"1", "true", "yes", "on"}:
    errors.append("COOKIE_SECURE must be true")
if len(values.get("ADMIN_PASSWORD", "")) < 14:
    errors.append("ADMIN_PASSWORD must be at least 14 characters")
if len(values.get("ADMIN_API_KEY", "")) < 32:
    errors.append("ADMIN_API_KEY must be at least 32 characters")
seed_keys = (
    "SEED_PASSWORD_MENTOR", "SEED_PASSWORD_SHAK", "SEED_PASSWORD_RAKIB",
    "SEED_PASSWORD_AHMED", "SEED_PASSWORD_EMRAN", "SEED_PASSWORD_WALO",
    "SEED_PASSWORD_HUDAYFA",
)
if any(len(values.get(key, "")) < 14 for key in seed_keys):
    errors.append("all SEED_PASSWORD_* values must be at least 14 characters")

def origin(value):
    parsed = urlsplit(value.strip().rstrip("/"))
    return f"{parsed.scheme}://{parsed.netloc}".lower() if parsed.scheme and parsed.netloc else None

frontend = origin(values.get("FRONTEND_URL", ""))
cors = [origin(item) for item in values.get("CORS_ORIGINS", "").split(",") if item.strip()]
if not frontend or not frontend.startswith("https://"):
    errors.append("FRONTEND_URL must be one HTTPS origin")
if not cors or any(item is None or not item.startswith("https://") for item in cors):
    errors.append("CORS_ORIGINS must contain only HTTPS origins")
if frontend and frontend not in cors:
    errors.append("FRONTEND_URL must be present in CORS_ORIGINS")
if any("localhost" in (item or "") or "127.0.0.1" in (item or "") or "examcompass.com" in (item or "") for item in cors):
    errors.append("CORS_ORIGINS contains a development or ExamCompass origin")

for error in errors:
    print(f"FAIL: {error}", file=sys.stderr)
raise SystemExit(1 if errors else 0)
PY
    then
        pass "production environment values pass format and origin checks"
    else
        FAILED=1
    fi
fi

for command in python3 gzip tar docker curl; do
    if command -v "$command" >/dev/null 2>&1; then pass "$command is available"; else fail "$command is unavailable"; fi
done
if [ -x "$BACKEND_PYTHON" ]; then pass "backend virtual environment is available"; else fail "backend virtual environment is missing"; fi
if [ -x "$REPO_ROOT/scripts/backup_sqlite.sh" ]; then pass "SQLite backup script is executable"; else fail "SQLite backup script is not executable"; fi

if [ -x "$BACKEND_PYTHON" ]; then
    # Use the venv interpreter as a module from backend/. Unlike the generated
    # console-script entry point, this puts backend/ on sys.path while Alembic
    # loads revision modules for commands such as `heads` and `history`.
    if HEADS_OUTPUT="$(cd "$BACKEND_ROOT" && "$BACKEND_PYTHON" -m alembic heads)"; then
        HEADS="$(printf '%s\n' "$HEADS_OUTPUT" | awk 'NF {print $1}')"
        HEAD_COUNT="$(printf '%s\n' "$HEADS" | sed '/^$/d' | wc -l)"
        if [ "$HEAD_COUNT" -eq 1 ]; then
            HEAD="$(printf '%s\n' "$HEADS" | head -n 1)"
            pass "Alembic has one head: $HEAD"
        else
            fail "Alembic does not have exactly one head"
        fi
    else
        fail "Alembic could not load migration heads"
    fi

    if CURRENT_OUTPUT="$(cd "$BACKEND_ROOT" && "$BACKEND_PYTHON" -m alembic current)"; then
        CURRENT="$(printf '%s\n' "$CURRENT_OUTPUT" | awk 'NF {print $1}')"
        CURRENT_COUNT="$(printf '%s\n' "$CURRENT" | sed '/^$/d' | wc -l)"
        if [ "$CURRENT_COUNT" -ne 1 ]; then
            fail "database does not have exactly one current Alembic revision"
        fi
    else
        fail "Alembic could not read the current database revision"
    fi

    if [ "${HEAD_COUNT:-0}" -eq 1 ] && [ "${CURRENT_COUNT:-0}" -eq 1 ]; then
        if [ "$CURRENT" = "$HEAD" ]; then
            pass "database revision matches Alembic head: $CURRENT"
        elif (cd "$BACKEND_ROOT" && "$BACKEND_PYTHON" -m alembic history -r "$CURRENT:$HEAD" >/dev/null); then
            pass "database revision $CURRENT is a valid ancestor of head $HEAD"
        else
            fail "database revision $CURRENT is not a valid ancestor of head $HEAD"
        fi
    fi
fi

AVAILABLE_KB="$(df -Pk "$REPO_ROOT" | awk 'NR==2 {print $4}')"
if [ "$AVAILABLE_KB" -ge 2097152 ]; then pass "at least 2 GiB of disk space is available"; else fail "less than 2 GiB of disk space is available"; fi

if [ -f "$REPO_ROOT/frontend/dist/index.html" ]; then pass "frontend production build exists"; else fail "frontend production build is missing"; fi
if [ -f "$REPO_ROOT/service-desk-app/apps/web/.next/BUILD_ID" ]; then pass "Service Desk production build exists"; else fail "Service Desk production build is missing"; fi

if docker inspect nexus-frontend >/dev/null 2>&1 && docker exec nexus-frontend nginx -t >/dev/null 2>&1; then pass "live nginx configuration syntax is valid"; else fail "live nginx container/configuration is unavailable or invalid"; fi
if docker inspect nexus-service-desk >/dev/null 2>&1; then
    pass "Service Desk container exists"
    if [ -f "$ENV_FILE" ]; then
        BACKEND_JWT_SECRET="$(read_env_value JWT_SECRET_KEY)"
        BACKEND_JWT_ALGORITHM="$(read_env_value JWT_ALGORITHM)"
        SERVICE_DESK_JWT_SECRET="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' nexus-service-desk | sed -n 's/^JWT_SECRET_KEY=//p' | head -n1)"
        SERVICE_DESK_JWT_ALGORITHM="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' nexus-service-desk | sed -n 's/^JWT_ALGORITHM=//p' | head -n1)"
        if [ -n "$BACKEND_JWT_SECRET" ] && [ "$BACKEND_JWT_SECRET" = "$SERVICE_DESK_JWT_SECRET" ] && \
           [ -n "$BACKEND_JWT_ALGORITHM" ] && [ "$BACKEND_JWT_ALGORITHM" = "$SERVICE_DESK_JWT_ALGORITHM" ]; then
            pass "backend and Service Desk JWT settings match"
        else
            fail "backend and Service Desk JWT settings are missing or do not match"
        fi
        unset BACKEND_JWT_SECRET BACKEND_JWT_ALGORITHM SERVICE_DESK_JWT_SECRET SERVICE_DESK_JWT_ALGORITHM
    else
        fail "backend and Service Desk JWT settings cannot be compared without the environment file"
    fi
else
    fail "Service Desk container is missing"
fi
if curl --fail --silent --show-error http://127.0.0.1:8000/health >/dev/null; then pass "backend health endpoint responds"; else fail "backend health endpoint failed"; fi
if curl --fail --silent --show-error http://127.0.0.1:13000/service-desk/api/health >/dev/null; then pass "Service Desk health endpoint responds"; else fail "Service Desk health endpoint failed"; fi

if [ "$FAILED" -ne 0 ]; then
    printf 'PREDEPLOY CHECK FAILED\n' >&2
    exit 1
fi
printf 'PREDEPLOY CHECK PASSED\n'
