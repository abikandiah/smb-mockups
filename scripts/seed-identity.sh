#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-flat}"
source .env

GROUPS=("hr" "finance" "engineering" "executive")
CREDS_FILE=".generated-credentials"

> "$CREDS_FILE"   # Truncate on each run — never append

if [[ "$PROFILE" == "flat" ]]; then
  CONTAINER="samba-nas"
  # servercontainers/samba is Alpine-based: addgroup/adduser, not groupadd/useradd
  for group in "${GROUPS[@]}"; do
    docker exec "$CONTAINER" addgroup "$group" 2>/dev/null || true
  done
  for i in $(seq 1 10); do
    username="user$(printf '%02d' $i)"
    password=$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9' | head -c 16)
    dept=${GROUPS[$((RANDOM % ${#GROUPS[@]}))]}
    docker exec "$CONTAINER" adduser -D -H -s /sbin/nologin -G "$dept" "$username" 2>/dev/null || true
    printf '%s\n%s\n' "$password" "$password" | \
      docker exec -i "$CONTAINER" smbpasswd -a -s "$username" 2>/dev/null || true
    printf '%s:%s:%s\n' "$username" "$password" "$dept" >> "$CREDS_FILE"
  done
else
  CONTAINER="samba-dc"
  for group in "${GROUPS[@]}"; do
    docker exec "$CONTAINER" samba-tool group add "$group" 2>/dev/null || true
  done
  for i in $(seq 1 10); do
    username="user$(printf '%02d' $i)"
    password=$(openssl rand -base64 12 | tr -dc 'A-Za-z0-9!@#' | head -c 16)
    dept=${GROUPS[$((RANDOM % ${#GROUPS[@]}))]}
    docker exec "$CONTAINER" samba-tool user create "$username" "$password" \
      --department="$dept" \
      --mail-address="${username}@${DOMAIN_FQDN}"
    docker exec "$CONTAINER" samba-tool group addmembers "$dept" "$username"
    printf '%s:%s:%s\n' "$username" "$password" "$dept" >> "$CREDS_FILE"
  done
fi

echo "Seeded 10 users across ${#GROUPS[@]} groups. Run 'make creds' to view."
