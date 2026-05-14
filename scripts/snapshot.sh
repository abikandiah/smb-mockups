#!/usr/bin/env bash
set -euo pipefail
source .env

ACTION="${1:-save}"
PROFILE="${2:-flat}"
SNAPSHOT_DIR="./snapshots"
PROJECT="${COMPOSE_PROJECT_NAME:-smb-mockups}"

mkdir -p "$SNAPSHOT_DIR"

declare -A PROFILE_VOLUMES
PROFILE_VOLUMES["flat"]="nas-finance nas-engineering nas-hr"
PROFILE_VOLUMES["standard"]="fs-finance fs-engineering fs-hr dc-data dc-config"

VOLS="${PROFILE_VOLUMES[$PROFILE]:-}"
[[ -z "$VOLS" ]] && { echo "Unknown profile: $PROFILE" >&2; exit 1; }

case "$ACTION" in
  save)
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    for vol in $VOLS; do
      FULL_VOL="${PROJECT}_${vol}"
      ARCHIVE="${SNAPSHOT_DIR}/${PROFILE}-${vol}-${TIMESTAMP}.tar.gz"
      docker run --rm \
        -v "${FULL_VOL}:/source:ro" \
        -v "$(pwd)/snapshots:/backup" \
        alpine tar czf "/backup/${PROFILE}-${vol}-${TIMESTAMP}.tar.gz" -C /source .
      echo "Saved: $ARCHIVE"
    done
    ;;
  restore)
    for vol in $VOLS; do
      FULL_VOL="${PROJECT}_${vol}"
      ARCHIVE=$(ls -t "${SNAPSHOT_DIR}/${PROFILE}-${vol}-"*.tar.gz 2>/dev/null | head -1)
      if [[ -z "$ARCHIVE" ]]; then
        echo "No snapshot found for: $vol" >&2; continue
      fi
      docker run --rm \
        -v "${FULL_VOL}:/target" \
        -v "$(pwd)/snapshots:/backup" \
        alpine sh -c "rm -rf /target/* && tar xzf '/backup/$(basename "$ARCHIVE")' -C /target"
      echo "Restored: $ARCHIVE → $vol"
    done
    ;;
  *)
    echo "Usage: snapshot.sh [save|restore] [profile]" >&2; exit 1
    ;;
esac
