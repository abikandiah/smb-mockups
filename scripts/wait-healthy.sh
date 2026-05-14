#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-flat}"
CONTAINER=$( [[ "$PROFILE" == "flat" ]] && echo "samba-nas" || echo "samba-fileserver" )
# Standard profile: DC provision (~45s) + fileserver domain join (~70s) = 230s worst case
MAX_WAIT=$( [[ "$PROFILE" == "flat" ]] && echo 120 || echo 360 )
ELAPSED=0

echo "Waiting for $CONTAINER to be healthy..."
until [[ "$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null)" == "healthy" ]]; do
  if (( ELAPSED >= MAX_WAIT )); then
    echo "Timed out waiting for $CONTAINER after ${MAX_WAIT}s" >&2
    exit 1
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  echo "  ...${ELAPSED}s elapsed"
done
echo "$CONTAINER is healthy."
