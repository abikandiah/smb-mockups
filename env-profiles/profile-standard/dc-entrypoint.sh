#!/usr/bin/env bash
set -euo pipefail

DATA_DIR=/var/lib/samba

# Only provision on first boot (volume is empty)
if [[ ! -f "${DATA_DIR}/private/krb5.conf" ]]; then
  echo "Provisioning Samba AD DC for ${SAMBA_REALM}..."
  samba-tool domain provision \
    --use-rfc2307 \
    --domain="${SAMBA_DOMAIN}" \
    --realm="${SAMBA_REALM}" \
    --adminpass="${SAMBA_ADMIN_PASSWORD}" \
    --dns-backend=SAMBA_INTERNAL \
    --server-role=dc
  cp /var/lib/samba/private/krb5.conf /etc/krb5.conf
  echo "Provision complete."
fi

exec samba --foreground --no-process-group
