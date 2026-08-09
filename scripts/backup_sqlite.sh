#!/bin/bash
# Nightly SQLite + uploads backup for the live .101 deployment.
# (scripts/backup_db.sh is the pg_dump variant for the Docker/Postgres stack —
#  this one covers the systemd+SQLite deployment actually running on .101.)
#
# Install:  crontab -e  →  30 23 * * * /opt/apps/"IT TRAINING PROJECT CODE"/projects/nexus-admin-academy/scripts/backup_sqlite.sh >> ~/backups/nexus/backup.log 2>&1
#
# Uses Python's sqlite3 online-backup API (safe against a live writer; the
# sqlite3 CLI is not installed on this box). Keeps 14 days, refuses to prune
# if tonight's backup looks suspiciously small, and pairs each DB snapshot
# with a timestamp-matched uploads archive for consistent restoration.

set -euo pipefail

DB="${NEXUS_SQLITE_DB:-/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/nexus.db}"
UPLOADS="${NEXUS_UPLOADS_DIR:-/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/backend/uploads}"
DEST="${NEXUS_BACKUP_DIR:-$HOME/backups/nexus}"
STAMP="${NEXUS_BACKUP_STAMP:-$(date +%Y%m%d-%H%M%S)}"
OUT="$DEST/nexus-$STAMP.db"
UPLOADS_OUT="$DEST/nexus-uploads-$STAMP.tar.gz"

if [ ! -f "$DB" ]; then
    echo "ERROR: SQLite database not found: $DB" >&2
    exit 1
fi
if [ ! -d "$UPLOADS" ]; then
    echo "ERROR: uploads directory not found: $UPLOADS" >&2
    exit 1
fi

mkdir -p "$DEST"

python3 - "$DB" "$OUT" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as source, sqlite3.connect(dst) as target:
    source.backup(target)
PY
gzip -f "$OUT"

# Guard: a healthy dump is >100KB gzipped; if smaller, something is wrong —
# keep old backups and scream instead of pruning.
SIZE=$(stat -c%s "$OUT.gz")
if [ "$SIZE" -lt 102400 ]; then
    echo "$(date): BACKUP SUSPICIOUSLY SMALL ($SIZE bytes) — retention skipped" >&2
    exit 1
fi

tar -czf "$UPLOADS_OUT" -C "$UPLOADS" .

find "$DEST" -name 'nexus-*.db.gz' -mtime +14 -delete
find "$DEST" -name 'nexus-uploads-*.tar.gz' -mtime +14 -delete
echo "$(date): backup ok — $OUT.gz ($SIZE bytes), $UPLOADS_OUT"
