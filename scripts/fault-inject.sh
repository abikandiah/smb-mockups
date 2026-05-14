#!/usr/bin/env bash
set -euo pipefail
source .env

FAULT="${1:-}"
PROFILE="${2:-flat}"

[[ -z "$FAULT" ]] && { echo "Usage: make fault FAULT=<type> [PROFILE=<profile>]"; exit 1; }

TARGET=$( [[ "$PROFILE" == "flat" ]] && echo "samba-nas" || echo "samba-fileserver" )
FINANCE_FILE="/storage/${SHARE_FINANCE}/ledger_entries.csv"

case "$FAULT" in
  dc-down)
    docker pause samba-dc
    echo "Injected: samba-dc paused"
    ;;
  dc-restore)
    docker unpause samba-dc
    echo "Cleared: samba-dc unpaused"
    ;;
  nas-down)
    docker pause samba-nas
    echo "Injected: samba-nas paused"
    ;;
  nas-restore)
    docker unpause samba-nas
    echo "Cleared: samba-nas unpaused"
    ;;
  acl-corrupt)
    docker exec "$TARGET" chmod 000 "$FINANCE_FILE"
    echo "Injected: $FINANCE_FILE set to 000"
    ;;
  acl-restore)
    docker exec "$TARGET" chmod 644 "$FINANCE_FILE"
    echo "Cleared: $FINANCE_FILE permissions restored"
    ;;
  restore-all)
    docker unpause samba-dc 2>/dev/null || true
    docker unpause samba-nas 2>/dev/null || true
    docker unpause samba-fileserver 2>/dev/null || true
    docker exec "$TARGET" chmod 644 "$FINANCE_FILE" 2>/dev/null || true
    echo "All faults cleared"
    ;;
  *)
    echo "Unknown fault: $FAULT"
    echo "Available: dc-down, dc-restore, nas-down, nas-restore, acl-corrupt, acl-restore, restore-all"
    exit 1
    ;;
esac
