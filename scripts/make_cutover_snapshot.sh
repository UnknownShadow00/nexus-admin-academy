#!/usr/bin/env bash
# Take a labelled, retention-proof snapshot before a V2 cutover.
#
# Why this exists: the nightly job prunes with
#
#     find "$DEST" -name 'nexus-*.db.gz' -mtime +14 -delete
#
# so a cutover snapshot named `nexus-...db.gz` is silently deleted a fortnight
# later — exactly when someone finally needs it. This writes
# `v2-cutover-<revision>-<stamp>.db.gz`, which that glob cannot match, so the
# snapshot survives until a human removes it.
#
# It never deletes anything and never alters the nightly retention policy.
# Writing requires --confirm; without it the script only reports its plan.
#
#   scripts/make_cutover_snapshot.sh                 # dry run
#   scripts/make_cutover_snapshot.sh --confirm
#   scripts/make_cutover_snapshot.sh --db /path/db --dest /path/dir --confirm
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${NEXUS_SQLITE_DB:-$REPO_ROOT/backend/nexus.db}"
DEST="${NEXUS_BACKUP_DIR:-$HOME/backups/nexus}"
LABEL="v2-cutover"
CONFIRM=0

usage() { sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0; }

while [ $# -gt 0 ]; do
    case "$1" in
        --db) DB="${2:?--db needs a path}"; shift 2 ;;
        --dest) DEST="${2:?--dest needs a path}"; shift 2 ;;
        --label) LABEL="${2:?--label needs a value}"; shift 2 ;;
        --confirm) CONFIRM=1; shift ;;
        -h|--help) usage ;;
        *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
done

case "$LABEL" in
    nexus-*|nexus)
        printf 'ERROR: label %q would match the nightly retention glob nexus-*.db.gz\n' "$LABEL" >&2
        exit 2 ;;
esac
if [[ ! "$LABEL" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf 'ERROR: label must contain only letters, numbers, dot, underscore, or hyphen\n' >&2
    exit 2
fi

[ -f "$DB" ] || { printf 'ERROR: database not found: %s\n' "$DB" >&2; exit 1; }

# Read the schema revision straight out of the file, read-only. The alembic
# CLI is deliberately not used: a bare alembic invocation resolves its own
# DATABASE_URL and can target production by accident.
REVISION="$(python3 - "$DB" <<'PY'
import sqlite3, sys
try:
    with sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    print(row[0] if row else "unknown")
except Exception:
    print("unknown")
PY
)"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$DEST/${LABEL}-${REVISION}-${STAMP}.db"

printf 'Cutover snapshot plan\n'
printf '  source database : %s\n' "$DB"
printf '  schema revision : %s\n' "$REVISION"
printf '  destination     : %s.gz\n' "$OUT"
printf '  retention       : outside the nightly nexus-*.db.gz prune — kept until removed by hand\n'

if [ "$CONFIRM" -ne 1 ]; then
    printf '\nDry run. Nothing was written. Re-run with --confirm to take the snapshot.\n'
    exit 0
fi

if [ -e "$OUT" ] || [ -e "$OUT.gz" ]; then
    printf 'ERROR: refusing to overwrite an existing snapshot: %s[.gz]\n' "$OUT" >&2
    exit 1
fi

mkdir -p "$DEST"

# SQLite's online backup API — consistent against a live writer, and it never
# opens the source for writing.
python3 - "$DB" "$OUT" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as source, sqlite3.connect(dst) as target:
    source.backup(target)
PY

gzip -f "$OUT"
SIZE="$(stat -c%s "$OUT.gz")"

# Same sanity floor the nightly job uses: a healthy dump is over 100 KiB
# gzipped. A snapshot smaller than that is not worth trusting at cutover.
if [ "$SIZE" -lt 102400 ]; then
    printf 'ERROR: snapshot is suspiciously small (%s bytes) — verify before relying on it\n' "$SIZE" >&2
    exit 1
fi

printf '\nSnapshot written: %s.gz (%s bytes)\n' "$OUT" "$SIZE"
printf 'Verify before cutting over:\n'
printf "  gzip -t %q.gz\n" "$OUT"
printf "  zcat %q.gz > /tmp/restore-check.db && python3 -c \"import sqlite3;print(sqlite3.connect('/tmp/restore-check.db').execute('PRAGMA integrity_check').fetchone())\"\n" "$OUT"
