#!/bin/bash
# Narrow-purpose maintenance script for NB-5 style controlled Service Desk
# validation sessions. Only touches the two Service Desk feature-gate
# environment values in the systemd drop-in that currently wins
# (zz-service-desk-admin.conf, alphabetically last), then reloads and
# restarts the backend unit and waits for a healthy response.
#
# Usage: sudo toggle_service_desk_lab.sh <LAB_ENABLED true|false> <ADMIN_ENABLED true|false>
#
# Intentionally does not accept arbitrary sed scripts or systemctl verbs —
# this is the whole point of scoping the sudoers NOPASSWD rule to this file.

set -euo pipefail

DROPIN="/etc/systemd/system/nexus-admin-academy.service.d/zz-service-desk-admin.conf"
UNIT="nexus-admin-academy.service"

usage() {
    echo "Usage: $0 <true|false> <true|false>" >&2
    echo "  arg1 = SERVICE_DESK_LAB_ENABLED" >&2
    echo "  arg2 = SERVICE_DESK_LAB_ADMIN_ENABLED" >&2
    exit 2
}

[ "$#" -eq 2 ] || usage

LAB="$1"
ADMIN="$2"

for v in "$LAB" "$ADMIN"; do
    case "$v" in
        true|false) ;;
        *) echo "Invalid value: $v (must be 'true' or 'false')" >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" -ne 0 ]; then
    echo "Must be run as root (via sudo)." >&2
    exit 1
fi

if [ ! -f "$DROPIN" ]; then
    echo "Expected drop-in not found: $DROPIN" >&2
    exit 1
fi

cat > "$DROPIN" <<EOF
[Service]
Environment="SERVICE_DESK_LAB_ADMIN_ENABLED=$ADMIN"
Environment="SERVICE_DESK_LAB_ENABLED=$LAB"
EOF

systemctl daemon-reload
systemctl restart "$UNIT"

for i in $(seq 1 15); do
    if curl --fail --silent --output /dev/null http://127.0.0.1:8000/health; then
        echo "OK: backend healthy after restart. Effective environment:"
        systemctl show "$UNIT" -p Environment
        exit 0
    fi
    sleep 1
done

echo "FAIL: backend did not become healthy within 15s" >&2
journalctl -u "$UNIT" -n 100 --no-pager >&2
exit 1
