#!/usr/bin/env bash
set -euo pipefail
source .env

PROFILE="${1:-flat}"
PASS=0
FAIL=0

check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  PASS: $desc"
    ((PASS++)) || true
  else
    echo "  FAIL: $desc"
    ((FAIL++)) || true
  fi
}

echo "=== Probing profile: $PROFILE ==="

TARGET=$( [[ "$PROFILE" == "flat" ]] && echo "samba-nas" || echo "samba-fileserver" )

check "Target container is healthy" \
  bash -c "[[ \"\$(docker inspect --format='{{.State.Health.Status}}' ${TARGET} 2>/dev/null)\" == \"healthy\" ]]"

check "Port 445 reachable on bridge" \
  docker run --rm --network "${SMB_BRIDGE}" alpine sh -c "nc -z ${TARGET} 445"

# Null sessions are disabled in ADS security mode; only test on flat profile
if [[ "$PROFILE" == "flat" ]]; then
  check "Shares listed without auth (guest)" \
    docker run --rm --network "${SMB_BRIDGE}" alpine sh -c \
      "apk add -q samba-client && smbclient -L ${TARGET} -N 2>/dev/null | grep -q ${SHARE_FINANCE}"
fi

check "Credentials file generated" test -s .generated-credentials

if [[ -s .generated-credentials ]]; then
  FIRST_USER=$(head -1 .generated-credentials)
  AUTH_USER=$(echo "$FIRST_USER" | cut -d: -f1)
  AUTH_PASS=$(echo "$FIRST_USER" | cut -d: -f2)
  AUTH_DEPT=$(echo "$FIRST_USER" | cut -d: -f3)

  # Resolve the share this user actually has access to
  case "$AUTH_DEPT" in
    finance)     AUTH_SHARE="$SHARE_FINANCE" ;;
    engineering) AUTH_SHARE="$SHARE_ENGINEERING" ;;
    hr)          AUTH_SHARE="$SHARE_HR" ;;
    executive)   AUTH_SHARE="$SHARE_FINANCE" ;;
    *)           AUTH_SHARE="$SHARE_FINANCE" ;;
  esac

  if [[ "$PROFILE" != "flat" ]]; then
    check "Shares listed (authenticated, ${AUTH_USER})" \
      docker run --rm --network "${SMB_BRIDGE}" alpine sh -c \
        "apk add -q samba-client && smbclient -L ${TARGET} -U ${AUTH_USER}%${AUTH_PASS} 2>/dev/null | grep -q ${SHARE_FINANCE}"
  fi

  check "Auth as seeded user (${AUTH_USER}@${AUTH_DEPT} → \\\\${TARGET}\\${AUTH_SHARE})" \
    docker run --rm --network "${SMB_BRIDGE}" alpine sh -c \
      "apk add -q samba-client && smbclient //${TARGET}/${AUTH_SHARE} -U ${AUTH_USER}%${AUTH_PASS} -c 'ls' 2>/dev/null"
fi

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[[ $FAIL -eq 0 ]] || exit 1
