#!/usr/bin/env bash
# Nightly PostgreSQL backup for Nexus Admin Academy (docker compose deployment).
#
# Dumps the `nexus` database from the compose `postgres` service, gzips it
# into /opt/backups, and prunes backups older than 14 days.
#
# Install (manual step — run `crontab -e` and add):
#   15 3 * * * /bin/bash "/opt/apps/IT TRAINING PROJECT CODE/projects/nexus-admin-academy/scripts/backup_db.sh" >> /opt/backups/backup.log 2>&1

set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="/opt/backups"
RETENTION_DAYS=14
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTFILE="${BACKUP_DIR}/nexus-${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

docker compose --project-directory "${COMPOSE_DIR}" exec -T postgres \
    pg_dump -U nexus -d nexus | gzip > "${OUTFILE}"

# A dump that small is a failed dump — refuse to silently keep it
if [ "$(stat -c%s "${OUTFILE}")" -lt 1024 ]; then
    echo "ERROR: backup ${OUTFILE} is suspiciously small, keeping previous backups" >&2
    exit 1
fi

find "${BACKUP_DIR}" -name "nexus-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "OK: ${OUTFILE} ($(stat -c%s "${OUTFILE}") bytes)"
