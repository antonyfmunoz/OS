#!/usr/bin/env bash
# obsidian_rsync.sh — sync Obsidian vault from Windows machine via Tailscale
#
# Usage:
#   scripts/obsidian_rsync.sh          # full sync
#   scripts/obsidian_rsync.sh --dry    # preview only
#
# Cron example (every 15 min):
#   */15 * * * * /opt/OS/scripts/obsidian_rsync.sh >> /opt/OS/logs/obsidian_rsync.log 2>&1
#
# Prerequisites:
#   - Tailscale active on both machines
#   - SSH key auth configured (no password prompts)
#   - rsync installed on both sides
#
# Fill in these values:
TAILSCALE_IP="PLACEHOLDER_IP"  # e.g. 100.x.y.z
REMOTE_USER="PLACEHOLDER_USER"  # e.g. antony
REMOTE_VAULT_PATH="PLACEHOLDER_PATH"  # e.g. /c/Users/Antony/Documents/Obsidian/Vault/
LOCAL_VAULT_PATH="/opt/OS/vault/"

set -euo pipefail

LOGFILE="/opt/OS/logs/obsidian_rsync.log"
mkdir -p /opt/OS/logs

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"
}

# Validate config
if [[ "$TAILSCALE_IP" == "PLACEHOLDER_IP" ]]; then
    log "ERROR: TAILSCALE_IP not configured. Edit scripts/obsidian_rsync.sh"
    exit 1
fi

# Check Tailscale connectivity
if ! ping -c 1 -W 3 "$TAILSCALE_IP" > /dev/null 2>&1; then
    log "WARN: Cannot reach $TAILSCALE_IP — machine offline or Tailscale down"
    exit 0  # exit 0 so cron doesn't spam on offline
fi

DRY_FLAG=""
if [[ "${1:-}" == "--dry" ]]; then
    DRY_FLAG="--dry-run"
    log "DRY RUN MODE"
fi

log "Starting rsync from ${REMOTE_USER}@${TAILSCALE_IP}:${REMOTE_VAULT_PATH}"

rsync -avz --delete \
    --exclude='.obsidian/workspace.json' \
    --exclude='.obsidian/workspace-mobile.json' \
    --exclude='.trash/' \
    --exclude='.DS_Store' \
    $DRY_FLAG \
    "${REMOTE_USER}@${TAILSCALE_IP}:${REMOTE_VAULT_PATH}" \
    "$LOCAL_VAULT_PATH"

EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]]; then
    log "Sync complete"
else
    log "ERROR: rsync exited with code $EXIT_CODE"
fi

exit $EXIT_CODE
