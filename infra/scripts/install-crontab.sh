#!/usr/bin/env bash
set -euo pipefail

TOKEN_FILE="/root/.op-service-account-token"
TEMPLATE="${UMH_ROOT:-/opt/OS}/infra/crontab.managed"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "[install-crontab] ERROR: $TOKEN_FILE not found"
    exit 1
fi

PERMS=$(stat -c '%a' "$TOKEN_FILE")
OWNER=$(stat -c '%U' "$TOKEN_FILE")
if [ "$PERMS" != "600" ]; then
    echo "[install-crontab] ERROR: $TOKEN_FILE must be mode 600 (is $PERMS)"
    exit 1
fi
if [ "$OWNER" != "$(id -un)" ]; then
    echo "[install-crontab] ERROR: $TOKEN_FILE must be owned by $(id -un) (owned by $OWNER)"
    exit 1
fi

IFS= read -r TOKEN < "$TOKEN_FILE"
if [[ ! "$TOKEN" =~ ^ops_[A-Za-z0-9_-]+$ ]]; then
    echo "[install-crontab] ERROR: token does not match expected ops_* format"
    exit 1
fi

# Token injected via stdin to python, never appears in process argv
python3 -c "
import sys
token = sys.stdin.readline().strip()
with open(sys.argv[1]) as f:
    print(f.read().replace('__OP_TOKEN__', token), end='')
" "$TEMPLATE" <<< "$TOKEN" | crontab -

echo "[install-crontab] Crontab installed with 1Password service account token"
