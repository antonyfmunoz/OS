#!/usr/bin/env bash
# dc-up.sh — Start Docker services with secrets from 1Password
#
# Generates ephemeral .env files from 1Password references, starts containers,
# then shreds the plaintext files. Containers retain env vars in process memory.
#
# Usage: bash infra/scripts/dc-up.sh [docker compose args...]
# Examples:
#   bash infra/scripts/dc-up.sh                    # start all services
#   bash infra/scripts/dc-up.sh os-discord          # start one service
#   bash infra/scripts/dc-up.sh --build             # rebuild + start
set -euo pipefail

UMH_ROOT="${UMH_ROOT:-/opt/OS}"
cd "$UMH_ROOT"

SERVICES_TPL="services/.env.tpl"
UMH_TPL="infra/docker/umh.env.tpl"
SERVICES_ENV="services/.env"
UMH_ENV="infra/docker/umh.env"

cleanup() {
    shred -u "$SERVICES_ENV" "$UMH_ENV" 2>/dev/null || true
}
trap cleanup EXIT

if ! command -v op &>/dev/null; then
    echo "[dc-up] ERROR: 1Password CLI (op) not found. Install it first."
    exit 1
fi

if ! op whoami &>/dev/null; then
    echo "[dc-up] ERROR: 1Password CLI not authenticated."
    echo "  Set OP_SERVICE_ACCOUNT_TOKEN or run 'op signin'."
    exit 1
fi

echo "[dc-up] Resolving secrets from 1Password..."
op inject -i "$SERVICES_TPL" -o "$SERVICES_ENV"
op inject -i "$UMH_TPL" -o "$UMH_ENV"
chmod 600 "$SERVICES_ENV" "$UMH_ENV"

echo "[dc-up] Starting containers..."
docker compose up -d "$@"

echo "[dc-up] Waiting for containers to load env vars..."
sleep 3

echo "[dc-up] Shredding ephemeral .env files..."
# cleanup runs via trap

echo "[dc-up] Done. Verify with: docker compose ps"
