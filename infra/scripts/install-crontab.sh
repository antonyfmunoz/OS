#!/usr/bin/env bash
set -euo pipefail

TOKEN_FILE="/root/.op-service-account-token"
TEMPLATE="${UMH_ROOT:-/opt/OS}/infra/crontab.managed"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "[install-crontab] ERROR: $TOKEN_FILE not found"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")
sed "s|__OP_TOKEN__|$TOKEN|" "$TEMPLATE" | crontab -
echo "[install-crontab] Crontab installed with 1Password service account token"
