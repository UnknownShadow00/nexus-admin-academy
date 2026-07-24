#!/bin/bash
# Migrate an empty SQLite database to head and load the standard application
# and curriculum seeds. Used by CI's migration/seed job and by
# start_local_stack.sh. Never touches production — DATABASE_URL always points
# at a throwaway path.
#
# Required env (caller sets these; this script does not invent secrets):
#   DATABASE_URL, JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD,
#   ADMIN_API_KEY, ADMIN_SECRET_KEY,
#   SEED_PASSWORD_MENTOR/SHAK/RAKIB/AHMED/EMRAN/WALO/HUDAYFA
#
# Usage: scripts/e2e/seed_fresh_db.sh

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../backend" && pwd)"

: "${DATABASE_URL:?DATABASE_URL must be set to a throwaway sqlite path}"
if [[ "$DATABASE_URL" != sqlite://* ]]; then
    echo "Refusing to seed a non-sqlite DATABASE_URL ($DATABASE_URL) — this script is for throwaway test databases only." >&2
    exit 1
fi
if [[ "$DATABASE_URL" == *"/backend/nexus.db"* ]]; then
    echo "Refusing to seed the production database path." >&2
    exit 1
fi

cd "$BACKEND_DIR"

# Use the local venv when present (developer machines); fall back to
# whatever `python` CI's setup-python step put on PATH.
if [[ -x "./.venv/bin/python" ]]; then
    PYTHON="./.venv/bin/python"
else
    PYTHON="python"
fi

echo "== alembic upgrade head =="
"$PYTHON" -m alembic upgrade head

echo "== seed_users.py =="
"$PYTHON" scripts/seed_users.py

echo "== seed.py =="
"$PYTHON" seed.py

echo "== seed_curriculum.py =="
"$PYTHON" seed_curriculum.py
