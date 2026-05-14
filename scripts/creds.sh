#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f .generated-credentials ]]; then
  echo "No credentials found. Run 'make seed' first." >&2
  exit 1
fi
echo ""
echo "=== Seeded Credentials (username:password:department) ==="
cat .generated-credentials
echo ""
